from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from revenueos.approvals import assign_reviewer
from revenueos.evaluation import STEWARD
from revenueos.knowledge import Principal
from revenueos.web import create_app
from revenueos.web_auth import WebSettings, google_identity, password_hash

pytestmark = pytest.mark.integration
PASSWORD = "Synthetic-test-password-2026!"
PASSWORD_HASH = password_hash(PASSWORD)


@pytest.fixture
def web(engine: Engine, intelligence: tuple) -> tuple[TestClient, WebSettings]:
    _, principal = intelligence
    settings = WebSettings(
        "http://localhost",
        "local",
        {
            "reader": {
                "organization_id": str(principal.organization_id),
                "actor_id": str(principal.actor_id),
                "password_hash": PASSWORD_HASH,
            },
            "reviewer": {
                "organization_id": str(principal.organization_id),
                "actor_id": str(STEWARD),
                "password_hash": PASSWORD_HASH,
            },
        },
        "test-state-secret-with-at-least-32-characters",
    )
    with engine.begin() as connection:
        steward = Principal(organization_id=principal.organization_id, actor_id=STEWARD)
        assign_reviewer(connection, steward, STEWARD)
    client = TestClient(
        create_app(engine, settings, evaluation=Path("data/dashboard/evaluation.json")),
        base_url="http://localhost",
        client=("127.0.0.1", 50000),
    )
    return client, settings


def login(client: TestClient, username: str = "reader") -> str:
    response = client.post(
        "/api/auth/login",
        headers={"Origin": "http://localhost"},
        json={"username": username, "password": PASSWORD},
    )
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    return client.get("/api/session").json()["csrf"]


def test_http_metrics_and_sessions(web: tuple, engine: Engine) -> None:
    client, _ = web
    assert client.get("/api/dashboard").status_code == 401
    csrf = login(client)
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["metrics"]["data_mode"] == "synthetic"
    assert data["metrics"]["leads"]["inbound_leads"] == 6
    assert data["metrics"]["opportunities"]["win_rate"] == 0.5
    assert data["actions"] == []
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/monitoring").status_code == 403
    token = client.cookies.get("revenueos_session")
    with engine.connect() as connection:
        assert token not in str(connection.execute(text("SELECT * FROM web_sessions")).all())
    assert (
        client.post(
            "/api/auth/logout",
            json={},
            headers={"Origin": "http://localhost", "X-CSRF-Token": csrf},
        ).status_code
        == 200
    )
    assert client.get("/api/dashboard").status_code == 401


@pytest.mark.parametrize(
    "fault", ["origin", "csrf", "expired", "revoked", "extra_scope", "interval"]
)
def test_http_boundaries(web: tuple, engine: Engine, fault: str) -> None:
    client, _ = web
    csrf = login(client)
    headers = {"Origin": "http://localhost", "X-CSRF-Token": csrf}
    if fault == "origin":
        headers["Origin"] = "https://attacker.example"
    elif fault == "csrf":
        headers["X-CSRF-Token"] = "invalid"
    elif fault in ("expired", "revoked"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE web_sessions SET expires_at=:past")
                if fault == "expired"
                else text("UPDATE knowledge_memberships SET active=false"),
                {"past": datetime.now(UTC) - timedelta(hours=1)},
            )
    elif fault == "interval":
        assert client.get("/api/dashboard?start=2026-10-01&end=2026-09-01").status_code == 422
        return
    response = client.post(
        "/api/workflows",
        headers=headers,
        json={
            "lead_id": str(uuid4()),
            "query": "configuration checklist",
            **({"organization_id": str(uuid4())} if fault == "extra_scope" else {}),
        },
    )
    assert response.status_code in (401, 403, 422)


def test_exact_version_review_via_http(web: tuple, engine: Engine, intelligence: tuple) -> None:
    client, _ = web
    csrf = login(client)
    dataset, _ = intelligence
    with engine.connect() as connection:
        lead = connection.scalar(
            text("SELECT id FROM leads WHERE dataset_id=:id AND external_id='L1'"), {"id": dataset}
        )
    result = client.post(
        "/api/workflows",
        headers={"Origin": "http://localhost", "X-CSRF-Token": csrf},
        json={"lead_id": str(lead), "query": "configuration checklist"},
    )
    assert result.status_code == 200
    action = result.json()["action"]
    assert client.get("/api/actions/" + action["action_id"]).status_code == 403
    csrf = login(client, "reviewer")
    inspection = client.get("/api/actions/" + action["action_id"]).json()
    assert inspection["payload"]["recipient"] == "lead1@one.example"
    headers = {"Origin": "http://localhost", "X-CSRF-Token": csrf}
    decision = {"version": 1, "payload_hash": inspection["payload_hash"], "decision": "approve"}
    url = "/api/actions/" + action["action_id"] + "/decision"
    assert client.post(url, headers=headers, json=decision).status_code == 200
    assert client.post(url, headers=headers, json=decision).status_code == 403
    assert client.post("/api/send", headers=headers, json={}).status_code == 404
    assert client.get("/api/monitoring").status_code == 200
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM action_receipts")) == 0


def test_login_rate_limit_and_redaction(web: tuple) -> None:
    client, _ = web
    for _ in range(5):
        assert (
            client.post(
                "/api/auth/login",
                headers={"Origin": "http://localhost"},
                json={"username": "reader", "password": "SECRET-wrong"},
            ).status_code
            == 401
        )
    response = client.post(
        "/api/auth/login",
        headers={"Origin": "http://localhost"},
        json={"username": "reader", "password": PASSWORD},
    )
    assert response.status_code == 429 and PASSWORD not in response.text
    invalid = client.post(
        "/api/auth/login",
        headers={"Origin": "http://localhost"},
        json={"password": "SECRET-wrong", "extra": "untrusted"},
    )
    assert invalid.status_code == 422 and "SECRET" not in invalid.text


def test_workflow_attempt_rate_limit(web: tuple, engine: Engine) -> None:
    client, _ = web
    csrf = login(client)
    for _ in range(10):
        response = client.post(
            "/api/workflows",
            json={"lead_id": str(uuid4()), "query": "onboarding"},
            headers={"Origin": "http://localhost", "X-CSRF-Token": csrf},
        )
        assert response.status_code == 409
    response = client.post(
        "/api/workflows",
        json={"lead_id": str(uuid4()), "query": "onboarding"},
        headers={"Origin": "http://localhost", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 429
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM bounded_workflows")) == 0


def test_real_data_login_blocked(web: tuple, engine: Engine) -> None:
    _, settings = web
    real_org = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("""INSERT INTO organizations(id,name,data_mode,default_currency)
            VALUES(:org,'Real-mode access guard fixture','real','USD')"""),
            {"org": real_org},
        )
        connection.execute(
            text("""INSERT INTO knowledge_memberships
            (organization_id,actor_id,role,scopes) VALUES(:org,:actor,'reader',ARRAY['team'])"""),
            {"org": real_org, "actor": settings.identities["reader"]["actor_id"]},
        )
    identities = {key: dict(value) for key, value in settings.identities.items()}
    identities["reader"]["organization_id"] = str(real_org)
    client = TestClient(
        create_app(engine, replace(settings, identities=identities)),
        base_url=settings.origin,
        client=("127.0.0.1", 50000),
    )
    assert (
        client.post(
            "/api/auth/login",
            headers={"Origin": "http://localhost"},
            json={"username": "reader", "password": PASSWORD},
        ).status_code
        == 403
    )


def test_database_outage_is_redacted(web: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = web
    login(client)

    def broken(*args: object, **kwargs: object) -> None:
        raise RuntimeError("SECRET database password")

    monkeypatch.setattr(client.app.state.engine, "connect", broken)
    response = client.get("/api/dashboard")
    assert response.status_code == 503 and "SECRET" not in response.text
    assert response.json()["error"]["request_id"]


def test_google_policy_and_untrusted_callback(web: tuple, runtime_engine: Engine) -> None:
    _, local = web
    identity = local.identities["reader"]
    google = replace(
        local,
        mode="google",
        origin="https://revenue.example",
        workspace_domain="business.example",
        client_id="test",
        client_secret="test",
        identities={"google:subject-1": identity},
    )
    google.validate()
    claims = {"hd": "business.example", "email_verified": True, "sub": "subject-1"}
    assert (
        google_identity(google, claims).actor_id
        == Principal.model_validate(
            {key: identity[key] for key in ("organization_id", "actor_id")}
        ).actor_id
    )
    for change in ({"hd": "attacker.example"}, {"email_verified": False}, {"sub": "unprovisioned"}):
        with pytest.raises(HTTPException):
            google_identity(google, {**claims, **change})
    client = TestClient(create_app(runtime_engine, google), base_url=google.origin)
    assert client.get("/auth/callback?state=forged&code=forged").status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            headers={"Origin": google.origin},
            json={"username": "reader", "password": PASSWORD},
        ).status_code
        == 403
    )
    with pytest.raises(ValueError):
        replace(local, origin="http://0.0.0.0").validate()


def test_local_peer_body_and_health_boundaries(web: tuple, engine: Engine) -> None:
    client, settings = web
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200
    remote = TestClient(
        create_app(engine, settings), base_url=settings.origin, client=("192.0.2.1", 50000)
    )
    assert remote.get("/api/auth/config").status_code == 403
    assert client.get("/api/auth/config", headers={"Host": "attacker.example"}).status_code == 400
    response = client.post(
        "/api/auth/login", headers={"Origin": settings.origin}, content="x" * 16385
    )
    assert response.status_code == 413
