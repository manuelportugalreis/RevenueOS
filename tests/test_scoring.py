from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text

from revenueos.ingestion import commit_bundle, preview_bundle
from revenueos.scoring import RulesConfig, predictive_readiness, rank_leads, score_context
from revenueos.synthetic import SYNTHETIC_ORG


def context() -> dict:
    now = datetime(2026, 10, 1, tzinfo=UTC)
    return {
        "id": uuid4(),
        "dataset_id": uuid4(),
        "observed_at": now,
        "created_at": now - timedelta(days=40),
        "source": "demo_request",
        "status": "new",
        "deleted_at": None,
        "do_not_contact": False,
        "currently_suppressed": False,
        "employee_band": "11-50",
        "lawful_use_status": "approved",
        "interactions": [
            {
                "id": uuid4(),
                "actor_type": "human",
                "direction": "inbound",
                "occurred_at": now - timedelta(days=2),
            }
        ],
    }


def test_hand_computed_explanation_without_invented_features() -> None:
    result = score_context(context())
    assert result["points"] == 65
    assert result["components"] == {
        "explicit_demo_request": 30,
        "recent_human_inbound_7d": 20,
        "target_company_size": 15,
        "declared_use_case_match": 0,
        "unanswered_over_24h": 0,
        "inactive_over_30d": 0,
    }
    assert "contact_coverage_unattested_time_penalties_disabled" in result["warnings"]


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("source", "test", "test_or_internal"),
        ("status", "disqualified", "disqualified"),
        ("do_not_contact", True, "do_not_contact"),
        ("currently_suppressed", True, "current_suppression_tombstone"),
        ("deleted_at", datetime(2026, 9, 1, tzinfo=UTC), "deleted"),
    ],
)
def test_excluded_leads_get_zero_points(field: str, value: object, reason: str) -> None:
    result = score_context({**context(), field: value})
    assert not result["eligible"] and result["points"] == 0
    assert reason in result["exclusions"]


def test_attested_coverage_enables_overdue_and_inactivity_rules() -> None:
    row = {**context(), "source": "website", "employee_band": None, "interactions": []}
    config = RulesConfig(
        contact_coverage_start=row["created_at"], coverage_attestation="fixture-v1"
    )
    result = score_context(row, config)
    assert result["components"]["unanswered_over_24h"] == 10
    assert result["components"]["inactive_over_30d"] == -15
    assert result["points"] == 0  # Clamp the negative sum, not an implied negative probability.


@pytest.mark.parametrize("age,expected", [(7, 20), (7.0001, 0)])
def test_recent_inbound_boundary(age: float, expected: int) -> None:
    row = context()
    row["interactions"][0]["occurred_at"] = row["observed_at"] - timedelta(days=age)
    assert score_context(row)["components"]["recent_human_inbound_7d"] == expected


def test_automated_activity_cannot_count_as_human_engagement() -> None:
    row = context()
    row["interactions"][0]["actor_type"] = "automation"
    assert score_context(row)["points"] == 45


@pytest.mark.parametrize("days,expected", [(30, 0), (30.0001, -15)])
def test_inactivity_boundary_requires_complete_coverage(days: float, expected: int) -> None:
    row = context()
    row["created_at"] = row["observed_at"] - timedelta(days=days)
    row["interactions"] = []
    config = RulesConfig(contact_coverage_start=row["created_at"], coverage_attestation="fixture")
    assert score_context(row, config)["components"]["inactive_over_30d"] == expected


@pytest.mark.parametrize("hours,expected", [(24, 0), (24.0001, 10)])
def test_overdue_boundary_requires_complete_coverage(hours: float, expected: int) -> None:
    row = context()
    row["created_at"] = row["observed_at"] - timedelta(hours=hours)
    row["interactions"] = []
    config = RulesConfig(contact_coverage_start=row["created_at"], coverage_attestation="fixture")
    assert score_context(row, config)["components"]["unanswered_over_24h"] == expected


def test_as_of_cannot_reconstruct_earlier_or_future_features() -> None:
    row = context()
    for instant in (row["observed_at"] - timedelta(days=1), row["observed_at"] + timedelta(days=1)):
        with pytest.raises(ValueError, match="exact_snapshot"):
            score_context(row, as_of=instant)


@pytest.mark.integration
def test_snapshot_queue_baselines_and_readiness(engine: Engine, bundle: Path) -> None:
    with engine.connect() as connection:
        preview = preview_bundle(bundle, connection)
    dataset = commit_bundle(bundle, engine, preview.preview_hash).dataset_id
    with engine.begin() as connection:
        ranked = rank_leads(connection, SYNTHETIC_ORG, dataset, persist=True)
        again = rank_leads(connection, SYNTHETIC_ORG, dataset)
        readiness = predictive_readiness(connection, SYNTHETIC_ORG, dataset)
        assert connection.scalar(text("SELECT count(*) FROM score_runs")) == 8
    assert ranked == again
    assert len(ranked["queues"]["rules"]) == 5
    assert set(ranked["queues"]["fifo"]) == set(ranked["queues"]["rules"])
    assert set(ranked["queues"]["newest_first"]) == set(ranked["queues"]["rules"])
    assert not readiness["model_training_allowed"]
    assert readiness["predictive_accuracy"] is None
    assert "synthetic_labels_are_not_business_outcomes" in readiness["reasons"]
    with engine.connect() as connection, pytest.raises(ValueError):
        rank_leads(connection, uuid4(), UUID(str(dataset)))
