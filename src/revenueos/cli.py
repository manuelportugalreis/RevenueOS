"""Local operator CLI. Authentication/API/UI are deferred; synthetic data only."""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from revenueos.analytics import metrics
from revenueos.contracts import Manifest
from revenueos.db import get_engine
from revenueos.evaluation import evaluate, scripted_valid, seed_knowledge
from revenueos.ingestion import BundleError, commit_bundle, preview_bundle
from revenueos.knowledge import Principal, resolve_citation, search
from revenueos.providers import ScriptedProvider
from revenueos.recommendations import PriceCard, recommend
from revenueos.scoring import RulesConfig, predictive_readiness, rank_leads
from revenueos.synthetic import generate


def _run() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    synth = sub.add_parser("synthetic")
    synth.add_argument("path", type=Path)
    synth.add_argument("--seed", type=int, default=42)
    synth.add_argument("--leads", type=int, default=1000)
    synth.add_argument("--golden", action="store_true")
    for action in ("init-org", "preview", "commit"):
        command = sub.add_parser(action)
        command.add_argument("path", type=Path)
        if action == "commit":
            command.add_argument("--confirm", required=True, help="Exact preview_hash from preview")
    report = sub.add_parser("analytics")
    report.add_argument("--organization", required=True, type=UUID)
    report.add_argument("--dataset", required=True, type=UUID)
    report.add_argument("--start", required=True, type=datetime.fromisoformat)
    report.add_argument("--end", required=True, type=datetime.fromisoformat)
    for name in (
        "score",
        "readiness",
        "seed-knowledge",
        "search",
        "citation",
        "recommend",
        "intelligence-eval",
    ):
        command = sub.add_parser(name)
        command.add_argument("--organization", required=True, type=UUID)
        if name in ("score", "readiness", "recommend", "intelligence-eval"):
            command.add_argument("--dataset", required=True, type=UUID)
        if name in ("search", "citation", "recommend"):
            command.add_argument("--actor", required=True, type=UUID)
        if name in ("search", "recommend"):
            command.add_argument("--query", required=True)
        if name == "score":
            command.add_argument("--persist", action="store_true")
            command.add_argument("--rules-config", type=Path)
        elif name == "search":
            command.add_argument(
                "--method", choices=("lexical", "title_keyword"), default="lexical"
            )
        elif name == "citation":
            command.add_argument("--chunk", required=True, type=UUID)
        elif name == "recommend":
            command.add_argument("--lead", required=True, type=UUID)
            command.add_argument(
                "--provider", choices=("template", "scripted-fixture"), default="template"
            )
        elif name == "seed-knowledge":
            command.add_argument(
                "--corpus", type=Path, default=Path("data/intelligence/corpus.json")
            )
        elif name == "intelligence-eval":
            command.add_argument("--fixtures", type=Path, default=Path("data/intelligence"))
            command.add_argument("--split", choices=("dev", "test"), default="test")
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "synthetic":
        generate(args.path, seed=args.seed, leads=args.leads, golden=args.golden)
        print("Generated SYNTHETIC CSV bundle")
        return
    engine = get_engine()
    try:
        if args.command in ("init-org", "preview", "commit"):
            metadata = Manifest.model_validate_json((args.path / "manifest.json").read_bytes())
            if metadata.data_mode != "synthetic":
                raise ValueError("CLI is synthetic-only pending real-data security readiness")
        if args.command == "init-org":
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO organizations"
                        "(id,name,data_mode,reporting_timezone,default_currency)"
                        " VALUES (:id,:name,:mode,:zone,:currency) ON CONFLICT (id) DO NOTHING"
                    ),
                    {
                        "id": metadata.organization_id,
                        "name": metadata.organization_name,
                        "mode": metadata.data_mode,
                        "zone": metadata.reporting_timezone,
                        "currency": metadata.default_currency,
                    },
                )
            print("Synthetic organization initialized (or already exists)")
        elif args.command == "preview":
            with engine.connect() as connection:
                print(json.dumps(preview_bundle(args.path, connection).summary(), indent=2))
        elif args.command == "commit":
            print(
                json.dumps(
                    asdict(commit_bundle(args.path, engine, args.confirm)), default=str, indent=2
                )
            )
        elif args.command == "analytics":
            with engine.connect() as connection:
                print(
                    json.dumps(
                        metrics(connection, args.organization, args.dataset, args.start, args.end),
                        default=str,
                        indent=2,
                    )
                )
        elif args.command == "score":
            config = (
                RulesConfig.model_validate_json(args.rules_config.read_bytes())
                if args.rules_config
                else RulesConfig()
            )
            with engine.begin() as connection:
                print(
                    json.dumps(
                        rank_leads(
                            connection,
                            args.organization,
                            args.dataset,
                            config,
                            persist=args.persist,
                        ),
                        default=str,
                        indent=2,
                    )
                )
        elif args.command == "readiness":
            with engine.connect() as connection:
                print(
                    json.dumps(
                        predictive_readiness(connection, args.organization, args.dataset),
                        default=str,
                        indent=2,
                    )
                )
        elif args.command == "seed-knowledge":
            with engine.begin() as connection:
                seed_knowledge(connection, args.organization, args.corpus)
            print("Seeded SYNTHETIC knowledge fixtures and local operator memberships")
        elif args.command == "search":
            with engine.connect() as connection:
                hits = search(
                    connection,
                    Principal(organization_id=args.organization, actor_id=args.actor),
                    args.query,
                    method=args.method,
                )
                print(json.dumps([hit.model_dump(mode="json") for hit in hits], indent=2))
        elif args.command == "citation":
            with engine.connect() as connection:
                citation = resolve_citation(
                    connection,
                    Principal(organization_id=args.organization, actor_id=args.actor),
                    args.chunk,
                )
                print(citation.model_dump_json(indent=2))
        elif args.command == "recommend":
            fixture = args.provider == "scripted-fixture"
            price = (
                PriceCard(
                    version="SIMULATED-not-provider-pricing-v1",
                    model="scripted-fixture-v1",
                    input_per_million_usd="0.5",
                    output_per_million_usd="2",
                )
                if fixture
                else None
            )
            print(
                json.dumps(
                    recommend(
                        engine,
                        Principal(organization_id=args.organization, actor_id=args.actor),
                        args.dataset,
                        args.lead,
                        args.query,
                        provider=ScriptedProvider(scripted_valid) if fixture else None,
                        price=price,
                    ),
                    default=str,
                    indent=2,
                )
            )
        elif args.command == "intelligence-eval":
            result = evaluate(
                engine, args.organization, args.dataset, args.fixtures, split=args.split
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(result, default=str, indent=2) + "\n", encoding="utf-8"
            )
            print(f"Offline {args.split} evaluation saved to {args.output}")
    finally:
        engine.dispose()


def main() -> None:
    try:
        _run()
    except BundleError as exc:
        # BundleError contains controlled codes only, never raw row/manifest values.
        print(f"Import rejected: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
    except (ValueError, OSError, KeyError, PermissionError):
        print("Invalid input/configuration; check paths, manifest, and interval.", file=sys.stderr)
        raise SystemExit(2) from None
    except SQLAlchemyError:
        print("Database operation failed; verify configuration and migrations.", file=sys.stderr)
        raise SystemExit(3) from None


if __name__ == "__main__":
    main()
