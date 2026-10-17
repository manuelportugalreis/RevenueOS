"""Explicit human review and one-use offline rehearsal. No external delivery adapters."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import Connection, Engine, text

from revenueos.audit import record
from revenueos.ingestion import digest
from revenueos.knowledge import Principal, authorize, resolve_citation
from revenueos.recommendations import Recommendation, open_recommendation


def assign_reviewer(connection: Connection, steward: Principal, actor: UUID) -> None:
    authorize(connection, steward, steward=True)
    authorize(connection, Principal(organization_id=steward.organization_id, actor_id=actor))
    record(connection, steward, "reviewer_assigned", "active", {"actor": str(actor)})
    connection.execute(
        text("""
        INSERT INTO workflow_reviewers(organization_id,actor_id) VALUES(:org,:actor)
        ON CONFLICT(organization_id,actor_id) DO UPDATE SET active=true
    """),
        {"org": steward.organization_id, "actor": actor},
    )


def _reviewer(connection: Connection, principal: Principal) -> None:
    authorize(connection, principal)
    allowed = connection.scalar(
        text("""
        SELECT 1 FROM workflow_reviewers WHERE organization_id=:org AND actor_id=:actor AND active
    """),
        {"org": principal.organization_id, "actor": principal.actor_id},
    )
    if not allowed:
        raise PermissionError("explicit_human_reviewer_role_required")


def _locked(connection: Connection, principal: Principal, action: UUID) -> dict[str, Any]:
    # Audit and action operations share org-first lock order to avoid inversion.
    connection.execute(
        text("SELECT id FROM organizations WHERE id=:org FOR UPDATE"),
        {"org": principal.organization_id},
    )
    row = (
        connection.execute(
            text("""
        SELECT a.*,w.actor_id,w.dataset_id,w.lead_id,w.recommendation_id
        FROM outreach_actions a JOIN bounded_workflows w ON w.id=a.workflow_id
        WHERE a.organization_id=:org AND a.id=:id FOR UPDATE OF a
    """),
            {"org": principal.organization_id, "id": action},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise PermissionError("action_not_accessible")
    return dict(row)


def _proposal(
    connection: Connection, principal: Principal, row: dict[str, Any], now: datetime
) -> Recommendation:
    # Reviewers may review another requester's proposal only through this trusted server path.
    _ = open_recommendation(
        connection,
        Principal(organization_id=principal.organization_id, actor_id=row["actor_id"]),
        row["recommendation_id"],
        now=now,
    )
    parsed = Recommendation.model_validate(_["recommendation"])
    for claim in [*parsed.rationale_claims, *(parsed.draft.claims if parsed.draft else [])]:
        resolve_citation(
            connection, principal, UUID(claim.evidence_id.removeprefix("doc:")), at=now
        )
    return parsed


def _payload(
    connection: Connection, principal: Principal, row: dict[str, Any], recipient: str, now: datetime
) -> dict[str, Any]:
    recommendation = _proposal(connection, principal, row, now)
    if recommendation.draft is None:
        raise ValueError("no_outreach_draft")
    email = connection.scalar(
        text("""
        SELECT email FROM lead_private WHERE organization_id=:org AND dataset_id=:dataset
          AND lead_id=:lead
    """),
        {"org": principal.organization_id, "dataset": row["dataset_id"], "lead": row["lead_id"]},
    )
    if (
        recipient != email
        or not re.fullmatch(r"[^\s@]+@[^\s@]+\.(example|invalid)", recipient)
        or len(recipient) > 254
    ):
        raise PermissionError("recipient_must_match_synthetic_crm_contact")
    draft = recommendation.draft
    return {
        "kind": "email_draft",
        "recipient": recipient,
        "subject": draft.subject,
        "body": "\n\n".join(
            [draft.opening, *[claim.text for claim in draft.claims], draft.closing]
        ),
        "recommendation_id": str(row["recommendation_id"]),
        "recommendation_hash": digest(recommendation.model_dump(mode="json")),
        "evidence_ids": sorted({claim.evidence_id for claim in draft.claims}),
    }


def prepare_action(
    engine: Engine,
    principal: Principal,
    workflow: UUID,
    recipient: str,
    *,
    reuse_existing: bool = False,
) -> dict[str, Any]:
    with engine.begin() as connection:
        authorize(connection, principal)
        connection.execute(
            text("SELECT id FROM organizations WHERE id=:org FOR UPDATE"),
            {"org": principal.organization_id},
        )
        row = (
            connection.execute(
                text("""
            SELECT * FROM bounded_workflows WHERE organization_id=:org AND id=:id
              AND actor_id=:actor AND state='review_pending'
        """),
                {"org": principal.organization_id, "id": workflow, "actor": principal.actor_id},
            )
            .mappings()
            .first()
        )
        if row is None:
            raise PermissionError("workflow_not_ready_or_owned")
        payload = _payload(connection, principal, dict(row), recipient, datetime.now(UTC))
        existing = connection.scalar(
            text("SELECT id FROM outreach_actions WHERE workflow_id=:id"), {"id": workflow}
        )
        if existing:
            if reuse_existing:
                version = (
                    connection.execute(
                        text("""SELECT v.version,v.payload_hash,a.state
                    FROM outreach_actions a JOIN outreach_versions v
                      ON (v.organization_id,v.action_id,v.version)=
                         (a.organization_id,a.id,a.current_version)
                    WHERE a.organization_id=:org AND a.id=:id"""),
                        {"org": principal.organization_id, "id": existing},
                    )
                    .mappings()
                    .one()
                )
                return {
                    "action_id": str(existing),
                    "version": version["version"],
                    "payload_hash": version["payload_hash"],
                    "state": version["state"],
                    "external_delivery_enabled": False,
                }
            raise ValueError("action_already_exists_use_revision")
        action = uuid4()
        connection.execute(
            text("""
            INSERT INTO outreach_actions(id,organization_id,workflow_id,state)
            VALUES(:id,:org,:workflow,'pending')
        """),
            {"id": action, "org": principal.organization_id, "workflow": workflow},
        )
        _insert_version(connection, principal, action, 1, payload)
        record(connection, principal, "action_prepared", "pending", payload, workflow)
        return {
            "action_id": str(action),
            "version": 1,
            "payload": payload,
            "payload_hash": digest(payload),
            "approved": False,
            "external_delivery_enabled": False,
        }


def _insert_version(
    connection: Connection,
    principal: Principal,
    action: UUID,
    version: int,
    payload: dict[str, Any],
) -> None:
    connection.execute(
        text("""
        INSERT INTO outreach_versions(organization_id,action_id,version,kind,recipient,message,
          payload_hash,expires_at,created_by)
        VALUES(:org,:action,:version,'email_draft',:recipient,
          CAST(:message AS jsonb),:hash,:expiry,:actor)
    """),
        {
            "org": principal.organization_id,
            "action": action,
            "version": version,
            "recipient": payload["recipient"],
            "message": json.dumps(payload),
            "hash": digest(payload),
            "expiry": datetime.now(UTC) + timedelta(hours=24),
            "actor": principal.actor_id,
        },
    )


def revise_action(
    engine: Engine,
    principal: Principal,
    action: UUID,
    expected_version: int,
    closing: Literal["Would a short discussion be useful?", "What would you like to clarify?"],
) -> dict[str, Any]:
    if closing not in ("Would a short discussion be useful?", "What would you like to clarify?"):
        raise ValueError("only_validated_closing_edit_supported")
    with engine.begin() as connection:
        authorize(connection, principal)
        row = _locked(connection, principal, action)
        if (
            row["actor_id"] != principal.actor_id
            or row["current_version"] != expected_version
            or row["state"] == "rehearsed"
        ):
            raise PermissionError("stale_or_unauthorized_revision")
        old = (
            connection.execute(
                text("""
            SELECT * FROM outreach_versions
            WHERE organization_id=:org AND action_id=:action AND version=:v
        """),
                {"org": principal.organization_id, "action": action, "v": expected_version},
            )
            .mappings()
            .one()
        )
        payload = _payload(connection, principal, row, old["recipient"], datetime.now(UTC))
        paragraphs = payload["body"].split("\n\n")
        paragraphs[-1] = closing
        payload["body"] = "\n\n".join(paragraphs)
        version = expected_version + 1
        _insert_version(connection, principal, action, version, payload)
        record(connection, principal, "action_revised", "pending", payload, row["workflow_id"])
        connection.execute(
            text("UPDATE outreach_actions SET current_version=:v,state='pending' WHERE id=:id"),
            {"v": version, "id": action},
        )
        return {
            "action_id": str(action),
            "version": version,
            "payload": payload,
            "payload_hash": digest(payload),
            "approved": False,
        }


def _current_version(
    connection: Connection, principal: Principal, action: UUID, version: int, expected_hash: str
) -> dict[str, Any]:
    row = (
        connection.execute(
            text("""
        SELECT * FROM outreach_versions WHERE organization_id=:org AND action_id=:id AND version=:v
    """),
            {"org": principal.organization_id, "id": action, "v": version},
        )
        .mappings()
        .one()
    )
    if row["payload_hash"] != expected_hash or digest(row["message"]) != expected_hash:
        raise PermissionError("payload_hash_mismatch")
    if row["expires_at"] <= datetime.now(UTC):
        raise PermissionError("action_expired")
    return dict(row)


def decide_action(
    engine: Engine,
    human: Principal,
    action: UUID,
    version: int,
    expected_hash: str,
    decision: Literal["approve", "reject"],
) -> dict[str, Any]:
    if decision not in ("approve", "reject"):
        raise ValueError("invalid_review_decision")
    denied = False
    with engine.begin() as connection:
        # Denials are committed, not lost through exception rollback.
        row = _locked(connection, human, action)
        try:
            _reviewer(connection, human)
            if row["current_version"] != version or row["state"] != "pending":
                raise PermissionError("stale_or_terminal_action")
            source = _current_version(connection, human, action, version, expected_hash)
            current_proposal = _proposal(connection, human, row, datetime.now(UTC))
            if (
                digest(current_proposal.model_dump(mode="json"))
                != source["message"]["recommendation_hash"]
            ):
                raise PermissionError("recommendation_changed")
            approval = uuid4()
            connection.execute(
                text("""
                INSERT INTO action_approvals(id,organization_id,action_id,version,payload_hash,
                  reviewer_id,decision,decided_at,expires_at)
                VALUES(:id,:org,:action,:v,:hash,:reviewer,:decision,now(),:expiry)
            """),
                {
                    "id": approval,
                    "org": human.organization_id,
                    "action": action,
                    "v": version,
                    "hash": expected_hash,
                    "reviewer": human.actor_id,
                    "decision": decision,
                    "expiry": source["expires_at"],
                },
            )
            connection.execute(
                text("UPDATE outreach_actions SET state=:state WHERE id=:id"),
                {"state": "approved" if decision == "approve" else "rejected", "id": action},
            )
            record(
                connection,
                human,
                "human_review",
                decision,
                {"hash": expected_hash},
                row["workflow_id"],
            )
        except (ValueError, PermissionError):
            denied = True
            record(
                connection,
                human,
                "human_review",
                "denied",
                {"version": version},
                row["workflow_id"],
            )
    if denied:
        raise PermissionError("human_review_denied")
    return {
        "action_id": str(action),
        "version": version,
        "decision": decision,
        "external_delivery_enabled": False,
    }


def inspect_action(engine: Engine, human: Principal, action: UUID) -> dict[str, Any]:
    with engine.begin() as connection:
        _reviewer(connection, human)
        row = _locked(connection, human, action)
        _proposal(connection, human, row, datetime.now(UTC))
        version = (
            connection.execute(
                text("""
            SELECT * FROM outreach_versions
            WHERE organization_id=:org AND action_id=:id AND version=:v
        """),
                {"org": human.organization_id, "id": action, "v": row["current_version"]},
            )
            .mappings()
            .one()
        )
        record(
            connection,
            human,
            "action_inspected",
            "reviewable",
            version["payload_hash"],
            row["workflow_id"],
        )
        return {
            "action_id": str(action),
            "version": row["current_version"],
            "state": row["state"],
            "payload": version["message"],
            "payload_hash": version["payload_hash"],
            "expires_at": version["expires_at"].isoformat(),
            "external_delivery_enabled": False,
        }


def rehearse_action(
    engine: Engine,
    human: Principal,
    action: UUID,
    expected_hash: str,
    *,
    mode: str = "offline_rehearsal",
) -> dict[str, Any]:
    denied = False
    receipt = None
    with engine.begin() as connection:
        row = _locked(connection, human, action)
        try:
            _reviewer(connection, human)
            if mode != "offline_rehearsal" or row["state"] != "approved":
                raise PermissionError("delivery_disabled_or_approval_missing")
            version = _current_version(
                connection, human, action, row["current_version"], expected_hash
            )
            current_proposal = _proposal(connection, human, row, datetime.now(UTC))
            if (
                digest(current_proposal.model_dump(mode="json"))
                != version["message"]["recommendation_hash"]
            ):
                raise PermissionError("recommendation_changed")
            approval = (
                connection.execute(
                    text("""
                SELECT * FROM action_approvals WHERE organization_id=:org AND action_id=:id
                  AND version=:v AND decision='approve' AND expires_at>now()
            """),
                    {"org": human.organization_id, "id": action, "v": row["current_version"]},
                )
                .mappings()
                .first()
            )
            if approval is None or approval["payload_hash"] != version["payload_hash"]:
                raise PermissionError("approval_not_valid_for_current_payload")
            _reviewer(
                connection,
                Principal(organization_id=human.organization_id, actor_id=approval["reviewer_id"]),
            )
            receipt = {
                "id": uuid4(),
                "org": human.organization_id,
                "action": action,
                "approval": approval["id"],
                "hash": expected_hash,
            }
            connection.execute(
                text("""
                INSERT INTO action_receipts(id,organization_id,action_id,approval_id,payload_hash,
                  mode,delivered,created_at)
                VALUES(:id,:org,:action,:approval,:hash,'offline_rehearsal',false,now())
            """),
                receipt,
            )
            connection.execute(
                text("UPDATE outreach_actions SET state='rehearsed' WHERE id=:id"), {"id": action}
            )
            record(
                connection,
                human,
                "action_consumed",
                "offline_rehearsal",
                receipt,
                row["workflow_id"],
            )
        except (ValueError, PermissionError):
            denied = True
            record(
                connection,
                human,
                "action_consumed",
                "denied",
                {"mode_hash": digest(mode)},
                row["workflow_id"],
            )
    if denied:
        raise PermissionError("action_rehearsal_denied")
    assert receipt is not None
    return {
        "receipt_id": str(receipt["id"]),
        "action_id": str(action),
        "mode": "offline_rehearsal",
        "delivered": False,
    }
