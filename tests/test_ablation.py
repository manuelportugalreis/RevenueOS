from pathlib import Path

from revenueos.comparison import ABLATION_ARMS, ARMS, summarize


def test_strong_ablation_reports_direct_vs_bounded_without_relabeling() -> None:
    rows = []
    for arm in ABLATION_ARMS:
        for index in range(4):
            rows.append(
                {
                    "arm": arm,
                    "phase": "measured",
                    "repetition": 0,
                    "case_id": str(index),
                    "family": str(index // 2),
                    "expect_abstention": False,
                    "state": "review_pending",
                    "fixture_success": arm != ARMS[0],
                    "false_abstention": False,
                    "abstained": False,
                    "relevant_completion": True,
                    "inappropriate_completion": False,
                    "completed": True,
                    "grounded_completion": True,
                    "technical_failure": False,
                    "elapsed_ms": 10.0,
                    "provider_attempts": 0,
                }
            )
    result = summarize(rows, ABLATION_ARMS)
    pair = result["paired_differences"]["focused_bounded_template_minus_focused_direct_template"]
    assert pair["point"] == 0 and pair["interval"] == [0, 0]
    assert set(ABLATION_ARMS).issubset(result)


def test_serving_selector_never_reads_case_labels() -> None:
    source = Path("src/revenueos/evidence.py").read_text()
    assert "cases.json" not in source and "relevant_slugs" not in source
    assert "data/intelligence" not in source
