"""Redacted append-only audit chain. Database administrators remain a trusted boundary."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, text

from revenueos.ingestion import digest
from revenueos.knowledge import Principal, authorize


def record(
    connection: Connection,
    principal: Principal,
    event: str,
    outcome: str,
    subject: Any,
    workflow: UUID | None = None,
) -> None:
    # Same first lock everywhere: serializes sequence allocation and approval consumption.
    connection.execute(
        text("SELECT id FROM organizations WHERE id=:org FOR UPDATE"),
        {"org": principal.organization_id},
    )
    previous = (
        connection.execute(
            text("""
        SELECT sequence,event_hash FROM workflow_audit WHERE organization_id=:org
        ORDER BY sequence DESC LIMIT 1
    """),
            {"org": principal.organization_id},
        )
        .mappings()
        .first()
    )
    body = {
        "organization_id": str(principal.organization_id),
        "sequence": previous["sequence"] + 1 if previous else 1,
        "workflow_id": str(workflow) if workflow else None,
        "actor_id": str(principal.actor_id),
        "event": event,
        "outcome": outcome,
        "subject_hash": digest(subject),
        "previous_hash": previous["event_hash"] if previous else "0" * 64,
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    connection.execute(
        text("""
        INSERT INTO workflow_audit(organization_id,sequence,workflow_id,actor_id,event,outcome,
          subject_hash,previous_hash,event_hash,occurred_at)
        VALUES(:organization_id,:sequence,:workflow_id,:actor_id,:event,:outcome,
          :subject_hash,:previous_hash,:event_hash,:occurred_at)
    """),
        {**body, "event_hash": digest(body)},
    )


def read_audit(
    connection: Connection, principal: Principal, workflow: UUID | None = None
) -> dict[str, Any]:
    authorize(connection, principal, steward=True)
    rows = [
        dict(row)
        for row in connection.execute(
            text("""
        SELECT * FROM workflow_audit WHERE organization_id=:org ORDER BY sequence
    """),
            {"org": principal.organization_id},
        ).mappings()
    ]
    previous = "0" * 64
    valid = True
    for sequence, row in enumerate(rows, 1):
        body = {
            key: (
                str(value)
                if isinstance(value, UUID)
                else value.isoformat()
                if isinstance(value, datetime)
                else value
            )
            for key, value in row.items()
            if key != "event_hash"
        }
        valid = valid and row["sequence"] == sequence and row["previous_hash"] == previous
        valid = valid and digest(body) == row["event_hash"]
        previous = row["event_hash"]
    return {
        "chain_valid": valid,
        "total_events": len(rows),
        "events": [row for row in rows if workflow is None or row["workflow_id"] == workflow],
    }
