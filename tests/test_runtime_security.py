from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError

from revenueos.db import actor_context, tenant_context
from revenueos.security import runtime_posture
from revenueos.web import create_app
from revenueos.web_auth import WebSettings, password_hash

pytestmark = pytest.mark.integration


def test_runtime_denies_unscoped_and_cross_org_reads(
    runtime_engine: Engine, intelligence: tuple, engine: Engine
) -> None:
    dataset, principal = intelligence
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("""SELECT count(*) FROM pg_proc p,
            LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
            WHERE p.oid='public.lookup_web_session(text)'::regprocedure
            AND a.grantee=0 AND a.privilege_type='EXECUTE'""")
            )
            == 0
        )
    with runtime_engine.connect() as connection:
        assert runtime_posture(connection)["restricted"] is True
        assert connection.scalar(text("SELECT count(*) FROM leads")) == 0
        assert connection.scalar(text("SELECT count(*) FROM current_datasets")) == 0
    tenant_context.set(principal.organization_id)
    actor_context.set(principal.actor_id)
    with runtime_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM leads")) == 8
        assert connection.scalar(text("SELECT count(*) FROM current_datasets")) == 1
        assert (
            connection.scalar(
                text("SELECT count(*) FROM document_versions WHERE access_scope='management'")
            )
            == 0
        )
    tenant_context.set(uuid4())
    with runtime_engine.connect() as connection:
        assert (
            connection.scalar(
                text("SELECT count(*) FROM leads WHERE dataset_id=:id"), {"id": dataset}
            )
            == 0
        )


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE public.unauthorized_table(id integer)",
        "UPDATE knowledge_memberships SET role='steward'",
        "DELETE FROM datasets",
        "TRUNCATE leads",
        "SET ROLE revenueos_test",
        "INSERT INTO workflow_reviewers(organization_id,actor_id) "
        "VALUES(gen_random_uuid(),gen_random_uuid())",
    ],
)
def test_runtime_privilege_denials(runtime_engine: Engine, intelligence: tuple, sql: str) -> None:
    _, principal = intelligence
    tenant_context.set(principal.organization_id)
    actor_context.set(principal.actor_id)
    with pytest.raises(DBAPIError), runtime_engine.begin() as connection:
        connection.execute(text(sql))


def test_runtime_actual_http_flow_and_pool_scope_reset(
    runtime_engine: Engine, intelligence: tuple
) -> None:
    _, principal = intelligence
    password = "synthetic-runtime-test-password"
    settings = WebSettings(
        "http://localhost",
        "local",
        {
            "reader": {
                "organization_id": str(principal.organization_id),
                "actor_id": str(principal.actor_id),
                "password_hash": password_hash(password),
            }
        },
        "synthetic-state-secret-more-than-32-characters",
    )
    client = TestClient(
        create_app(runtime_engine, settings), base_url=settings.origin, client=("127.0.0.1", 50000)
    )
    assert (
        client.post(
            "/api/auth/login",
            headers={"Origin": settings.origin},
            json={"username": "reader", "password": password},
        ).status_code
        == 200
    )
    csrf = client.get("/api/session").json()["csrf"]
    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    lead = dashboard.json()["priorities"][0]["lead_id"]
    # Known eligible fixture lead, not an assumption about the first ranked lead's lawful use.
    tenant_context.set(principal.organization_id)
    actor_context.set(principal.actor_id)
    with runtime_engine.connect() as connection:
        lead = str(connection.scalar(text("SELECT id FROM leads WHERE external_id='L1'")))
    tenant_context.set(None)
    actor_context.set(None)
    response = client.post(
        "/api/workflows",
        headers={"Origin": settings.origin, "X-CSRF-Token": csrf, "Idempotency-Key": str(uuid4())},
        json={"lead_id": lead, "query": "configuration checklist"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "review_pending"
    with runtime_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM leads")) == 0
