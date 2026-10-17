"""Isolated synthetic restore drill; no existing database is deleted."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import make_url

from revenueos.db import get_engine


def validate_target(url: str, target: str) -> None:
    source = make_url(url)
    if (
        source.host not in ("127.0.0.1", "localhost")
        or not re.fullmatch(r"revenueos_restore_check_[a-z0-9_]{1,30}", target)
        or source.database == target
    ):
        raise ValueError("isolated_local_restore_target_required")


def fingerprint(engine: Engine) -> dict[str, Any]:
    result = {}
    with engine.connect() as connection:
        for table in sorted(inspect(connection).get_table_names()):
            values = list(
                connection.scalars(
                    text(
                        f'SELECT row_to_json(t)::text FROM public."{table}" t '
                        "ORDER BY row_to_json(t)::text"
                    )
                )
            )
            result[table] = {
                "rows": len(values),
                "sha256": hashlib.sha256("\n".join(values).encode()).hexdigest(),
            }
    return result


def run(url: str, target: str, output: Path) -> dict[str, Any]:
    validate_target(url, target)
    source = make_url(url)
    engine = get_engine(url)
    with engine.connect() as connection:
        if connection.scalar(
            text("SELECT count(*) FROM organizations WHERE data_mode<>'synthetic'")
        ):
            raise ValueError("restore_drill_synthetic_only")
        if connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname=:name"), {"name": target}
        ):
            raise ValueError("restore_target_already_exists_preserve_it")
    before = fingerprint(engine)
    archive = Path("work/backups") / f"{target}.dump"
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists() or output.exists():
        raise ValueError("restore_artifacts_already_exist")
    environment = dict(os.environ)
    if source.password:
        environment["PGPASSWORD"] = source.password
    common = [
        "-h",
        source.host or "127.0.0.1",
        "-p",
        str(source.port or 5432),
        "-U",
        source.username or "",
    ]

    def execute(name: str, args: list[str]) -> None:
        binary = Path(os.environ.get("PG_BINDIR", "work/postgres/pgsql/bin")) / (
            name + (".exe" if os.name == "nt" else "")
        )
        executable = str(binary.resolve()) if binary.exists() else shutil.which(name)
        if not executable:
            raise ValueError("postgres_client_binary_required")
        process = subprocess.run(
            [executable, *common, *args],
            env=environment,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if process.returncode:
            raise RuntimeError(f"{name}_failed_exit_{process.returncode}")

    started = time.perf_counter()
    execute(
        "pg_dump",
        [
            "--format=custom",
            "--no-owner",
            "--no-acl",
            "--file",
            str(archive),
            source.database or "",
        ],
    )
    dump_seconds = time.perf_counter() - started
    execute("createdb", [target])
    started = time.perf_counter()
    execute(
        "pg_restore",
        [
            "--no-owner",
            "--no-acl",
            "--single-transaction",
            "--exit-on-error",
            "-d",
            target,
            str(archive),
        ],
    )
    restore_seconds = time.perf_counter() - started
    restored = get_engine(source.set(database=target).render_as_string(hide_password=False))
    try:
        if before != fingerprint(engine) or before != fingerprint(restored):
            raise ValueError("source_changed_or_restore_fingerprint_mismatch")
        with restored.connect() as connection:
            policies = connection.scalar(
                text("SELECT count(*) FROM pg_policies WHERE schemaname='public'")
            )
            version = connection.scalar(text("SELECT version_num FROM alembic_version"))
        report = {
            "evidence_class": "observed_synthetic_restore_drill",
            "target": target,
            "source_database": source.database,
            "dump_seconds": dump_seconds,
            "restore_seconds": restore_seconds,
            "tables": before,
            "schema_version": version,
            "tenant_policies_restored": policies,
            "all_fingerprints_equal": True,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "encryption_tested": False,
            "production_rpo_rto": None,
            "role_grants": "Not restored (--no-acl); re-provision runtime/login grants separately.",
            "cleanup": "Target retained for inspection; no existing database was dropped.",
        }
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return report
    finally:
        engine.dispose()
        restored.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(os.environ["DATABASE_URL"], args.target, args.output)
    print(
        json.dumps(
            {
                key: report[key]
                for key in ("all_fingerprints_equal", "schema_version", "tenant_policies_restored")
            }
        )
    )


if __name__ == "__main__":
    main()
