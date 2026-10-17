import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import Engine

pytestmark = pytest.mark.integration


def test_cli_preview_commit_replay_and_analytics(engine: Engine, bundle: Path) -> None:
    environment = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False)}

    def run(*args: str) -> dict:
        completed = subprocess.run(
            [sys.executable, "-m", "revenueos.cli", *args],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    preview = run("preview", str(bundle))
    result = run("commit", str(bundle), "--confirm", preview["preview_hash"])
    replay = run("commit", str(bundle), "--confirm", preview["preview_hash"])
    assert result["dataset_id"] == replay["dataset_id"]
    assert replay["replayed"] is True
    output = run(
        "analytics",
        "--organization",
        preview["organization_id"],
        "--dataset",
        result["dataset_id"],
        "--start",
        "2026-08-01T00:00:00Z",
        "--end",
        "2026-10-01T00:00:00Z",
    )
    assert output["leads"]["inbound_leads"] == 6
    assert output["open_pipeline_by_currency"][0]["amount"] == "4000.20"


def test_cli_rejects_unconfirmed_import_without_traceback(engine: Engine, bundle: Path) -> None:
    environment = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False)}
    result = subprocess.run(
        [sys.executable, "-m", "revenueos.cli", "commit", str(bundle), "--confirm", "bad"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "preview_changed" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_manifest_error_does_not_echo_input(engine: Engine, bundle: Path) -> None:
    environment = {**os.environ, "DATABASE_URL": engine.url.render_as_string(hide_password=False)}
    (bundle / "manifest.json").write_text('{"private_marker":"DO_NOT_ECHO_THIS"}', encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "revenueos.cli", "preview", str(bundle)],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "DO_NOT_ECHO_THIS" not in result.stderr
    assert "Traceback" not in result.stderr
