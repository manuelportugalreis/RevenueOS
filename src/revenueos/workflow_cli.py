"""Trusted local synthetic operator commands; no delivery connector or live planner."""

import argparse
import json
import sys
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from revenueos.approvals import (
    assign_reviewer,
    decide_action,
    inspect_action,
    prepare_action,
    rehearse_action,
    revise_action,
)
from revenueos.audit import read_audit
from revenueos.db import get_engine
from revenueos.knowledge import Principal
from revenueos.workflows import run_workflow, tool_schemas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("schemas")
    for name in (
        "run",
        "prepare",
        "inspect",
        "review",
        "rehearse",
        "revise",
        "assign-reviewer",
        "audit",
    ):
        command = sub.add_parser(name)
        command.add_argument("--organization", type=UUID, required=True)
        command.add_argument("--actor", type=UUID, required=True)
        if name == "run":
            command.add_argument("--dataset", type=UUID, required=True)
            command.add_argument("--lead", type=UUID, required=True)
            command.add_argument("--query", required=True)
        elif name == "prepare":
            command.add_argument("--workflow", type=UUID, required=True)
            command.add_argument("--recipient", required=True)
        elif name == "assign-reviewer":
            command.add_argument("--reviewer", type=UUID, required=True)
        elif name != "audit":
            command.add_argument("--action", type=UUID, required=True)
        if name in ("review", "rehearse"):
            command.add_argument("--hash", required=True)
        if name in ("review", "revise"):
            command.add_argument("--version", type=int, required=True)
        if name == "review":
            command.add_argument("--decision", choices=("approve", "reject"), required=True)
        if name == "revise":
            command.add_argument(
                "--closing",
                choices=("Would a short discussion be useful?", "What would you like to clarify?"),
                required=True,
            )
    args = parser.parse_args()
    if args.command == "schemas":
        print(json.dumps(tool_schemas(), indent=2))
        return
    engine = get_engine()
    principal = Principal(organization_id=args.organization, actor_id=args.actor)
    try:
        if args.command == "run":
            result = run_workflow(engine, principal, args.dataset, args.lead, args.query)
        elif args.command == "prepare":
            result = prepare_action(engine, principal, args.workflow, args.recipient)
        elif args.command == "inspect":
            result = inspect_action(engine, principal, args.action)
        elif args.command == "review":
            result = decide_action(
                engine, principal, args.action, args.version, args.hash, args.decision
            )
        elif args.command == "rehearse":
            result = rehearse_action(engine, principal, args.action, args.hash)
        elif args.command == "revise":
            result = revise_action(engine, principal, args.action, args.version, args.closing)
        elif args.command == "assign-reviewer":
            with engine.begin() as connection:
                assign_reviewer(connection, principal, args.reviewer)
            result = {"reviewer_id": str(args.reviewer), "assigned": True}
        else:
            with engine.connect() as connection:
                result = read_audit(connection, principal)
        print(json.dumps(result, default=str, indent=2))
    except (PermissionError, ValueError, SQLAlchemyError):
        print(
            "Workflow or review denied; inspect the scoped audit for recorded denials.",
            file=sys.stderr,
        )
        raise SystemExit(2) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
