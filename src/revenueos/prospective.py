"""Prospective authored diagnostics; offline means template-only, never simulated LLM quality."""

import argparse
import csv
import hashlib
import json
import os
import random
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import Engine, text

from revenueos.comparison import classify, summarize
from revenueos.db import get_engine
from revenueos.evaluation import READER, STEWARD
from revenueos.free_provider import MODEL, FreeGemini
from revenueos.knowledge import Principal
from revenueos.recommendations import (
    INSTRUCTIONS,
    PROMPT_VERSION,
    PriceCard,
    configure_budget,
    provider_schema,
    recommend,
)

FIXED_AT = datetime(2026, 10, 16, 12, tzinfo=UTC)


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(
    engine: Engine,
    organization: UUID,
    dataset: UUID,
    output: Path,
    *,
    live: bool = False,
    cases_path: Path = Path("data/prospective/cases.json"),
) -> dict[str, Any]:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    provider = FreeGemini.from_environment(len(cases)) if live else None
    if provider and (not provider.api_key or not provider.free_tier_confirmed):
        raise ValueError("configure_GEMINI_API_KEY_and_confirm_project_has_no_billing")
    if not 1 <= len(cases) <= 48 or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("invalid_case_set")
    principal = Principal(organization_id=organization, actor_id=READER)
    with engine.connect() as connection:
        lead = connection.scalar(
            text("""SELECT id FROM leads WHERE organization_id=:org
            AND dataset_id=:dataset AND external_id='L1'"""),
            {"org": organization, "dataset": dataset},
        )
        if lead is None:
            raise ValueError("synthetic_L1_fixture_required")
        evidence = {
            f"doc:{r.id}": (r.slug, r.text)
            for r in connection.execute(
                text("""SELECT c.id,d.slug,c.text FROM document_chunks c
                JOIN document_versions v ON v.id=c.document_version_id
                JOIN documents d ON d.id=v.document_id WHERE d.organization_id=:org"""),
                {"org": organization},
            )
        }
    output.mkdir(parents=True, exist_ok=False)
    if provider:
        with engine.begin() as connection:
            configure_budget(
                connection,
                Principal(organization_id=organization, actor_id=STEWARD),
                FIXED_AT.strftime("%Y-%m"),
                Decimal(0),
            )
    price = PriceCard(
        model=MODEL,
        version="google-free-tier-2026-10-17-user-no-billing-attestation",
        input_per_million_usd=Decimal(0),
        output_per_million_usd=Decimal(0),
    )
    arms = ("focused_template", "gemini_free") if live else ("focused_template",)
    rows = []
    raw = output / "attempts.jsonl"
    for case in cases:
        # Seeded order counterbalances software timing; only one repetition, no latency SLO.
        order = list(arms)
        random.Random(case["id"]).shuffle(order)
        for arm in order:
            active = provider if arm == "gemini_free" else None
            if active and not active.halt_reason:
                time.sleep(max(0, active.last_call + active.interval_seconds - time.monotonic()))
            started = time.monotonic()
            result = (
                recommend(
                    engine,
                    principal,
                    dataset,
                    lead,
                    case["query"],
                    now=FIXED_AT,
                    provider=active,
                    price=price if active else None,
                    max_attempts=1,
                )
                if not (active and active.halt_reason)
                else {
                    "run_id": None,
                    "state": "failed",
                    "failure_code": "skipped_after_provider_failure",
                    "recommendation": None,
                    "attempts": [],
                }
            )
            row = {
                "phase": "measured",
                "repetition": 0,
                "arm": arm,
                "case_id": case["id"],
                "family": case["family"],
                "expect_abstention": case["expect_abstention"],
                "query": case["query"],
                "elapsed_ms": (time.monotonic() - started) * 1000,
                "state": result["state"],
                "failure_code": result["failure_code"],
                "output": result["recommendation"],
                "run_id": result["run_id"],
                "attempts": result["attempts"],
                "provider_attempts": len(result["attempts"]),
                **classify(case, result["state"], result["recommendation"], evidence),
            }
            rows.append(row)
            with raw.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(row, default=str) + "\n")
    source_paths = [*Path("src/revenueos").glob("*.py"), cases_path]
    report = {
        "protocol": "prospective_authored_extractiveness_v1",
        "recorded_at": datetime.now(UTC).isoformat(),
        "evidence_at": FIXED_AT.isoformat(),
        "live_model_status": "executed" if live else "not_run_missing_free_credentials",
        "live_transport_calls": provider.calls if provider else 0,
        "provider_halt_reason": provider.halt_reason if provider else None,
        "model": MODEL if live else None,
        "prompt_version": PROMPT_VERSION,
        "prompt_schema_sha256": hashlib.sha256(
            (INSTRUCTIONS + json.dumps(provider_schema(), sort_keys=True)).encode()
        ).hexdigest(),
        "hashes": {p.as_posix(): fingerprint(p) for p in source_paths},
        "corpus_sha256": fingerprint(Path("data/intelligence/corpus.json")),
        "raw_sha256": fingerprint(raw),
        "summary": summarize(rows, arms),
        "model_incremental_value": None if not live else "see_paired_fixture_diagnostic",
        "actual_invoice_usd": None,
        "account_billing_verified_by_api": False,
        "free_tier_attested_by_operator": bool(live),
        "independent_human_review": "not_conducted_blank_packet_only",
        "realized_roi": None,
        "limitations": [
            "New project-authored cases; no independent labels or hidden predictive holdout.",
            "Same restrictive extractive schema, not a free-writing model comparison.",
            "Upstream policy abstentions may bypass the provider; inspect actual call count.",
            "One repetition; descriptive family bootstrap, not population inference.",
            "No human preparation/review/rework observations or client company.",
            "Free tier availability is account-dependent; no paid fallback or endpoint override.",
        ],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    shuffled = list(rows)
    random.Random(20261017).shuffle(shuffled)
    with (
        (output / "independent-review-blank.csv").open("w", newline="", encoding="utf-8") as f,
        (output / "coordinator-key.csv").open("w", newline="", encoding="utf-8") as k,
    ):
        writer, key = csv.writer(f), csv.writer(k)
        writer.writerow(
            [
                "review_id",
                "query",
                "output",
                "relevance_0_2",
                "grounding_0_2",
                "review_seconds",
                "edit_seconds",
                "reviewer_id",
                "notes",
            ]
        )
        key.writerow(["review_id", "case_id", "arm"])
        for i, row in enumerate(shuffled):
            writer.writerow([i, row["query"], json.dumps(row["output"]), "", "", "", "", "", ""])
            key.writerow([i, row["case_id"], row["arm"]])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organization", type=UUID, required=True)
    parser.add_argument("--dataset", type=UUID, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live-free", action="store_true")
    parser.add_argument(
        "--env-file", type=Path, help="Optional ignored file; only Gemini settings read"
    )
    args = parser.parse_args()
    if args.env_file:
        for line in args.env_file.read_text(encoding="utf-8-sig").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() in ("GEMINI_API_KEY", "REVENUEOS_FREE_TIER_CONFIRMED"):
                os.environ.setdefault(name.strip(), value.strip().strip("\"'"))
    engine = get_engine()
    try:
        report = execute(engine, args.organization, args.dataset, args.output, live=args.live_free)
        print(json.dumps({k: report[k] for k in ("live_model_status", "live_transport_calls")}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
