"""Seed synthetic fixtures idempotently and serve an authenticated loopback dashboard."""

import json
import logging
import os
import secrets
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from revenueos.approvals import assign_reviewer
from revenueos.db import get_engine
from revenueos.evaluation import READER, STEWARD, seed_knowledge
from revenueos.ingestion import commit_bundle, preview_bundle
from revenueos.knowledge import Principal
from revenueos.security import runtime_posture
from revenueos.synthetic import SYNTHETIC_ORG, generate
from revenueos.web import create_app
from revenueos.web_auth import WebSettings, password_hash


def main() -> None:
    password = os.environ["REVENUEOS_DEMO_PASSWORD"]
    if len(password) < 16:
        raise ValueError("Use a demo password of at least 16 characters")
    engine = get_engine()
    command.upgrade(Config("alembic.ini"), "head")
    bundle = Path("work/dashboard-golden")
    generate(bundle, golden=True)
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO organizations(id,name,data_mode,default_currency)
            VALUES(:org,'SYNTHETIC Dashboard','synthetic','USD') ON CONFLICT DO NOTHING"""),
            {"org": SYNTHETIC_ORG},
        )
    with engine.connect() as connection:
        report = preview_bundle(bundle, connection)
    commit_bundle(bundle, engine, report.preview_hash)
    with engine.begin() as connection:
        seed_knowledge(connection, SYNTHETIC_ORG, Path("data/intelligence/corpus.json"))
        assign_reviewer(
            connection, Principal(organization_id=SYNTHETIC_ORG, actor_id=STEWARD), STEWARD
        )
        lead = connection.scalar(
            text("SELECT id FROM leads WHERE organization_id=:org AND external_id='L1' LIMIT 1"),
            {"org": SYNTHETIC_ORG},
        )
    settings = WebSettings(
        "http://127.0.0.1:8000",
        "local",
        {
            name: {
                "organization_id": str(SYNTHETIC_ORG),
                "actor_id": str(actor),
                "password_hash": password_hash(password),
            }
            for name, actor in (("executive", READER), ("reviewer", STEWARD))
        },
        secrets.token_urlsafe(48),
    )
    Path("work/dashboard-demo-reference.json").write_text(json.dumps({"lead_id": str(lead)}))
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    runtime_url = os.environ.get("REVENUEOS_RUNTIME_DATABASE_URL")
    web_engine = get_engine(runtime_url) if runtime_url else engine
    if runtime_url:
        with web_engine.connect() as connection:
            if not runtime_posture(connection)["restricted"]:
                raise ValueError("configured_runtime_role_is_not_restricted")
    app = create_app(
        web_engine, settings, Path("frontend/dist"), Path("data/dashboard/evaluation.json")
    )
    uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()
