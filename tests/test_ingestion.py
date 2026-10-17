import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Engine, text

from revenueos.ingestion import BundleError, commit_bundle, preview_bundle
from revenueos.synthetic import golden_rows, manifest, write_bundle

pytestmark = pytest.mark.integration


def preview(engine: Engine, bundle: Path) -> Any:
    with engine.connect() as connection:
        return preview_bundle(bundle, connection)


def next_bundle(bundle: Path, rows: dict[str, list[dict[str, Any]]]) -> None:
    metadata = manifest()
    metadata["observed_at"] = "2026-10-02T00:00:00Z"
    write_bundle(bundle, metadata, rows)


def test_preview_exact_reconciliation_and_no_writes(engine: Engine, bundle: Path) -> None:
    report = preview(engine, bundle)
    assert report.total_rows == 35
    assert report.accepted == 28
    assert report.quarantined == 6
    assert report.duplicates == 1
    assert report.summary()["accepted_by_entity"] == {
        "accounts": 2,
        "leads": 8,
        "opportunities": 4,
        "interactions": 6,
        "opportunity_leads": 2,
        "opportunity_stage_events": 1,
        "lead_outcomes": 5,
    }
    serialized = json.dumps(report.summary())
    assert "lead1@" not in serialized
    assert "not-a-date" not in serialized
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM datasets")) == 0
        assert connection.scalar(text("SELECT count(*) FROM import_batches")) == 0


def test_confirm_and_replay(engine: Engine, bundle: Path) -> None:
    report = preview(engine, bundle)
    with pytest.raises(BundleError, match="preview_changed"):
        commit_bundle(bundle, engine, "unconfirmed")
    first = commit_bundle(bundle, engine, report.preview_hash)
    replay = commit_bundle(bundle, engine, report.preview_hash)
    assert not first.replayed and replay.replayed
    assert first.dataset_id == replay.dataset_id
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM datasets")) == 1
        assert connection.scalar(text("SELECT count(*) FROM leads")) == 8
        assert (
            connection.scalar(text("SELECT count(DISTINCT (entity,row_number)) FROM import_errors"))
            == 6
        )


def test_concurrent_identical_commit_is_idempotent(engine: Engine, bundle: Path) -> None:
    report = preview(engine, bundle)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda _: commit_bundle(bundle, engine, report.preview_hash), range(2))
        )
    assert results[0].dataset_id == results[1].dataset_id
    assert sorted(result.replayed for result in results) == [False, True]


def test_changed_file_invalidates_preview(engine: Engine, bundle: Path) -> None:
    report = preview(engine, bundle)
    rows = golden_rows()
    rows["leads"][0]["name"] = "SYNTHETIC Changed"
    write_bundle(bundle, manifest(), rows)
    with pytest.raises(BundleError, match="preview_changed"):
        commit_bundle(bundle, engine, report.preview_hash)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM datasets")) == 0


def test_stale_and_conflicting_source_versions(engine: Engine, bundle: Path) -> None:
    report = preview(engine, bundle)
    commit_bundle(bundle, engine, report.preview_hash)
    rows = golden_rows()
    # Remove repeated L1 so the history check, rather than within-file duplicate policy, is tested.
    rows["leads"] = rows["leads"][:8]
    rows["leads"][0]["source_updated_at"] = "2026-09-29T00:00:00Z"
    rows["leads"][1]["name"] = "SYNTHETIC Conflicting version"
    next_bundle(bundle, rows)
    report = preview(engine, bundle)
    codes = {issue.code for issue in report.issues}
    assert "stale_source_version" in codes
    assert "source_version_conflict" in codes
    assert "missing_or_quarantined_parent" in codes


def test_suppression_survives_disappearance_and_reappearance(engine: Engine, bundle: Path) -> None:
    report = preview(engine, bundle)
    commit_bundle(bundle, engine, report.preview_hash)
    rows = golden_rows()
    rows["leads"] = [row for row in rows["leads"] if row["external_id"] not in ("L7", "L8")]
    next_bundle(bundle, rows)
    commit_bundle(bundle, engine, preview(engine, bundle).preview_hash)
    rows = golden_rows()
    for row in rows["leads"]:
        row["source_updated_at"] = "2026-10-02T00:00:00Z"
        row["do_not_contact"] = False
        row["deleted_at"] = ""
    metadata = manifest()
    metadata["observed_at"] = "2026-10-03T00:00:00Z"
    write_bundle(bundle, metadata, rows)
    report = preview(engine, bundle)
    indexed = {row["external_id"]: row for row in report.rows["leads"]}
    assert indexed["L7"]["do_not_contact"] is True
    assert indexed["L8"]["deleted_at"] is not None
    result = commit_bundle(bundle, engine, report.preview_hash)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT do_not_contact FROM leads WHERE external_id='L7' AND dataset_id=:id"),
                {"id": result.dataset_id},
            )
            is True
        )


@pytest.mark.parametrize(
    "kind",
    [
        "missing_file",
        "header",
        "invalid_utf8",
        "mode",
        "future",
        "mapping",
        "orphan",
        "incomplete_outcome",
        "before_creation",
    ],
)
def test_validation_edges(engine: Engine, bundle: Path, kind: str) -> None:
    rows = golden_rows()
    metadata = manifest()
    fatal = kind in ("missing_file", "header", "invalid_utf8", "mode", "mapping")
    if kind == "mode":
        rows["accounts"][0]["data_mode"] = "real"
    elif kind == "future":
        rows["accounts"][0]["source_updated_at"] = "2027-01-01T00:00:00Z"
    elif kind == "mapping":
        metadata["column_mapping"] = {"unknown_entity": {}}
    elif kind == "orphan":
        rows["leads"][0]["account_external_id"] = "NO_ACCOUNT"
    elif kind == "incomplete_outcome":
        rows["lead_outcomes"][0]["observed_through"] = "2026-08-15T00:00:00Z"
    elif kind == "before_creation":
        rows["interactions"][0]["occurred_at"] = "2026-01-01T00:00:00Z"
    write_bundle(bundle, metadata, rows)
    if kind == "missing_file":
        (bundle / "accounts.csv").unlink()
    elif kind == "header":
        (bundle / "accounts.csv").write_text("invalid,header\n", encoding="utf-8")
    elif kind == "invalid_utf8":
        (bundle / "accounts.csv").write_bytes(b"\xff\xfe")
    if fatal:
        with pytest.raises(BundleError):
            preview(engine, bundle)
    else:
        report = preview(engine, bundle)
        assert report.quarantined > 6
        assert report.total_rows == report.accepted + report.quarantined + report.duplicates


def test_custom_column_mapping(engine: Engine, bundle: Path) -> None:
    metadata = manifest()
    metadata["column_mapping"] = {"accounts": {"external_id": "CRM_ID"}}
    (bundle / "manifest.json").write_text(json.dumps(metadata), encoding="utf-8")
    content = (bundle / "accounts.csv").read_text(encoding="utf-8")
    (bundle / "accounts.csv").write_text(
        content.replace("external_id", "CRM_ID", 1), encoding="utf-8"
    )
    assert preview(engine, bundle).accepted == 28


def test_strict_bad_csv_column_count(engine: Engine, bundle: Path) -> None:
    with (bundle / "accounts.csv").open("a", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["too", "few"])
    report = preview(engine, bundle)
    assert any(issue.code == "column_count" for issue in report.issues)


def test_row_and_file_limits(engine: Engine, bundle: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("revenueos.ingestion.MAX_ROWS", 1)
    with pytest.raises(BundleError, match="too_many_rows"):
        preview(engine, bundle)
    from revenueos.ingestion import _read

    with pytest.raises(BundleError, match="file_too_large"):
        _read(bundle / "accounts.csv", limit=1)
