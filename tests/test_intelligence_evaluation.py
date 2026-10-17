import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import Engine

from revenueos.evaluation import evaluate, queue_diagnostics
from revenueos.synthetic import SYNTHETIC_ORG

ROOT = Path(__file__).resolve().parents[1]


def test_fixed_case_split_and_provenance() -> None:
    data = json.loads((ROOT / "data/intelligence/cases.json").read_text(encoding="utf-8"))
    assert len(data["cases"]) == 100
    assert len({case["id"] for case in data["cases"]}) == 100
    dev = {case["family"] for case in data["cases"] if case["split"] == "dev"}
    test = {case["family"] for case in data["cases"] if case["split"] == "test"}
    assert len(dev) == 12 and len(test) == 8 and dev.isdisjoint(test)
    assert "not_independently_human_reviewed" in data["annotation_source"]
    for line in (ROOT / "data/intelligence/SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert (
            hashlib.sha256((ROOT / "data/intelligence" / name).read_bytes()).hexdigest() == expected
        )


def test_fixture_builder_is_byte_reproducible(tmp_path: Path) -> None:
    directory = ROOT / "data/intelligence"
    before = {path.name: path.read_bytes() for path in directory.glob("*.json")}
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_intelligence_fixtures.py"),
            "--output",
            str(tmp_path),
        ],
        check=True,
    )
    assert before == {path.name: path.read_bytes() for path in tmp_path.glob("*.json")}
    assert (directory / "SHA256SUMS").read_bytes() == (tmp_path / "SHA256SUMS").read_bytes()


@pytest.mark.integration
def test_development_harness_reports_limits_and_baselines(
    engine: Engine, intelligence: tuple
) -> None:
    dataset, _ = intelligence
    report = evaluate(engine, SYNTHETIC_ORG, dataset, ROOT / "data/intelligence", split="dev")
    assert report["cases"] == 60 and report["independent_families"] == 12
    assert report["readiness"]["predictive_accuracy"] is None
    assert report["live_model_evaluation"] == "not_run_offline_by_owner_instruction"
    assert set(report["retrieval_comparison"]) == {"lexical", "title_keyword"}
    assert set(report["recommendation_comparison"]) == {"template", "scripted_fixture"}
    assert report["recommendation_comparison"]["template"]["simulated_cost_usd"] == 0
    assert len(report["cases_detail"]) == 60
    with engine.connect() as connection:
        queues = queue_diagnostics(connection, SYNTHETIC_ORG, dataset, k=2)
    assert queues["predictive_accuracy"] is None
    assert all(queue["selected"] == 2 for queue in queues["queues"].values())
