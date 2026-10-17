import csv
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine

from revenueos.evaluation import STEWARD, scripted_valid
from revenueos.knowledge import Principal
from revenueos.prospective import execute
from revenueos.providers import ScriptedProvider
from revenueos.recommendations import PriceCard, configure_budget, recommend


def test_new_queries_and_frozen_policy_have_honest_provenance() -> None:
    new = json.loads(Path("data/prospective/cases.json").read_text())["cases"]
    old = json.loads(Path("data/intelligence/cases.json").read_text())["cases"]
    assert len(new) == 24 and not {c["query"] for c in new} & {c["query"] for c in old}
    freeze = json.loads(Path("data/prospective/policy-freeze.json").read_text())
    assert freeze["annotation_source"] == "project_authored_not_independent"
    for name, expected in freeze["policy_sha256"].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected


def test_published_model_summary_matches_recorded_attempts() -> None:
    root = Path("outputs/prospective/free-gemini-run-2")
    report = json.loads((root / "report.json").read_text())
    raw = root / "attempts.jsonl"
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == report["raw_sha256"]
    published = json.loads(Path("data/dashboard/prospective-evaluation.json").read_text())
    assert (
        published["source_sha256"]
        == hashlib.sha256((root / "report.json").read_bytes()).hexdigest()
    )
    rows = [json.loads(line) for line in raw.read_text().splitlines()]
    for arm, field in (
        ("focused_template", "template_successes"),
        ("gemini_free", "model_successes"),
    ):
        assert published[field] == sum(r["fixture_success"] for r in rows if r["arm"] == arm)
    assert published["transport_calls"] == report["live_transport_calls"]
    assert published["actual_invoice_usd"] is None and published["provisional_labels"]


def test_live_preflight_cannot_touch_database_without_free_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("REVENUEOS_FREE_TIER_CONFIRMED", raising=False)
    engine = MagicMock()
    with pytest.raises(ValueError, match="no_billing"):
        execute(engine, MagicMock(), MagicMock(), tmp_path / "never-created", live=True)
    engine.connect.assert_not_called()
    assert not (tmp_path / "never-created").exists()


@pytest.mark.integration
def test_offline_report_never_invents_model_comparison(
    engine: Engine,
    intelligence: tuple,
    tmp_path: Path,
) -> None:
    dataset, principal = intelligence
    out = tmp_path / "offline"
    result = execute(engine, principal.organization_id, dataset, out)
    assert result["model_incremental_value"] is None and result["live_transport_calls"] == 0
    assert result["model"] is None and result["actual_invoice_usd"] is None
    assert result["summary"]["focused_template"]["unique_tasks"] == 24
    assert "paired_fixture_success_difference" not in result["summary"]
    with (out / "independent-review-blank.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 24 and all(not r["relevance_0_2"] for r in rows)


@pytest.mark.integration
def test_actual_query_reaches_provider_under_same_validator(
    engine: Engine, intelligence: tuple
) -> None:
    from datetime import UTC, datetime
    from decimal import Decimal

    from sqlalchemy import text

    dataset, principal = intelligence
    seen = []

    def script(payload: dict, attempt: int):
        seen.append(json.loads(payload["input"])["query"])
        return scripted_valid(payload, attempt)

    with engine.begin() as c:
        configure_budget(
            c,
            Principal(organization_id=principal.organization_id, actor_id=STEWARD),
            "2026-10",
            Decimal(1),
        )
        lead = c.scalar(text("SELECT id FROM leads WHERE external_id='L1'"))
    provider = ScriptedProvider(script)
    result = recommend(
        engine,
        principal,
        dataset,
        lead,
        "configuration checklist",
        provider=provider,
        price=PriceCard(
            version="fixture",
            model=provider.model,
            input_per_million_usd=Decimal(0),
            output_per_million_usd=Decimal(0),
        ),
        now=datetime(2026, 10, 16, 12, tzinfo=UTC),
        max_attempts=1,
    )
    assert seen == ["configuration checklist"] and result["state"] == "review_pending"
