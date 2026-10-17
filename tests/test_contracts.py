from pathlib import Path

import pytest
from pydantic import ValidationError

from revenueos.contracts import Lead, Opportunity
from revenueos.db import get_engine
from revenueos.synthetic import generate, golden_rows


@pytest.mark.parametrize(
    "field,value",
    [
        ("created_at", "2026-08-01T00:00:00"),
        ("created_at", "bad-date"),
        ("do_not_contact", "yes"),
        ("email", "person@real-company.com"),
        ("email", "invalid-address"),
        ("source", "unknown-source"),
        ("deleted_at", "2026-01-01T00:00:00Z"),
        ("external_id", "unsafe/id"),
    ],
)
def test_lead_rejects_invalid_values(field: str, value: str) -> None:
    row = {**golden_rows()["leads"][0], field: value}
    with pytest.raises(ValidationError):
        Lead.model_validate(row)


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-1.00", "1.001", "1000000000000.00"])
def test_money_rejects_invalid_amounts(amount: str) -> None:
    with pytest.raises(ValidationError):
        Opportunity.model_validate({**golden_rows()["opportunities"][0], "amount": amount})


def test_timestamp_normalizes_offset() -> None:
    lead = Lead.model_validate(
        {**golden_rows()["leads"][0], "created_at": "2026-07-31T17:00:00-07:00"}
    )
    assert lead.created_at.isoformat() == "2026-08-01T00:00:00+00:00"


@pytest.mark.parametrize("golden", [True, False])
def test_generator_byte_reproducible(tmp_path: Path, golden: bool) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    generate(first, seed=73, leads=100, golden=golden)
    generate(second, seed=73, leads=100, golden=golden)
    assert {p.name: p.read_bytes() for p in first.iterdir()} == {
        p.name: p.read_bytes() for p in second.iterdir()
    }


def test_database_dialect_is_explicit() -> None:
    with pytest.raises(ValueError, match="requires PostgreSQL"):
        get_engine("sqlite:///:memory:")


def test_nul_is_quarantined_before_database_write() -> None:
    with pytest.raises(ValidationError):
        Lead.model_validate({**golden_rows()["leads"][0], "name": "Bad\x00Name"})


def test_invalid_timezone_is_a_validation_error() -> None:
    from revenueos.contracts import Manifest
    from revenueos.synthetic import manifest

    with pytest.raises(ValidationError):
        Manifest.model_validate({**manifest(), "reporting_timezone": "Not/A/Zone"})


def test_checked_in_fixtures_match_generator(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1] / "data" / "synthetic"
    for name, golden in (("golden", True), ("demo", False)):
        generated = tmp_path / name
        generate(generated, golden=golden)
        assert {p.name: p.read_bytes() for p in generated.iterdir()} == {
            p.name: p.read_bytes() for p in (root / name).iterdir()
        }
