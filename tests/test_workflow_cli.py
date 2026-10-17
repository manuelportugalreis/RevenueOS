"""Exercise the trusted operator interface with a synthetic reviewer persona."""

import json
import subprocess
import sys

import pytest
from sqlalchemy import Engine, text

from revenueos.evaluation import STEWARD

pytestmark = pytest.mark.integration


def test_offline_operator_flow(engine: Engine, intelligence: tuple) -> None:
    dataset, requester = intelligence
    with engine.connect() as connection:
        lead = connection.scalar(
            text("SELECT id FROM leads WHERE dataset_id=:id AND external_id='L1'"),
            {"id": dataset},
        )

    def invoke(command: str, *args: object, actor: object = requester.actor_id) -> dict:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "revenueos.workflow_cli",
                command,
                "--organization",
                str(requester.organization_id),
                "--actor",
                str(actor),
                *map(str, args),
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return json.loads(result.stdout)

    schemas = subprocess.run(
        [sys.executable, "-m", "revenueos.workflow_cli", "schemas"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert len(json.loads(schemas.stdout)) == 4
    workflow = invoke(
        "run", "--dataset", dataset, "--lead", lead, "--query", "configuration checklist"
    )
    assert workflow["state"] == "review_pending"
    action = invoke(
        "prepare", "--workflow", workflow["workflow_id"], "--recipient", "lead1@one.example"
    )
    invoke("assign-reviewer", "--reviewer", STEWARD, actor=STEWARD)
    inspected = invoke("inspect", "--action", action["action_id"], actor=STEWARD)
    assert inspected["payload_hash"] == action["payload_hash"]
    invoke(
        "review",
        "--action",
        action["action_id"],
        "--version",
        1,
        "--hash",
        action["payload_hash"],
        "--decision",
        "approve",
        actor=STEWARD,
    )
    receipt = invoke(
        "rehearse", "--action", action["action_id"], "--hash", action["payload_hash"], actor=STEWARD
    )
    assert receipt["delivered"] is False
    assert invoke("audit", actor=STEWARD)["chain_valid"]
    denied = subprocess.run(
        [
            sys.executable,
            "-m",
            "revenueos.workflow_cli",
            "rehearse",
            "--organization",
            str(requester.organization_id),
            "--actor",
            str(STEWARD),
            "--action",
            action["action_id"],
            "--hash",
            action["payload_hash"],
        ],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert denied.returncode == 2 and "denied" in denied.stderr
    assert "Traceback" not in denied.stderr
