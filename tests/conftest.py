"""Only an explicitly disposable local PostgreSQL database may be reset."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.engine import make_url

from revenueos.db import get_engine
from revenueos.synthetic import SYNTHETIC_ORG, generate

ROOT = Path(__file__).resolve().parents[1]


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--require-db", action="store_true", help="Fail instead of skipping DB tests")


@pytest.fixture(scope="session")
def db_engine(request: pytest.FixtureRequest) -> Iterator[Engine]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        if request.config.getoption("--require-db"):
            pytest.fail("TEST_DATABASE_URL is required")
        pytest.skip("TEST_DATABASE_URL absent; database integration NOT verified")
    target = make_url(url)
    if (
        target.host not in ("127.0.0.1", "localhost")
        or target.database != "revenueos_test"
        or os.environ.get("REVENUEOS_TEST_ALLOW_RESET") != "1"
    ):
        pytest.fail("Refusing reset: local revenueos_test DB and explicit reset consent required")
    os.environ["DATABASE_URL"] = url
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    engine = get_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def engine(db_engine: Engine) -> Engine:
    # All names are fixed application tables. No schema/database DROP or unrelated data reset.
    tables = (
        "web_workflow_requests,web_sessions,web_login_attempts,"
        "action_receipts,action_approvals,outreach_versions,outreach_actions,workflow_audit,"
        "workflow_reviewers,bounded_workflows,"
        "ai_attempts,ai_runs,ai_budgets,score_runs,document_chunks,document_versions,documents,"
        "knowledge_memberships,"
        "suppression_tombstones,lead_outcomes,opportunity_stage_events,opportunity_leads,"
        "interactions,lead_private,opportunities,leads,accounts,import_errors,datasets,"
        "import_batches,organizations"
    )
    with db_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY"))
        connection.execute(
            text(
                "INSERT INTO organizations(id,name,data_mode,default_currency) "
                "VALUES (:org,'SYNTHETIC Test','synthetic','USD')"
            ),
            {"org": SYNTHETIC_ORG},
        )
    return db_engine


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    path = tmp_path / "bundle"
    generate(path, golden=True)
    return path


@pytest.fixture
def intelligence(engine: Engine, bundle: Path) -> tuple[object, object]:
    from revenueos.evaluation import READER, seed_knowledge
    from revenueos.ingestion import commit_bundle, preview_bundle
    from revenueos.knowledge import Principal

    with engine.connect() as connection:
        report = preview_bundle(bundle, connection)
    dataset = commit_bundle(bundle, engine, report.preview_hash).dataset_id
    with engine.begin() as connection:
        seed_knowledge(connection, SYNTHETIC_ORG, ROOT / "data/intelligence/corpus.json")
    return dataset, Principal(organization_id=SYNTHETIC_ORG, actor_id=READER)


@pytest.fixture
def runtime_engine(engine: Engine) -> Iterator[Engine]:
    from revenueos.db import actor_context, tenant_context
    from revenueos.security import install_runtime_role

    with engine.begin() as connection:
        install_runtime_role(connection, "revenueos_runtime_test")
        if not connection.scalar(
            text("SELECT 1 FROM pg_roles WHERE rolname='revenueos_runtime_login_test'")
        ):
            connection.execute(
                text("""CREATE ROLE revenueos_runtime_login_test LOGIN
                NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS
                PASSWORD 'synthetic-runtime-fixture-only'""")
            )
        connection.execute(text("GRANT revenueos_runtime_test TO revenueos_runtime_login_test"))
    restricted = get_engine(
        engine.url.set(
            username="revenueos_runtime_login_test", password="synthetic-runtime-fixture-only"
        ).render_as_string(hide_password=False)
    )

    org_token = tenant_context.set(None)
    actor_token = actor_context.set(None)
    try:
        yield restricted
    finally:
        restricted.dispose()
        tenant_context.reset(org_token)
        actor_context.reset(actor_token)
