"""Trusted synthetic operator commands; no remote services or automatic messaging."""

import argparse
import json
from pathlib import Path
from typing import Any

from revenueos.db import actor_context, get_engine, tenant_context
from revenueos.knowledge import Principal
from revenueos.rehearsal import Task, analyze
from revenueos.reliability import reconcile_interrupted
from revenueos.security import install_runtime_role, runtime_posture


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("provision-runtime")
    sub.add_parser("runtime-check")
    recovery = sub.add_parser("reconcile")
    recovery.add_argument("--organization", required=True)
    recovery.add_argument("--actor", required=True)
    recovery.add_argument("--age-minutes", type=int, default=15)
    rehearse = sub.add_parser("rehearse-pilot")
    rehearse.add_argument("--input", type=Path, required=True)
    rehearse.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, Any]
    if args.command == "rehearse-pilot":
        data = json.loads(args.input.read_text())
        result = {
            name: analyze([Task.model_validate(row) for row in rows])
            for name, rows in data["scenarios"].items()
        }
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("Exported scripted fictional rehearsal; no pilot was conducted.")
        return
    engine = get_engine()
    try:
        if args.command == "provision-runtime":
            with engine.begin() as connection:
                install_runtime_role(connection)
            result = {
                "capability_role": "revenueos_runtime",
                "login_provisioning": "operator_required",
            }
        elif args.command == "runtime-check":
            with engine.connect() as connection:
                result = runtime_posture(connection)
        else:
            principal = Principal(organization_id=args.organization, actor_id=args.actor)
            tenant_context.set(principal.organization_id)
            actor_context.set(principal.actor_id)
            result = reconcile_interrupted(engine, principal, args.age_minutes)
        print(json.dumps(result, default=str, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
