"""Versioned attention-priority points. These scores are not conversion probabilities."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict
from sqlalchemy import Connection, text

from revenueos.ingestion import digest


class RulesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["attention_v1"] = "attention_v1"
    target_employee_bands: tuple[str, ...] = ("11-50", "51-200")
    contact_coverage_start: AwareDatetime | None = None
    coverage_attestation: str | None = None

    @property
    def config_hash(self) -> str:
        return digest(self.model_dump(mode="json"))


def lead_context(
    connection: Connection, organization: UUID, dataset: UUID, lead: UUID
) -> dict[str, Any]:
    row = (
        connection.execute(
            text("""
        SELECT l.*,a.employee_band,p.lawful_use_status,d.observed_at,d.data_mode,d.source_system
        FROM leads l JOIN datasets d ON (d.organization_id,d.id)=(l.organization_id,l.dataset_id)
        LEFT JOIN accounts a ON (a.organization_id,a.dataset_id,a.id)=
          (l.organization_id,l.dataset_id,l.account_id)
        JOIN lead_private p ON (p.organization_id,p.dataset_id,p.lead_id)=
          (l.organization_id,l.dataset_id,l.id)
        WHERE l.organization_id=:org AND l.dataset_id=:dataset AND l.id=:lead
    """),
            {"org": organization, "dataset": dataset, "lead": lead},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise ValueError("lead_not_found_in_snapshot")
    result = dict(row)
    # No names, email, freeform notes, opportunities, or outcome labels in scoring/model context.
    result["interactions"] = [
        dict(event)
        for event in connection.execute(
            text("""
        SELECT id,occurred_at,direction,actor_type FROM interactions
        WHERE organization_id=:org AND dataset_id=:dataset AND lead_id=:lead
        ORDER BY occurred_at,id
    """),
            {"org": organization, "dataset": dataset, "lead": lead},
        ).mappings()
    ]
    suppression = (
        connection.execute(
            text("""
        SELECT do_not_contact,deleted_at FROM suppression_tombstones
        WHERE organization_id=:org AND source_system=:source AND lead_id=:lead
    """),
            {"org": organization, "source": row["source_system"], "lead": lead},
        )
        .mappings()
        .first()
    )
    result["currently_suppressed"] = bool(
        suppression and (suppression["do_not_contact"] or suppression["deleted_at"])
    )
    return result


def score_context(
    context: dict[str, Any], config: RulesConfig | None = None, as_of: datetime | None = None
) -> dict[str, Any]:
    config = config or RulesConfig()
    observed: datetime = context["observed_at"]
    as_of = as_of or observed
    if as_of.tzinfo is None or as_of != observed:
        raise ValueError("scoring_requires_exact_snapshot_as_of")
    exclusions = []
    for condition, reason in (
        (context["source"] in ("test", "internal"), "test_or_internal"),
        (context["status"] == "disqualified", "disqualified"),
        (context["deleted_at"] is not None, "deleted"),
        (context["do_not_contact"], "do_not_contact"),
        (context.get("currently_suppressed", False), "current_suppression_tombstone"),
    ):
        if condition:
            exclusions.append(reason)
    warnings = ["declared_use_case_match_unavailable_in_crm_v1"]
    if context["employee_band"] is None:
        warnings.append("company_size_unknown")
    if context["lawful_use_status"] != "approved":
        warnings.append("lawful_use_not_approved_no_draft")
    human = [
        event
        for event in context["interactions"]
        if event["actor_type"] == "human" and context["created_at"] <= event["occurred_at"] <= as_of
    ]
    inbound = [
        context["created_at"],
        *[event["occurred_at"] for event in human if event["direction"] == "inbound"],
    ]
    outbound = [event["occurred_at"] for event in human if event["direction"] == "outbound"]
    last_outbound = max(outbound, default=datetime.min.replace(tzinfo=UTC))
    unanswered = [instant for instant in inbound if instant > last_outbound]
    oldest_unanswered = min(unanswered) if unanswered else None
    covered = bool(
        config.contact_coverage_start
        and config.coverage_attestation
        and config.contact_coverage_start <= context["created_at"]
    )
    if not covered:
        warnings.append("contact_coverage_unattested_time_penalties_disabled")
    recent_inbound = any(
        event["direction"] == "inbound" and event["occurred_at"] >= as_of - timedelta(days=7)
        for event in human
    )
    last_human = max((event["occurred_at"] for event in human), default=None)
    last_activity = max(context["created_at"], last_human) if last_human else context["created_at"]
    points = {
        "explicit_demo_request": 30 if context["source"] == "demo_request" else 0,
        "recent_human_inbound_7d": 20 if recent_inbound else 0,
        "target_company_size": 15
        if context["employee_band"] in config.target_employee_bands
        else 0,
        "declared_use_case_match": 0,
        "unanswered_over_24h": 10
        if covered
        and oldest_unanswered is not None
        and as_of - oldest_unanswered > timedelta(hours=24)
        else 0,
        "inactive_over_30d": -15 if covered and as_of - last_activity > timedelta(days=30) else 0,
    }
    eligible = not exclusions
    return {
        "lead_id": str(context["id"]),
        "dataset_id": str(context["dataset_id"]),
        "as_of": as_of.isoformat(),
        "ruleset_version": config.version,
        "config_hash": config.config_hash,
        "config": config.model_dump(mode="json"),
        "eligible": eligible,
        "points": max(0, min(100, sum(points.values()))) if eligible else 0,
        "components": points,
        "exclusions": exclusions,
        "warnings": warnings,
        "oldest_unanswered_at": oldest_unanswered.isoformat() if oldest_unanswered else None,
        "evidence": {
            "source": context["source"],
            "employee_band": context["employee_band"],
            "last_known_human_activity": last_human.isoformat() if last_human else None,
            "inbound_acquisition_at": context["created_at"].isoformat(),
            "human_interaction_ids": [str(event["id"]) for event in human],
            "crm_reference": f"crm:{context['dataset_id']}:{context['id']}",
        },
        "interpretation": (
            "Attention-priority points; not a probability or measured predictive skill."
        ),
        "policy_note": "Current tombstones can exclude historical snapshot leads for safety.",
    }


def rank_leads(
    connection: Connection,
    organization: UUID,
    dataset: UUID,
    config: RulesConfig | None = None,
    *,
    persist: bool = False,
) -> dict[str, Any]:
    exists = connection.scalar(
        text("SELECT 1 FROM datasets WHERE organization_id=:org AND id=:id"),
        {"org": organization, "id": dataset},
    )
    if not exists:
        raise ValueError("dataset_not_found_in_organization")
    contexts = {
        str(row["id"]): {**dict(row), "interactions": []}
        for row in connection.execute(
            text("""SELECT l.*,a.employee_band,p.lawful_use_status,
            d.observed_at,d.data_mode,d.source_system,
            coalesce(s.do_not_contact OR s.deleted_at IS NOT NULL,false) AS currently_suppressed
            FROM leads l JOIN datasets d
              ON (d.organization_id,d.id)=(l.organization_id,l.dataset_id)
            LEFT JOIN accounts a ON (a.organization_id,a.dataset_id,a.id)=
                (l.organization_id,l.dataset_id,l.account_id)
            JOIN lead_private p ON (p.organization_id,p.dataset_id,p.lead_id)=
                (l.organization_id,l.dataset_id,l.id)
            LEFT JOIN suppression_tombstones s ON (s.organization_id,s.source_system,s.lead_id)=
                (l.organization_id,d.source_system,l.id)
            WHERE l.organization_id=:org AND l.dataset_id=:id ORDER BY l.id"""),
            {"org": organization, "id": dataset},
        ).mappings()
    }
    for event in connection.execute(
        text("""SELECT lead_id,id,occurred_at,direction,actor_type
        FROM interactions WHERE organization_id=:org AND dataset_id=:id
        ORDER BY lead_id,occurred_at,id"""),
        {"org": organization, "id": dataset},
    ).mappings():
        if str(event["lead_id"]) in contexts:
            contexts[str(event["lead_id"])]["interactions"].append(
                {key: event[key] for key in ("id", "occurred_at", "direction", "actor_type")}
            )
    scores = [score_context(context, config) for context in contexts.values()]
    eligible = [score for score in scores if score["eligible"]]
    eligible.sort(
        key=lambda score: (
            -score["points"],
            score["oldest_unanswered_at"] or "9999",
            score["lead_id"],
        )
    )
    fifo = sorted(
        eligible, key=lambda score: (contexts[score["lead_id"]]["created_at"], score["lead_id"])
    )
    newest = sorted(
        eligible,
        key=lambda score: (-contexts[score["lead_id"]]["created_at"].timestamp(), score["lead_id"]),
    )
    shuffled = sorted(score["lead_id"] for score in eligible)
    random.Random(42).shuffle(shuffled)
    if persist:
        for score in scores:
            connection.execute(
                text("""
                INSERT INTO score_runs(id,organization_id,dataset_id,lead_id,as_of,ruleset_version,
                  config_hash,eligible,points,explanation)
                VALUES(:id,:org,:dataset,:lead,:as_of,:version,:hash,:eligible,:points,
                  CAST(:body AS jsonb))
            """),
                {
                    "id": uuid4(),
                    "org": organization,
                    "dataset": dataset,
                    "lead": UUID(score["lead_id"]),
                    "as_of": score["as_of"],
                    "version": score["ruleset_version"],
                    "hash": score["config_hash"],
                    "eligible": score["eligible"],
                    "points": score["points"],
                    "body": json.dumps(score),
                },
            )
    return {
        "scores": scores,
        "queues": {
            "rules": [score["lead_id"] for score in eligible],
            "fifo": [score["lead_id"] for score in fifo],
            "newest_first": [score["lead_id"] for score in newest],
            "random_seed_42": shuffled,
        },
    }


def predictive_readiness(
    connection: Connection, organization: UUID, dataset: UUID
) -> dict[str, Any]:
    row = (
        connection.execute(
            text("""
        SELECT d.data_mode,d.observed_at,
          (SELECT count(*) FROM datasets WHERE organization_id=d.organization_id) AS snapshots,
          count(l.id) AS leads,
          count(o.lead_id) AS recorded_outcomes,
          count(*) FILTER(WHERE o.observation_complete AND
            o.observed_through >= l.created_at + interval '30 days') AS complete_outcomes,
          count(*) FILTER(WHERE o.observation_complete AND
            o.observed_through >= l.created_at + interval '30 days' AND
            o.qualified_at BETWEEN l.created_at
            AND l.created_at + interval '30 days') AS mature_dated_positives,
          count(*) FILTER(WHERE l.source_updated_at > l.created_at) AS updated_after_creation
        FROM datasets d LEFT JOIN leads l
          ON (l.organization_id,l.dataset_id)=(d.organization_id,d.id)
        LEFT JOIN lead_outcomes o ON (o.organization_id,o.dataset_id,o.lead_id)=
          (l.organization_id,l.dataset_id,l.id)
        WHERE d.organization_id=:org AND d.id=:dataset GROUP BY d.id
    """),
            {"org": organization, "dataset": dataset},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise ValueError("dataset_not_found_in_organization")
    reasons = [
        "no_verified_pre_outcome_feature_snapshots",
        "no_locked_time_account_disjoint_holdout",
        "no_independent_business_label_audit",
    ]
    if row["data_mode"] == "synthetic":
        reasons.insert(0, "synthetic_labels_are_not_business_outcomes")
    if row["complete_outcomes"] < 1000 or row["mature_dated_positives"] < 100:
        reasons.append("below_proposed_mature_label_screen")
    return {
        "model_training_allowed": False,
        "decision": "retain_rules_baseline",
        "counts": {key: value for key, value in row.items() if key != "observed_at"},
        "reasons": reasons,
        "predictive_accuracy": None,
        "note": "Readiness screen; passing a count heuristic alone cannot authorize training.",
    }
