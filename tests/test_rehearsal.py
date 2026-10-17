import pytest
from pydantic import ValidationError

from revenueos.rehearsal import Task, analyze


def sample(arm: str, prep: int | None = 100, **changes: object) -> Task:
    return Task.model_validate(
        {
            "evidence_class": "synthetic_scripted",
            "pair_id": "fictional-1",
            "arm": arm,
            "prep_seconds": prep,
            "review_seconds": 50,
            "rework_seconds": 30,
            "queue_seconds": 20,
            "completed": True,
            "acceptable": True,
            "missing_reason": None,
            **changes,
        }
    )


def test_review_and_rework_are_included() -> None:
    result = analyze([sample("baseline"), sample("assisted", 50, rework_seconds=130)])
    assert result["assumed_time_reduction"] == -0.25
    assert result["scenario_decision"] == "time_target_failed"
    assert result["realized_roi"] is None and result["real_participants"] == 0


def test_missing_timing_is_not_zero_or_success() -> None:
    result = analyze(
        [sample("baseline"), sample("assisted", None, missing_reason="instrumentation_missing")]
    )
    assert result["assumed_time_reduction"] is None
    assert result["scenario_decision"] == "inconclusive_missingness"


def test_skipped_work_cannot_win_time_target() -> None:
    result = analyze(
        [
            sample("baseline"),
            sample(
                "assisted",
                0,
                review_seconds=0,
                rework_seconds=0,
                queue_seconds=0,
                completed=False,
                acceptable=False,
                no_activity_attested=True,
            ),
        ]
    )
    assert result["scenario_decision"] == "guardrail_failed"


def test_assignment_and_evidence_integrity() -> None:
    with pytest.raises(ValueError):
        analyze([sample("baseline")])
    with pytest.raises(ValueError):
        analyze([sample("baseline"), sample("baseline"), sample("assisted")])
    with pytest.raises(ValidationError):
        sample("assisted", None)
    with pytest.raises(ValidationError):
        sample("assisted", evidence_class="actual_client")
