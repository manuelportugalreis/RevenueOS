"""Reproducible comparisons; separates synthetic diagnostics from predictive/live evidence."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
import time
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, Engine, text

from revenueos.knowledge import DocumentInput, Principal, ingest_document, revoke_document, search
from revenueos.providers import ProviderReply, ScriptedProvider
from revenueos.recommendations import PriceCard, configure_budget, recommend, template
from revenueos.scoring import predictive_readiness, rank_leads

STEWARD = UUID("22222222-2222-4222-8222-222222222222")
READER = UUID("33333333-3333-4333-8333-333333333333")
FIXTURE_APPROVAL_TIME = datetime(2026, 9, 1, tzinfo=UTC)


def seed_knowledge(connection: Connection, organization: UUID, corpus_path: Path) -> None:
    mode = connection.scalar(
        text("SELECT data_mode FROM organizations WHERE id=:org"), {"org": organization}
    )
    if mode != "synthetic":
        raise ValueError("fixture_seeding_requires_synthetic_organization")
    for actor, role, scopes in (
        (STEWARD, "steward", ["team", "management"]),
        (READER, "reader", ["team"]),
    ):
        connection.execute(
            text("""
            INSERT INTO knowledge_memberships(organization_id,actor_id,role,scopes)
            VALUES(:org,:actor,:role,:scopes) ON CONFLICT DO NOTHING
        """),
            {"org": organization, "actor": actor, "role": role, "scopes": scopes},
        )
    principal = Principal(organization_id=organization, actor_id=STEWARD)
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    for entry in corpus["documents"]:
        version = ingest_document(
            connection,
            principal,
            DocumentInput.model_validate(entry["document"]),
            now=FIXTURE_APPROVAL_TIME,
        )
        revoked = (
            connection.scalar(
                text("SELECT status FROM document_versions WHERE id=:id"), {"id": version}
            )
            == "revoked"
        )
        if entry["revoked"] and not revoked:
            revoke_document(connection, principal, version)


def scripted_valid(payload: dict[str, Any], attempt: int) -> ProviderReply:
    """Copies the template deliberately; tests schema plumbing, never LLM reasoning."""
    from revenueos.knowledge import Citation

    request = json.loads(payload["input"])
    citations = [Citation.model_validate(item) for item in request["evidence"]]
    result = template(UUID(request["lead_id"]), request["source"], citations)
    return ProviderReply(result.model_dump_json(), 500, 180, "scripted-fixture-v1")


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _wilson(successes: int, total: int) -> list[float] | None:
    if not total:
        return None
    z = 1.96
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    half = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return [max(0, center - half), min(1, center + half)]


def queue_diagnostics(
    connection: Connection, organization: UUID, dataset: UUID, *, k: int = 20
) -> dict[str, Any]:
    if not 1 <= k <= 100:
        raise ValueError("invalid_queue_capacity")
    started = time.monotonic()
    ranked = rank_leads(connection, organization, dataset)
    rows = connection.execute(
        text("""
        SELECT l.id,o.observation_complete,
          (o.qualified_at BETWEEN l.created_at AND l.created_at+interval '30 days') AS positive,
          (o.observed_through >= l.created_at+interval '30 days') AS covered
        FROM leads l LEFT JOIN lead_outcomes o ON (o.organization_id,o.dataset_id,o.lead_id)=
          (l.organization_id,l.dataset_id,l.id)
        WHERE l.organization_id=:org AND l.dataset_id=:dataset
    """),
        {"org": organization, "dataset": dataset},
    ).mappings()
    labels = {str(row["id"]): row for row in rows}
    results = {}
    rules_top = set(ranked["queues"]["rules"][:k])
    for method, queue in ranked["queues"].items():
        selected = queue[:k]
        known = [
            labels[lead]
            for lead in selected
            if labels[lead]["observation_complete"] and labels[lead]["covered"]
        ]
        results[method] = {
            "selected": len(selected),
            "known_synthetic_outcomes": len(known),
            "positive_synthetic_outcomes": sum(bool(row["positive"]) for row in known),
            "overlap_with_rules_top_k": len(set(selected) & rules_top),
        }
    return {
        "evidence_class": "synthetic_snapshot_composition_not_prediction",
        "capacity_k": k,
        "eligible_count": len(ranked["queues"]["rules"]),
        "queues": results,
        "elapsed_ms": (time.monotonic() - started) * 1000,
        "predictive_accuracy": None,
        "caveat": "Features/outcomes share a synthetic current snapshot; no predictive holdout.",
    }


def evaluate(
    engine: Engine, organization: UUID, dataset: UUID, fixture_dir: Path, *, split: str = "test"
) -> dict[str, Any]:
    if split not in ("dev", "test"):
        raise ValueError("choose_dev_or_test_split")
    case_data = json.loads((fixture_dir / "cases.json").read_text(encoding="utf-8"))
    cases = [case for case in case_data["cases"] if case["split"] == split]
    principal = Principal(organization_id=organization, actor_id=READER)
    now = datetime.fromisoformat(case_data["fixed_at"])
    with engine.begin() as connection:
        seed_knowledge(connection, organization, fixture_dir / "corpus.json")
        steward = Principal(organization_id=organization, actor_id=STEWARD)
        configure_budget(connection, steward, now.strftime("%Y-%m"), Decimal("10"))
        readiness = predictive_readiness(connection, organization, dataset)
        diagnostics = queue_diagnostics(connection, organization, dataset)
        lead = connection.scalar(
            text("""
            SELECT l.id FROM leads l JOIN lead_private p ON
              (p.organization_id,p.dataset_id,p.lead_id)=(l.organization_id,l.dataset_id,l.id)
            WHERE l.organization_id=:org AND l.dataset_id=:dataset AND NOT l.do_not_contact
              AND l.deleted_at IS NULL AND l.status<>'disqualified'
              AND l.source NOT IN ('test','internal') AND p.lawful_use_status='approved'
            ORDER BY l.external_id LIMIT 1
        """),
            {"org": organization, "dataset": dataset},
        )
        if lead is None:
            raise ValueError("no_eligible_evaluation_lead")
        document_slugs: dict[UUID, str] = {
            row[0]: row[1]
            for row in connection.execute(
                text("SELECT id,slug FROM documents WHERE organization_id=:org"),
                {"org": organization},
            ).all()
        }
    fixture_price = PriceCard(
        version="SIMULATED-not-provider-pricing-v1",
        model="scripted-fixture-v1",
        input_per_million_usd=Decimal("0.5"),
        output_per_million_usd=Decimal("2"),
    )
    details = []
    retrieval_counts: dict[str, dict[str, Any]] = {
        method: {"answerable": 0, "hits": 0, "latencies": []}
        for method in ("lexical", "title_keyword")
    }
    recommendations: dict[str, dict[str, Any]] = {
        method: {
            "total": 0,
            "correct_abstentions": 0,
            "abstention_cases": 0,
            "false_abstentions": 0,
            "answerable_cases": 0,
            "relevant_answers": 0,
            "latencies": [],
            "attempts": 0,
            "simulated_cost_usd": Decimal("0"),
        }
        for method in ("template", "scripted_fixture")
    }
    for case in cases:
        row: dict[str, Any] = {
            "case_id": case["id"],
            "family": case["family"],
            "category": case["category"],
            "retrieval": {},
            "recommendations": {},
        }
        for method in ("lexical", "title_keyword"):
            started = time.monotonic()
            with engine.connect() as connection:
                hits = search(connection, principal, case["query"], method=method, at=now)
            elapsed = (time.monotonic() - started) * 1000
            found = [document_slugs[citation.document_id] for citation in hits]
            relevant = set(found) & set(case["relevant_slugs"])
            tally = retrieval_counts[method]
            tally["latencies"].append(elapsed)
            if case["relevant_slugs"]:
                tally["answerable"] += 1
                tally["hits"] += int(bool(relevant))
            row["retrieval"][method] = {
                "found_slugs": found,
                "relevant_hit": bool(relevant),
                "latency_ms": elapsed,
            }
        for method in ("template", "scripted_fixture"):
            started = time.monotonic()
            result = recommend(
                engine,
                principal,
                dataset,
                lead,
                case["query"],
                now=now,
                provider=ScriptedProvider(scripted_valid) if method != "template" else None,
                price=fixture_price if method != "template" else None,
                quality_profile="legacy_v1",
            )
            elapsed = (time.monotonic() - started) * 1000
            tally = recommendations[method]
            tally["total"] += 1
            tally["latencies"].append(elapsed)
            abstained = result["state"] != "review_pending"
            if case["expect_abstention"]:
                tally["abstention_cases"] += 1
                tally["correct_abstentions"] += int(abstained)
            else:
                tally["answerable_cases"] += 1
                tally["false_abstentions"] += int(abstained)
                if not abstained:
                    # All passages are one chunk in this fixture; compare exact document gold.
                    used = {
                        claim["evidence_id"]
                        for claim in result["recommendation"]["rationale_claims"]
                    }
                    with engine.connect() as connection:
                        hits = search(connection, principal, case["query"], at=now)
                    correct_ids = {
                        citation.evidence_id
                        for citation in hits
                        if document_slugs[citation.document_id] in case["relevant_slugs"]
                    }
                    tally["relevant_answers"] += int(bool(used & correct_ids))
            tally["attempts"] += len(result["attempts"])
            tally["simulated_cost_usd"] += sum(
                (attempt["estimated_cost_usd"] or Decimal("0")) for attempt in result["attempts"]
            )
            row["recommendations"][method] = {
                "state": result["state"],
                "failure_code": result["failure_code"],
                "latency_ms": elapsed,
                "attempts": len(result["attempts"]),
                "run_id": result["run_id"],
            }
        details.append(row)
    retrieval_report = {}
    for method, tally in retrieval_counts.items():
        total = tally["answerable"]
        retrieval_report[method] = {
            "answerable_cases": total,
            "relevant_passage_hits_at_5": tally["hits"],
            "recall_at_5": tally["hits"] / total if total else None,
            "descriptive_wilson_95": _wilson(tally["hits"], total),
            "p95_latency_ms": _percentile(tally["latencies"], 0.95),
        }
    recommendation_report = {}
    for method, tally in recommendations.items():
        recommendation_report[method] = {
            key: value for key, value in tally.items() if key != "latencies"
        }
        recommendation_report[method]["mean_latency_ms"] = statistics.mean(tally["latencies"])
        recommendation_report[method]["p95_latency_ms"] = _percentile(tally["latencies"], 0.95)
        count_abstain = tally["abstention_cases"]
        count_answer = tally["answerable_cases"]
        recommendation_report[method]["correct_abstention_rate"] = (
            tally["correct_abstentions"] / count_abstain if count_abstain else None
        )
        recommendation_report[method]["false_abstention_rate"] = (
            tally["false_abstentions"] / count_answer if count_answer else None
        )
        recommendation_report[method]["abstention_gates_passed"] = bool(
            count_abstain
            and count_answer
            and tally["correct_abstentions"] / count_abstain >= 0.95
            and tally["false_abstentions"] / count_answer <= 0.10
        )
    return {
        "evaluation_version": "offline_intelligence_eval_v1",
        "split": split,
        "cases": len(cases),
        "independent_families": len({case["family"] for case in cases}),
        "categories": dict(Counter(case["category"] for case in cases)),
        "annotation_source": case_data["annotation_source"],
        "fixture_hashes": {
            name: hashlib.sha256((fixture_dir / name).read_bytes()).hexdigest()
            for name in ("cases.json", "corpus.json", "failure_cases.json")
        },
        "readiness": readiness,
        "queue_comparison": diagnostics,
        "retrieval_comparison": retrieval_report,
        "recommendation_comparison": recommendation_report,
        "cost_evidence": (
            "No external calls. Scripted token counts and rates are simulated, not billed."
        ),
        "limitations": [
            "No independent human annotation or semantic quality adjudication.",
            "Variants share families; intervals are descriptive, not independent-case inference.",
            "Scripted provider copies the template; it measures plumbing, not LLM skill.",
            "No live-model, predictive-accuracy, real-business, or ROI result is established.",
        ],
        "live_model_evaluation": "not_run_offline_by_owner_instruction",
        "release_status": "offline_demo_only_independent_review_and_live_quality_pending",
        "cases_detail": details,
    }
