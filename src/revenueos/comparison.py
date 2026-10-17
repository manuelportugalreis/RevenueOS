"""Paired synthetic workflow diagnostics, never a measurement of human productivity."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, text

from revenueos.db import get_engine
from revenueos.evaluation import READER, queue_diagnostics, seed_knowledge
from revenueos.knowledge import Principal, authorize, resolve_citation
from revenueos.recommendations import recommend
from revenueos.scoring import predictive_readiness
from revenueos.workflows import POLICY_VERSION, run_workflow

ARMS = ("baseline_title_template", "assisted_bounded_lexical_template")
ABLATION_ARMS = (
    "baseline_title_template",
    "legacy_lexical_template",
    "focused_direct_template",
    "focused_bounded_template",
)
SEED = 20261016


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lo = int(index)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)


def paired_interval(
    rows: list[dict[str, Any]], seed: int = SEED, arms: tuple[str, ...] = ARMS
) -> dict[str, Any]:
    """Resample whole families, preserving paired arms and correlated variants."""
    families: dict[str, list[float]] = defaultdict(list)
    pairs: dict[str, dict[str, Any]] = defaultdict(dict)
    for row in rows:
        if row["phase"] == "measured" and row["repetition"] == 0:
            pairs[row["case_id"]][row["arm"]] = row
    for pair in pairs.values():
        if set(pair) != set(arms) or len(arms) != 2:
            raise ValueError("incomplete_case_pair")
        baseline, assisted = (pair[arm] for arm in arms)
        families[baseline["family"]].append(
            float(assisted["fixture_success"]) - float(baseline["fixture_success"])
        )
    if not families:
        return {"point": None, "interval": None, "families": 0}
    keys = sorted(families)
    rng = random.Random(seed)
    estimates = []
    for _ in range(2000):
        sampled = [value for key in rng.choices(keys, k=len(keys)) for value in families[key]]
        estimates.append(statistics.mean(sampled))
    return {
        "point": statistics.mean(value for values in families.values() for value in values),
        "interval": [percentile(estimates, 0.025), percentile(estimates, 0.975)],
        "families": len(keys),
        "bootstrap_resamples": 2000,
        "seed": seed,
        "interpretation": (
            "Descriptive paired family bootstrap, conditional on authored fixture; "
            "not pilot inference."
        ),
    }


def classify(
    case: dict[str, Any],
    state: str,
    output: dict[str, Any] | None,
    evidence: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    completed = state == "review_pending" and output is not None
    abstained = state == "abstained" and output is not None
    claims = (
        [*output.get("rationale_claims", []), *((output.get("draft") or {}).get("claims", []))]
        if output
        else []
    )
    grounded = bool(claims) and all(
        claim["evidence_id"] in evidence
        and claim["text"] == claim["quote"] == evidence[claim["evidence_id"]][1]
        for claim in claims
    )
    relevant = grounded and all(
        evidence[claim["evidence_id"]][0] in case["relevant_slugs"] for claim in claims
    )
    success = abstained if case["expect_abstention"] else completed and relevant
    return {
        "fixture_success": bool(success),
        "completed": completed,
        "abstained": abstained,
        "technical_failure": state not in ("review_pending", "abstained") or output is None,
        "grounded_completion": bool(completed and grounded),
        "relevant_completion": bool(completed and relevant and not case["expect_abstention"]),
        "false_abstention": bool(abstained and not case["expect_abstention"]),
        "inappropriate_completion": bool(completed and (case["expect_abstention"] or not relevant)),
    }


def summarize(rows: list[dict[str, Any]], arms: tuple[str, ...] = ARMS) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for arm in arms:
        attempts = [row for row in rows if row["arm"] == arm and row["phase"] == "measured"]
        unique = [row for row in attempts if row["repetition"] == 0]
        answerable = [row for row in unique if not row["expect_abstention"]]
        abstention = [row for row in unique if row["expect_abstention"]]
        count = Counter(row["state"] for row in attempts)
        successes = sum(row["fixture_success"] for row in unique)
        false_abstentions = sum(row["false_abstention"] for row in answerable)
        correct_abstentions = sum(row["abstained"] for row in abstention)
        report[arm] = {
            "attempts": len(attempts),
            "unique_tasks": len(unique),
            "states": dict(count),
            "fixture_task_successes": successes,
            "fixture_task_success_rate": successes / len(unique) if unique else None,
            "answerable_tasks": len(answerable),
            "abstention_tasks": len(abstention),
            "relevant_completions": sum(row["relevant_completion"] for row in answerable),
            "false_abstentions": false_abstentions,
            "false_abstention_rate": false_abstentions / len(answerable) if answerable else None,
            "correct_abstentions": correct_abstentions,
            "correct_abstention_rate": correct_abstentions / len(abstention)
            if abstention
            else None,
            "inappropriate_completions": sum(row["inappropriate_completion"] for row in unique),
            "unsupported_completions": sum(
                row["completed"] and not row["grounded_completion"] for row in unique
            ),
            "technical_failures_all_attempts": sum(row["technical_failure"] for row in attempts),
            "mean_software_latency_ms": statistics.mean(row["elapsed_ms"] for row in attempts)
            if attempts
            else None,
            "p95_software_latency_ms": percentile([row["elapsed_ms"] for row in attempts], 0.95),
            "provider_attempts": sum(row["provider_attempts"] for row in attempts),
            "actual_provider_invoice_usd": None,
            "human_minutes_per_task": None,
            "abstention_gates_passed": bool(
                answerable
                and abstention
                and false_abstentions / len(answerable) <= 0.1
                and correct_abstentions / len(abstention) >= 0.95
            ),
        }
    if len(arms) == 2:
        report["paired_fixture_success_difference"] = paired_interval(rows, arms=arms)
    else:
        report["paired_differences"] = {
            f"{second}_minus_{first}": paired_interval(
                [row for row in rows if row["arm"] in (first, second)], arms=(first, second)
            )
            for first, second in ((arms[1], arms[2]), (arms[2], arms[3]), (arms[0], arms[3]))
        }
    report["unstable_case_arms"] = len(
        {
            (row["case_id"], row["arm"])
            for row in rows
            if row["phase"] == "measured"
            and any(
                other["case_id"] == row["case_id"]
                and other["arm"] == row["arm"]
                and (other["state"], other["fixture_success"])
                != (row["state"], row["fixture_success"])
                for other in rows
                if other["phase"] == "measured"
            )
        }
    )
    return report


def business_scenario(assumptions: dict[str, float]) -> dict[str, Any]:
    required = {
        "monthly_leads",
        "baseline_minutes",
        "assisted_minutes_including_review",
        "loaded_hourly_usd",
        "monthly_operating_usd",
        "monthly_amortized_setup_usd",
    }
    if set(assumptions) != required or any(
        type(v) not in (int, float) or v < 0 or not float(v) < float("inf")
        for v in assumptions.values()
    ):
        raise ValueError("explicit_finite_nonnegative_scenario_assumptions_required")
    a = {key: Decimal(str(value)) for key, value in assumptions.items()}
    minutes = a["baseline_minutes"] - a["assisted_minutes_including_review"]
    hours = a["monthly_leads"] * minutes / 60
    capacity = hours * a["loaded_hourly_usd"]
    costs = a["monthly_operating_usd"] + a["monthly_amortized_setup_usd"]
    per_lead = minutes / 60 * a["loaded_hourly_usd"]
    return {
        "evidence_class": "simulation_not_observed",
        "assumptions": assumptions,
        "capacity_hours": float(hours.quantize(Decimal("0.0001"))),
        "potential_capacity_value_usd": float(capacity.quantize(Decimal("0.01"))),
        "scenario_cost_usd": float(costs.quantize(Decimal("0.01"))),
        "net_potential_capacity_value_usd": float((capacity - costs).quantize(Decimal("0.01"))),
        "capacity_break_even_leads": float(costs / per_lead) if per_lead > 0 else None,
        "realized_cash_savings_usd": None,
        "attributable_revenue_usd": None,
        "measured_roi": None,
    }


def execute(
    engine: Engine,
    organization: UUID,
    dataset: UUID,
    fixture: Path,
    destination: Path,
    repetitions: int = 2,
    variant: str = "legacy",
    split_scope: str = "all",
) -> dict[str, Any]:
    if variant not in ("legacy", "ablation"):
        raise ValueError("unknown_comparison_variant")
    if split_scope not in ("all", "dev", "test"):
        raise ValueError("unknown_split_scope")
    arms_to_run = ARMS if variant == "legacy" else ABLATION_ARMS
    if not 1 <= repetitions <= 5:
        raise ValueError("repetitions_must_be_1_to_5")
    destination.mkdir(parents=True, exist_ok=True)
    raw_path = destination / "RevenueOS-Comparison-Attempts.jsonl"
    report_path = destination / "RevenueOS-Workflow-Comparison.json"
    if raw_path.exists() or report_path.exists():
        raise ValueError("use_a_fresh_output_directory_preserve_previous_runs")
    for entry in (fixture / "SHA256SUMS").read_text().splitlines():
        expected, name = entry.split("  ", 1)
        if (
            Path(name).name != name
            or hashlib.sha256((fixture / name).read_bytes()).hexdigest() != expected
        ):
            raise ValueError("fixture_hash_mismatch")
    fixture_data = json.loads((fixture / "cases.json").read_text())
    if not fixture_data["cases"] or len({c["id"] for c in fixture_data["cases"]}) != len(
        fixture_data["cases"]
    ):
        raise ValueError("empty_or_duplicate_cases")
    fixed_at = datetime.fromisoformat(fixture_data["fixed_at"])
    principal = Principal(organization_id=organization, actor_id=READER)
    started = datetime.now(UTC)
    with engine.begin() as connection:
        authorize(connection, principal)
        if (
            connection.scalar(
                text("SELECT data_mode FROM datasets WHERE organization_id=:org AND id=:id"),
                {"org": organization, "id": dataset},
            )
            != "synthetic"
        ):
            raise ValueError("comparison_requires_synthetic_snapshot")
        seed_knowledge(connection, organization, fixture / "corpus.json")
        readiness = predictive_readiness(connection, organization, dataset)
        queues = queue_diagnostics(connection, organization, dataset)
        lead = connection.scalar(
            text("""SELECT l.id FROM leads l JOIN lead_private p ON
            (p.organization_id,p.dataset_id,p.lead_id)=(l.organization_id,l.dataset_id,l.id)
            WHERE l.organization_id=:org AND l.dataset_id=:dataset AND NOT l.do_not_contact
              AND l.deleted_at IS NULL AND l.status<>'disqualified'
              AND l.source NOT IN ('test','internal') AND p.lawful_use_status='approved'
            ORDER BY l.external_id LIMIT 1"""),
            {"org": organization, "dataset": dataset},
        )
        if lead is None:
            raise ValueError("no_eligible_synthetic_target")
        slugs = {
            str(row[0]): row[1]
            for row in connection.execute(
                text("SELECT id,slug FROM documents WHERE organization_id=:org"),
                {"org": organization},
            )
        }
    cases = [
        case
        for case in fixture_data["cases"]
        if split_scope == "all" or case["split"] == split_scope
    ]
    rows: list[dict[str, Any]] = []
    rng = random.Random(SEED)
    schedule = [("warmup", -1, case) for case in cases[:4]]
    for repetition in range(repetitions):
        order = list(cases)
        rng.shuffle(order)
        schedule.extend(("measured", repetition, case) for case in order)
    with raw_path.open("x", encoding="utf-8") as raw:
        for phase, repetition, case in schedule:
            arms = list(arms_to_run)
            rng.shuffle(arms)
            for arm in arms:
                begin = time.perf_counter()
                run = workflow = None
                state, failure, output = "failed", None, None
                try:
                    if arm not in (ARMS[1], "focused_bounded_template"):
                        result = recommend(
                            engine,
                            principal,
                            dataset,
                            lead,
                            case["query"],
                            now=fixed_at,
                            retrieval_method="title_keyword" if arm == ARMS[0] else "lexical",
                            quality_profile="focused_v2"
                            if arm == "focused_direct_template"
                            else "legacy_v1",
                        )
                        run = result["run_id"]
                    else:
                        result = run_workflow(
                            engine,
                            principal,
                            dataset,
                            lead,
                            case["query"],
                            evidence_at=fixed_at,
                            quality_profile="focused_v2"
                            if arm == "focused_bounded_template"
                            else "legacy_v1",
                        )
                        run, workflow = result["recommendation_id"], result["workflow_id"]
                    state, failure = result["state"], result["failure_code"]
                except Exception as exc:
                    failure = "evaluation_" + type(exc).__name__
                elapsed = (time.perf_counter() - begin) * 1000
                evidence: dict[str, tuple[str, str]] = {}
                provider_attempts = 0
                with engine.connect() as connection:
                    if run:
                        output = connection.scalar(
                            text("""SELECT output FROM ai_runs
                            WHERE organization_id=:org AND actor_id=:actor AND id=:id"""),
                            {"org": organization, "actor": READER, "id": run},
                        )
                        provider_attempts = connection.scalar(
                            text("SELECT count(*) FROM ai_attempts WHERE run_id=:id"), {"id": run}
                        )
                    claims = (
                        [
                            *output.get("rationale_claims", []),
                            *((output.get("draft") or {}).get("claims", [])),
                        ]
                        if output
                        else []
                    )
                    for claim in claims:
                        try:
                            citation = resolve_citation(
                                connection,
                                principal,
                                UUID(claim["evidence_id"].removeprefix("doc:")),
                                at=fixed_at,
                            )
                            evidence[claim["evidence_id"]] = (
                                slugs[str(citation.document_id)],
                                citation.text,
                            )
                        except (ValueError, PermissionError):
                            pass
                row = {
                    "phase": phase,
                    "repetition": repetition,
                    "ordinal": len(rows) + 1,
                    "arm": arm,
                    "case_id": case["id"],
                    "family": case["family"],
                    "split": case["split"],
                    "category": case["category"],
                    "expect_abstention": case["expect_abstention"],
                    "state": state,
                    "failure_code": failure,
                    "run_id": run,
                    "workflow_id": workflow,
                    "elapsed_ms": elapsed,
                    "provider_attempts": provider_attempts,
                    "output": output,
                    **classify(case, state, output, evidence),
                }
                rows.append(row)
                raw.write(json.dumps(row, default=str) + "\n")
                raw.flush()
    code_paths = [
        *Path("src/revenueos").glob("*.py"),
        Path("requirements.lock"),
        Path("frontend/package-lock.json"),
        Path("docs/21-comparison-acceptance.md"),
    ]
    if variant == "ablation":
        code_paths.append(Path("docs/27-improvements-acceptance.md"))
    report: dict[str, Any] = {
        "protocol": "four_arm_ablation_v2"
        if variant == "ablation"
        else "paired_synthetic_workflow_v1",
        "evidence_class": "synthetic_observed_software",
        "started_at": started.isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "runtime": {"python": sys.version, "platform": platform.platform(), "postgres": None},
        "evidence_at": fixed_at.isoformat(),
        "dataset_id": str(dataset),
        "organization_id": str(organization),
        "repetitions": repetitions,
        "seed": SEED,
        "split_scope": split_scope,
        "warmup_attempts": len(cases[:4]) * len(arms_to_run),
        "measured_attempts": len(cases) * repetitions * len(arms_to_run),
        "raw_attempts": len(rows),
        "fixture_hashes": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.glob("*.json")
        },
        "source_hashes": {
            p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in code_paths
        },
        "raw_sha256": hashlib.sha256(raw_path.read_bytes()).hexdigest(),
        "policy_version": POLICY_VERSION,
        "quality_counting": (
            "Unique first repetitions; technical failures never credited as abstentions."
        ),
        "overall": summarize(rows, arms_to_run),
        "splits": {
            split: summarize([row for row in rows if row["split"] == split], arms_to_run)
            for split in ("dev", "test")
        },
        "readiness": readiness,
        "queue_diagnostics": queues,
        "real_retrospective": {
            "status": "not_available",
            "reason": "No authorized real labels/as-of feature history.",
        },
        "actual_pilot": {
            "status": "not_run",
            "participants": 0,
            "human_task_times": None,
            "client_outcomes": None,
        },
        "costs": {
            "provider_attempts": sum(row["provider_attempts"] for row in rows),
            "model_calls": 0,
            "actual_invoice_usd": None,
            "hosting_usd": None,
            "labor_usd": None,
            "basis": "All arms use deterministic templates; no provider transport is configured.",
        },
        "limitations": [
            "Authored, previously seen cases; no new hidden holdout or independent annotation.",
            "One eligible synthetic lead shared across knowledge tasks; no operational rep study.",
            "Computation excludes human reading/review/rework; not human time savings.",
            "Only two serial repetitions, no concurrency/cold-start/network/load SLO claim.",
            "Family bootstrap describes fixture sensitivity, not population confidence.",
            "Baseline is a software proxy; human sales work and live LLM behavior unmeasured.",
        ],
    }
    with engine.connect() as connection:
        report["runtime"]["postgres"] = connection.scalar(text("SELECT version()"))
    report_path.write_text(json.dumps(report, default=str, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization", type=UUID, required=True)
    parser.add_argument("--dataset", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("legacy", "ablation"), default="legacy")
    parser.add_argument("--split", choices=("all", "dev", "test"), default="all")
    args = parser.parse_args()
    engine = get_engine()
    try:
        report = execute(
            engine,
            args.organization,
            args.dataset,
            Path("data/intelligence"),
            args.output,
            variant=args.variant,
            split_scope=args.split,
        )
        print(
            json.dumps(
                {key: report[key] for key in ("protocol", "raw_attempts", "costs")}, indent=2
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
