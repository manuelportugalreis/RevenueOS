"""Idempotent synthetic requests and fail-closed interrupted-run reconciliation."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, text

from revenueos.approvals import prepare_action
from revenueos.audit import record
from revenueos.ingestion import digest
from revenueos.knowledge import Principal, authorize
from revenueos.recommendations import open_recommendation
from revenueos.web_auth import hashed
from revenueos.workflows import run_workflow


class RequestConflict(ValueError):
    pass


def _complete(
    engine: Engine, principal: Principal, key: UUID, workflow: dict[str, Any]
) -> dict[str, Any]:
    result = dict(workflow)
    if workflow["state"] == "review_pending":
        with engine.connect() as connection:
            open_recommendation(connection, principal, UUID(workflow["recommendation_id"]))
            row = connection.execute(
                text("""SELECT p.email FROM bounded_workflows w
                JOIN lead_private p ON (p.organization_id,p.dataset_id,p.lead_id)=
                    (w.organization_id,w.dataset_id,w.lead_id)
                WHERE w.organization_id=:org AND w.actor_id=:actor AND w.id=:id"""),
                {
                    "org": principal.organization_id,
                    "actor": principal.actor_id,
                    "id": workflow["workflow_id"],
                },
            ).one()
        action = prepare_action(
            engine, principal, UUID(workflow["workflow_id"]), row.email, reuse_existing=True
        )
        result["action"] = {k: v for k, v in action.items() if k != "payload"}
    result["request_key"] = str(key)
    with engine.begin() as connection:
        record(
            connection,
            principal,
            "web_request_completed",
            result["state"],
            {"key_hash": hashed(str(key))},
            UUID(workflow["workflow_id"]),
        )
        connection.execute(
            text("""UPDATE web_workflow_requests SET state='completed',
            response=CAST(:body AS jsonb),completed_at=now() WHERE organization_id=:org
            AND actor_id=:actor AND request_key=:key"""),
            {
                "body": json.dumps(result, default=str),
                "org": principal.organization_id,
                "actor": principal.actor_id,
                "key": key,
            },
        )
    return result


def submit_workflow(
    engine: Engine, principal: Principal, lead: UUID, query: str, key: UUID
) -> dict[str, Any]:
    payload_hash = digest({"lead_id": str(lead), "query": query})
    params = {"org": principal.organization_id, "actor": principal.actor_id, "key": key}
    lock_id = int(
        digest(
            {
                "org": str(principal.organization_id),
                "actor": str(principal.actor_id),
                "key": str(key),
            }
        )[:15],
        16,
    )
    with engine.connect() as lock:
        if not lock.scalar(text("SELECT pg_try_advisory_lock(:id)"), {"id": lock_id}):
            raise RequestConflict("request_in_progress")
        try:
            with engine.begin() as connection:
                authorize(connection, principal)
                row = (
                    connection.execute(
                        text("""SELECT * FROM web_workflow_requests
                    WHERE organization_id=:org AND actor_id=:actor AND request_key=:key"""),
                        params,
                    )
                    .mappings()
                    .first()
                )
                if row and row["payload_hash"] != payload_hash:
                    raise RequestConflict("idempotency_key_payload_mismatch")
                if row and row["state"] == "completed":
                    result = dict(row["response"])
                    if result.get("recommendation_id") and result["state"] == "review_pending":
                        open_recommendation(
                            connection, principal, UUID(result["recommendation_id"])
                        )
                    return result
                if row and row["state"] == "failed":
                    raise RequestConflict("interrupted_request_requires_new_key")
                if row:
                    if not row["workflow_id"]:
                        raise RequestConflict("unlinked_request_not_replayable")
                    work = (
                        connection.execute(
                            text("""SELECT * FROM bounded_workflows
                        WHERE organization_id=:org AND actor_id=:actor AND id=:id"""),
                            {**params, "id": row["workflow_id"]},
                        )
                        .mappings()
                        .one()
                    )
                    if work["state"] not in ("review_pending", "abstained", "failed"):
                        raise RequestConflict("request_needs_reconciliation")
                    terminal = {
                        "workflow_id": str(work["id"]),
                        "state": work["state"],
                        "failure_code": work["failure_code"],
                        "recommendation_id": str(work["recommendation_id"])
                        if work["recommendation_id"]
                        else None,
                        "external_delivery_enabled": False,
                        "policy_version": work["policy_version"],
                    }
                else:
                    connection.execute(
                        text("SELECT id FROM organizations WHERE id=:org FOR UPDATE"), params
                    )
                    quota = hashed(f"workflow:{principal.organization_id}:{principal.actor_id}")
                    count = connection.scalar(
                        text("""SELECT count(*) FROM web_login_attempts
                        WHERE key_hash=:key AND occurred_at>now()-interval '1 minute'"""),
                        {"key": quota},
                    )
                    if count >= 10:
                        raise RequestConflict("workflow_rate_limited")
                    connection.execute(
                        text("INSERT INTO web_login_attempts(key_hash) VALUES(:key)"),
                        {"key": quota},
                    )
                    dataset = connection.scalar(
                        text("SELECT id FROM current_datasets WHERE organization_id=:org"), params
                    )
                    if not dataset:
                        raise RequestConflict("no_dataset")
                    connection.execute(
                        text("""INSERT INTO web_workflow_requests
                        (organization_id,actor_id,request_key,payload_hash)
                        VALUES(:org,:actor,:key,:hash)"""),
                        {**params, "hash": payload_hash},
                    )
                    terminal = None
            if terminal:
                return _complete(engine, principal, key, terminal)

            def bind(workflow: UUID) -> None:
                with engine.begin() as connection:
                    connection.execute(
                        text("""UPDATE web_workflow_requests SET workflow_id=:id
                        WHERE organization_id=:org AND actor_id=:actor AND request_key=:key"""),
                        {**params, "id": workflow},
                    )

            try:
                result = run_workflow(engine, principal, dataset, lead, query, on_started=bind)
                return _complete(engine, principal, key, result)
            except Exception:
                # Preserve linked terminal output for safe preparation recovery; never regenerate.
                with engine.begin() as connection:
                    connection.execute(
                        text("""UPDATE web_workflow_requests SET state='failed',
                        failure_code='request_interrupted' WHERE organization_id=:org
                        AND actor_id=:actor AND request_key=:key AND workflow_id IS NULL"""),
                        params,
                    )
                raise
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:id)"), {"id": lock_id})
            lock.commit()


def reconcile_interrupted(
    engine: Engine, steward: Principal, age_minutes: int = 15
) -> dict[str, int]:
    if not 5 <= age_minutes <= 1440:
        raise ValueError("reconciliation_age_out_of_bounds")
    cutoff = datetime.now(UTC) - timedelta(minutes=age_minutes)
    count = 0
    with engine.begin() as connection:
        authorize(connection, steward, steward=True)
        record(
            connection,
            steward,
            "reconciliation_started",
            "maintenance",
            {"cutoff": cutoff.isoformat()},
        )
        rows = (
            connection.execute(
                text("""SELECT id FROM bounded_workflows
            WHERE organization_id=:org AND state IN ('planning','reading','recommending')
              AND created_at<:cutoff FOR UPDATE"""),
                {"org": steward.organization_id, "cutoff": cutoff},
            )
            .scalars()
            .all()
        )
        for workflow in rows:
            connection.execute(
                text("""UPDATE bounded_workflows SET state='failed',
                failure_code='interrupted_reconciled',completed_at=now() WHERE id=:id"""),
                {"id": workflow},
            )
            record(connection, steward, "workflow_reconciled", "failed_no_retry", {}, workflow)
            count += 1
        connection.execute(
            text("""UPDATE ai_attempts SET state='usage_unknown',
            outcome='interrupted_reservation_retained'
            WHERE organization_id=:org AND state='reserved'
            AND run_id IN (SELECT id FROM ai_runs WHERE organization_id=:org AND state='running'
                           AND created_at<:cutoff)"""),
            {"org": steward.organization_id, "cutoff": cutoff},
        )
        connection.execute(
            text("""UPDATE ai_runs SET state='failed',failure_code='interrupted_reconciled',
            completed_at=now() WHERE organization_id=:org
            AND state='running' AND created_at<:cutoff"""),
            {"org": steward.organization_id, "cutoff": cutoff},
        )
        connection.execute(
            text("""UPDATE web_workflow_requests SET state='failed',
            failure_code='unlinked_interrupted',completed_at=now() WHERE organization_id=:org
            AND workflow_id IS NULL AND state='pending' AND created_at<:cutoff"""),
            {"org": steward.organization_id, "cutoff": cutoff},
        )
    return {"workflows_failed_without_retry": count, "external_actions": 0}
