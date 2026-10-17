from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import Engine

from revenueos.analytics import metrics
from revenueos.ingestion import commit_bundle, preview_bundle
from revenueos.synthetic import SYNTHETIC_ORG

pytestmark = pytest.mark.integration


def report(engine: Engine, bundle: Path, start: datetime, end: datetime) -> dict:
    with engine.connect() as connection:
        preview = preview_bundle(bundle, connection)
    committed = commit_bundle(bundle, engine, preview.preview_hash)
    with engine.connect() as connection:
        return metrics(connection, SYNTHETIC_ORG, committed.dataset_id, start, end)


def test_hand_computed_metrics(engine: Engine, bundle: Path) -> None:
    result = report(
        engine, bundle, datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)
    )
    leads = result["leads"]
    assert leads["total_cohort"] == 8
    assert leads["excluded_test_internal"] == 1
    assert leads["excluded_deleted"] == 1
    assert leads["inbound_leads"] == 6
    assert leads["response_observed"] == 3
    assert leads["no_recorded_response"] == 3
    assert leads["response_median_hours"] == 2
    assert leads["response_p90_hours"] == pytest.approx(3.6)
    assert leads["qualification_denominator"] == 3
    assert leads["qualified_30d"] == 1
    assert leads["qualification_rate"] == pytest.approx(1 / 3)
    assert leads["immature_leads"] == 1
    assert leads["missing_or_incomplete_outcomes"] == 2
    assert result["opportunities"] == {
        "won": 1,
        "lost": 1,
        "closed_denominator": 2,
        "win_rate": 0.5,
    }
    assert result["open_pipeline_by_currency"] == [
        {"currency": "EUR", "amount": Decimal("4000.20"), "opportunity_count": 1},
        {"currency": "USD", "amount": Decimal("3000.10"), "opportunity_count": 1},
    ]
    assert result["data_mode"] == "synthetic"


def test_empty_cohort_is_not_zero_conversion(engine: Engine, bundle: Path) -> None:
    result = report(
        engine, bundle, datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)
    )
    assert result["leads"]["inbound_leads"] == 0
    assert result["leads"]["qualification_rate"] is None
    assert result["leads"]["response_median_hours"] is None
    assert result["opportunities"]["win_rate"] is None


def test_end_is_exclusive(engine: Engine, bundle: Path) -> None:
    result = report(
        engine, bundle, datetime(2026, 7, 1, tzinfo=UTC), datetime(2026, 8, 1, tzinfo=UTC)
    )
    assert result["leads"]["total_cohort"] == 0


def test_timezone_offset_preserves_same_cohort(engine: Engine, bundle: Path) -> None:
    result = report(
        engine,
        bundle,
        datetime.fromisoformat("2026-07-31T17:00:00-07:00"),
        datetime.fromisoformat("2026-09-30T17:00:00-07:00"),
    )
    assert result["leads"]["inbound_leads"] == 6


def test_scope_and_invalid_interval(engine: Engine, bundle: Path) -> None:
    with engine.connect() as connection:
        preview = preview_bundle(bundle, connection)
    committed = commit_bundle(bundle, engine, preview.preview_hash)
    with engine.connect() as connection:
        with pytest.raises(ValueError, match="dataset_not_found"):
            metrics(
                connection,
                uuid4(),
                committed.dataset_id,
                datetime(2026, 8, 1, tzinfo=UTC),
                datetime(2026, 10, 1, tzinfo=UTC),
            )
        with pytest.raises(ValueError, match="timezone-aware"):
            metrics(
                connection,
                SYNTHETIC_ORG,
                committed.dataset_id,
                datetime(2026, 8, 1),
                datetime(2026, 10, 1),
            )
