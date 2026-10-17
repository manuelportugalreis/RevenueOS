import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import Engine

from revenueos.comparison import (
    ARMS,
    business_scenario,
    classify,
    execute,
    paired_interval,
    summarize,
)


def test_failure_is_not_successful_abstention() -> None:
    case = {"expect_abstention": True, "relevant_slugs": []}
    failed = classify(case, "failed", None, {})
    assert failed["technical_failure"] and not failed["fixture_success"]
    assert not failed["abstained"]
    assert classify(case, "abstained", {"rationale_claims": [], "draft": None}, {})[
        "fixture_success"
    ]


def test_grounding_and_relevance_are_different() -> None:
    case = {"expect_abstention": False, "relevant_slugs": ["right"]}
    output = {
        "rationale_claims": [{"text": "Exact text", "quote": "Exact text", "evidence_id": "doc:1"}]
    }
    result = classify(case, "review_pending", output, {"doc:1": ("wrong", "Exact text")})
    assert result["grounded_completion"] and not result["fixture_success"]
    assert result["inappropriate_completion"]
    assert not classify(case, "review_pending", output, {})["grounded_completion"]


def rows() -> list[dict]:
    return [
        {
            "case_id": str(i),
            "family": str(i // 2),
            "phase": "measured",
            "repetition": 0,
            "arm": arm,
            "fixture_success": bool(j),
            "expect_abstention": False,
            "state": "review_pending",
            "false_abstention": False,
            "abstained": False,
            "relevant_completion": bool(j),
            "inappropriate_completion": not bool(j),
            "completed": True,
            "grounded_completion": True,
            "technical_failure": False,
            "elapsed_ms": 1.0,
            "provider_attempts": 0,
        }
        for i in range(4)
        for j, arm in enumerate(ARMS)
    ]


def test_paired_cluster_bootstrap_and_repetitions() -> None:
    original = rows()
    result = paired_interval(original)
    assert result["point"] == 1 and result["interval"] == [1, 1] and result["families"] == 2
    assert result == paired_interval(original)
    repeated = original + [{**row, "repetition": 1} for row in original]
    report = summarize(repeated)
    assert report[ARMS[0]]["unique_tasks"] == 4 and report[ARMS[0]]["attempts"] == 8
    assert report["paired_fixture_success_difference"] == result
    with pytest.raises(ValueError):
        paired_interval(original[:-1])


@pytest.mark.parametrize("assisted", [3.0, 5.0, 7.0])
def test_scenario_never_claims_observed_roi(assisted: float) -> None:
    result = business_scenario(
        {
            "monthly_leads": 1000,
            "baseline_minutes": 5,
            "assisted_minutes_including_review": assisted,
            "loaded_hourly_usd": 60,
            "monthly_operating_usd": 100,
            "monthly_amortized_setup_usd": 300,
        }
    )
    assert result["evidence_class"] == "simulation_not_observed"
    assert result["measured_roi"] is None and result["realized_cash_savings_usd"] is None
    assert result["net_potential_capacity_value_usd"] == (5 - assisted) * 1000 - 400
    if assisted >= 5:
        assert result["capacity_break_even_leads"] is None


def test_incomplete_scenario_rejected() -> None:
    with pytest.raises(ValueError):
        business_scenario({"monthly_leads": 1})


@pytest.mark.integration
def test_small_comparison_reconciles_and_preserves_output(
    engine: Engine, intelligence: tuple, tmp_path: Path
) -> None:
    dataset, actor = intelligence
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    source = Path("data/intelligence")
    data = json.loads((source / "cases.json").read_text())
    data["cases"] = [
        data["cases"][0],
        next(c for c in data["cases"] if c["category"] == "injection"),
    ]
    (fixture / "cases.json").write_text(json.dumps(data))
    (fixture / "corpus.json").write_bytes((source / "corpus.json").read_bytes())
    (fixture / "SHA256SUMS").write_text(
        "\n".join(
            hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.name
            for p in fixture.glob("*.json")
        )
    )
    destination = tmp_path / "comparison"
    result = execute(engine, actor.organization_id, dataset, fixture, destination, repetitions=1)
    raw = [
        json.loads(line)
        for line in (destination / "RevenueOS-Comparison-Attempts.jsonl").read_text().splitlines()
    ]
    assert result["raw_attempts"] == len(raw) == 8
    assert result["warmup_attempts"] == result["measured_attempts"] == 4
    assert result["costs"]["provider_attempts"] == 0
    assert result["actual_pilot"]["status"] == "not_run"
    assert result["real_retrospective"]["status"] == "not_available"
    assert (
        result["raw_sha256"]
        == hashlib.sha256(
            (destination / "RevenueOS-Comparison-Attempts.jsonl").read_bytes()
        ).hexdigest()
    )
    with pytest.raises(ValueError, match="fresh_output"):
        execute(engine, actor.organization_id, dataset, fixture, destination)
