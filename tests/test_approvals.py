import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from revenueos.approvals import (
    assign_reviewer,
    decide_action,
    inspect_action,
    prepare_action,
    rehearse_action,
    revise_action,
)
from revenueos.audit import read_audit
from revenueos.evaluation import STEWARD
from revenueos.knowledge import Principal, revoke_document, search
from revenueos.workflows import run_workflow

pytestmark = pytest.mark.integration


def setup_action(engine: Engine, intelligence: tuple) -> tuple:
    dataset, requester = intelligence
    reviewer = Principal(organization_id=requester.organization_id, actor_id=STEWARD)
    with engine.begin() as connection:
        assign_reviewer(connection, reviewer, reviewer.actor_id)
        lead = connection.scalar(
            text("SELECT id FROM leads WHERE dataset_id=:id AND external_id='L1'"), {"id": dataset}
        )
    workflow = run_workflow(engine, requester, dataset, lead, "configuration checklist")
    action = prepare_action(engine, requester, UUID(workflow["workflow_id"]), "lead1@one.example")
    return requester, reviewer, action


def approve(engine: Engine, reviewer: Principal, action: dict) -> None:
    decide_action(
        engine,
        reviewer,
        UUID(action["action_id"]),
        action["version"],
        action["payload_hash"],
        "approve",
    )


def test_explicit_review_and_single_use_rehearsal(engine: Engine, intelligence: tuple) -> None:
    requester, reviewer, action = setup_action(engine, intelligence)
    action_id = UUID(action["action_id"])
    inspected = inspect_action(engine, reviewer, action_id)
    assert inspected["payload_hash"] == action["payload_hash"]
    assert inspected["payload"]["recipient"] == "lead1@one.example"
    with pytest.raises(PermissionError):
        rehearse_action(engine, reviewer, action_id, action["payload_hash"])
    with pytest.raises(PermissionError):
        approve(engine, requester, action)
    approve(engine, reviewer, action)
    result = rehearse_action(engine, reviewer, action_id, action["payload_hash"])
    assert not result["delivered"] and result["mode"] == "offline_rehearsal"
    with pytest.raises(PermissionError):
        rehearse_action(engine, reviewer, action_id, action["payload_hash"])
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM action_receipts")) == 1
        audit = read_audit(connection, reviewer)
    assert audit["chain_valid"] and any(row["outcome"] == "denied" for row in audit["events"])
    assert "lead1@one.example" not in json.dumps(audit, default=str)


def test_edit_invalidates_previous_approval(engine: Engine, intelligence: tuple) -> None:
    requester, reviewer, action = setup_action(engine, intelligence)
    approve(engine, reviewer, action)
    action_id = UUID(action["action_id"])
    revised = revise_action(engine, requester, action_id, 1, "What would you like to clarify?")
    assert revised["version"] == 2 and revised["payload_hash"] != action["payload_hash"]
    with pytest.raises(PermissionError):
        rehearse_action(engine, reviewer, action_id, action["payload_hash"])
    approve(engine, reviewer, revised)
    assert not rehearse_action(engine, reviewer, action_id, revised["payload_hash"])["delivered"]


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_hash",
        "wrong_version",
        "non_reviewer",
        "inactive",
        "rejected",
        "external_delivery",
        "expired",
        "revoked_source",
        "suppressed",
        "foreign_org",
    ],
)
def test_action_permission_and_freshness_boundaries(
    engine: Engine, intelligence: tuple, fault: str
) -> None:
    requester, reviewer, action = setup_action(engine, intelligence)
    action_id = UUID(action["action_id"])
    if fault == "wrong_hash":
        with pytest.raises(PermissionError):
            decide_action(engine, reviewer, action_id, 1, "x" * 64, "approve")
        return
    if fault == "wrong_version":
        with pytest.raises(PermissionError):
            decide_action(engine, reviewer, action_id, 99, action["payload_hash"], "approve")
        return
    if fault == "non_reviewer":
        with pytest.raises(PermissionError):
            approve(engine, requester, action)
        return
    if fault == "foreign_org":
        with pytest.raises(PermissionError):
            approve(engine, Principal(organization_id=uuid4(), actor_id=reviewer.actor_id), action)
        return
    if fault == "rejected":
        decide_action(engine, reviewer, action_id, 1, action["payload_hash"], "reject")
    else:
        approve(engine, reviewer, action)
    with engine.begin() as connection:
        if fault == "inactive":
            connection.execute(text("UPDATE workflow_reviewers SET active=false"))
        elif fault == "expired":
            connection.execute(
                text("UPDATE ai_runs SET created_at=:old"),
                {"old": datetime.now(UTC) - timedelta(hours=25)},
            )
        elif fault == "revoked_source":
            citation = search(connection, reviewer, "configuration checklist")[0]
            revoke_document(connection, reviewer, citation.version_id)
        elif fault == "suppressed":
            connection.execute(
                text("""
                INSERT INTO suppression_tombstones
                    (organization_id,source_system,lead_id,do_not_contact)
                SELECT organization_id,'synthetic_crm',lead_id,true FROM bounded_workflows
            """)
            )
    with pytest.raises(PermissionError):
        rehearse_action(
            engine,
            reviewer,
            action_id,
            action["payload_hash"],
            mode="send_email" if fault == "external_delivery" else "offline_rehearsal",
        )
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM action_receipts")) == 0


def test_concurrent_consumption_only_one_receipt(engine: Engine, intelligence: tuple) -> None:
    _, reviewer, action = setup_action(engine, intelligence)
    approve(engine, reviewer, action)

    def consume() -> str:
        try:
            rehearse_action(engine, reviewer, UUID(action["action_id"]), action["payload_hash"])
            return "rehearsed"
        except PermissionError:
            return "denied"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: consume(), range(2))) == ["denied", "rehearsed"]
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM action_receipts")) == 1
        assert read_audit(connection, reviewer)["chain_valid"]


def test_real_or_wrong_recipient_cannot_be_prepared(engine: Engine, intelligence: tuple) -> None:
    requester, _, action = setup_action(engine, intelligence)
    with engine.connect() as connection:
        workflow = connection.scalar(
            text("SELECT workflow_id FROM outreach_actions WHERE id=:id"),
            {"id": action["action_id"]},
        )
    for recipient in ("real@example.com", "another@one.example"):
        with pytest.raises(PermissionError):
            prepare_action(engine, requester, workflow, recipient)


def test_approvals_and_action_versions_are_immutable(engine: Engine, intelligence: tuple) -> None:
    _, reviewer, action = setup_action(engine, intelligence)
    approve(engine, reviewer, action)
    for table in ("action_approvals", "outreach_versions"):
        with pytest.raises(DBAPIError), engine.begin() as connection:
            connection.execute(text(f"DELETE FROM {table}"))
