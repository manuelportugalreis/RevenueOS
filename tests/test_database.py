import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from revenueos.analytics import metrics
from revenueos.ingestion import commit_bundle, preview_bundle
from revenueos.synthetic import SYNTHETIC_ORG, generate, golden_rows, manifest, write_bundle

pytestmark = pytest.mark.integration


def commit(engine: Engine, bundle: Path) -> Any:
    with engine.connect() as connection:
        report = preview_bundle(bundle, connection)
    return commit_bundle(bundle, engine, report.preview_hash)


def test_all_migrations_roundtrip(engine: Engine) -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    command.upgrade(config, "head")
    assert len(set(inspect(engine).get_table_names()) - {"alembic_version"}) == 31
    assert set(inspect(engine).get_view_names()) == {"current_datasets", "lead_response_facts_v1"}


def test_database_scope_money_and_immutability(engine: Engine, bundle: Path) -> None:
    result = commit(engine, bundle)
    with engine.connect() as connection:
        lead = dict(connection.execute(text("SELECT * FROM leads LIMIT 1")).mappings().one())
        account = connection.scalar(text("SELECT id FROM accounts LIMIT 1"))
    # SQL constraints protect even direct database callers from a cross-organization reference.
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO leads(organization_id,dataset_id,id,external_id,source_updated_at,"
                "row_hash,account_id,source,status,created_at,do_not_contact) "
                "VALUES (:org,:dataset,:id,'CROSS',:updated,:hash,:account,"
                "'website','new',:created,false)"
            ),
            {
                "org": uuid4(),
                "dataset": result.dataset_id,
                "id": uuid4(),
                "updated": lead["source_updated_at"],
                "hash": "a" * 64,
                "account": account,
                "created": lead["created_at"],
            },
        )
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO opportunities "
                "(organization_id,dataset_id,id,external_id,source_updated_at,"
                "row_hash,account_id,stage,amount,currency,created_at) "
                "VALUES (:org,:dataset,:id,'NEGATIVE',:updated,:hash,:account,"
                "'demo',-1,'USD',:created)"
            ),
            {
                "org": SYNTHETIC_ORG,
                "dataset": result.dataset_id,
                "id": uuid4(),
                "updated": lead["source_updated_at"],
                "hash": "a" * 64,
                "account": account,
                "created": lead["created_at"],
            },
        )
    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(text("UPDATE leads SET status='qualified'"))
    with pytest.raises(DBAPIError, match="append-only"), engine.begin() as connection:
        connection.execute(text("DELETE FROM datasets"))


def test_commit_failure_rolls_back_all_tables(
    engine: Engine,
    bundle: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with engine.connect() as connection:
        report = preview_bundle(bundle, connection)
    from revenueos import ingestion

    insert = ingestion._insert_row
    calls = 0

    def fail_midway(*args: Any, **kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == 10:
            raise RuntimeError("injected write failure")
        insert(*args, **kwargs)

    monkeypatch.setattr(ingestion, "_insert_row", fail_midway)
    with pytest.raises(RuntimeError, match="injected"):
        commit_bundle(bundle, engine, report.preview_hash)
    with engine.connect() as connection:
        for table in (
            "datasets",
            "import_batches",
            "import_errors",
            "accounts",
            "leads",
            "lead_private",
            "suppression_tombstones",
        ):
            assert connection.scalar(text(f"SELECT count(*) FROM {table}")) == 0


def test_old_snapshot_metrics_do_not_change(engine: Engine, bundle: Path) -> None:
    from datetime import UTC, datetime

    first = commit(engine, bundle)
    start, end = datetime(2026, 8, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC)
    with engine.connect() as connection:
        before = metrics(connection, SYNTHETIC_ORG, first.dataset_id, start, end)
    rows = golden_rows()
    for row in rows["opportunities"]:
        row["source_updated_at"] = "2026-10-02T00:00:00Z"
        if row["external_id"] == "O3":
            row["amount"] = "99.00"
    metadata = manifest()
    metadata["observed_at"] = "2026-10-02T00:00:00Z"
    write_bundle(bundle, metadata, rows)
    second = commit(engine, bundle)
    assert second.version == 2
    with engine.connect() as connection:
        assert metrics(connection, SYNTHETIC_ORG, first.dataset_id, start, end) == before
        assert connection.scalar(text("SELECT version FROM current_datasets")) == 2


def test_large_seeded_bundle_ingests(engine: Engine, tmp_path: Path) -> None:
    path = tmp_path / "demo"
    generate(path, seed=42, leads=1000)
    with engine.connect() as connection:
        report = preview_bundle(path, connection)
    assert report.quarantined == 0
    assert report.duplicates == 0
    assert len(report.rows["leads"]) == 1000
    result = commit_bundle(path, engine, report.preview_hash)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM leads WHERE dataset_id=:id"), {"id": result.dataset_id}
            )
            == 1000
        )


def test_org_mode_isolation(engine: Engine, bundle: Path) -> None:
    metadata = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    metadata["data_mode"] = "real"
    (bundle / "manifest.json").write_text(json.dumps(metadata), encoding="utf-8")
    from revenueos.ingestion import BundleError

    with engine.connect() as connection, pytest.raises(BundleError, match="mode_mismatch"):
        preview_bundle(bundle, connection)
