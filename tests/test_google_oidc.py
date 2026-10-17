"""Real Authlib/JWT verification against an offline HTTP transport, never Google."""

import time
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from fastapi.testclient import TestClient
from joserfc import jwt
from joserfc.jwk import RSAKey
from sqlalchemy import Engine

from revenueos.web import create_app
from revenueos.web_auth import WebSettings

pytestmark = pytest.mark.integration


@pytest.mark.parametrize(
    "fault", [None, "audience", "signature", "nonce", "expired", "workspace", "issuer"]
)
def test_oidc_signature_nonce_and_claims(
    engine: Engine, intelligence: tuple, fault: str | None, runtime_engine: Engine
) -> None:
    _, principal = intelligence
    settings = WebSettings(
        "https://revenue.example",
        "google",
        {
            "google:sub-1": {
                "organization_id": str(principal.organization_id),
                "actor_id": str(principal.actor_id),
            }
        },
        "oidc-test-state-secret-longer-than-32-characters",
        "company.example",
        "client-1",
        "secret",
    )
    app = create_app(runtime_engine, settings)
    key, wrong_key = RSAKey.generate_key(2048), RSAKey.generate_key(2048)
    nonce = ""
    requests = []

    def transport(request: httpx2.Request) -> httpx2.Response:
        requests.append(str(request.url))
        if request.url.path.endswith("openid-configuration"):
            body = {
                "issuer": "https://accounts.google.com",
                "authorization_endpoint": "https://accounts.google.com/authorize",
                "token_endpoint": "https://accounts.google.com/token",
                "jwks_uri": "https://accounts.google.com/jwks",
                "id_token_signing_alg_values_supported": ["RS256"],
                "response_types_supported": ["code"],
            }
        elif request.url.path == "/jwks":
            body = {"keys": [{**key.as_dict(private=False), "kid": "key-1"}]}
        elif request.url.path == "/token":
            now = int(time.time())
            claims = {
                "iss": "https://wrong.example"
                if fault == "issuer"
                else "https://accounts.google.com",
                "sub": "sub-1",
                "aud": "wrong" if fault == "audience" else "client-1",
                "iat": now - 4000 if fault == "expired" else now,
                "exp": now - 3600 if fault == "expired" else now + 300,
                "nonce": "wrong" if fault == "nonce" else nonce,
                "hd": "wrong.example" if fault == "workspace" else "company.example",
                "email_verified": True,
            }
            token = jwt.encode(
                {"alg": "RS256", "kid": "key-1"}, claims, wrong_key if fault == "signature" else key
            )
            body = {"access_token": "offline-test-token", "token_type": "Bearer", "id_token": token}
        else:
            raise AssertionError("Unexpected network URL")
        return httpx2.Response(200, json=body)

    app.state.oauth.google.client_kwargs["transport"] = httpx2.MockTransport(transport)
    client = TestClient(app, base_url=settings.origin)
    redirect = client.get("/auth/google", follow_redirects=False)
    assert redirect.status_code == 302
    query = parse_qs(urlparse(redirect.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    nonce = query["nonce"][0]
    callback = client.get(
        "/auth/callback",
        params={"state": query["state"][0], "code": "offline-code"},
        follow_redirects=False,
    )
    if fault is None:
        assert callback.status_code == 303
        assert "Secure" in callback.headers["set-cookie"]
        assert client.get("/api/session").status_code == 200
        assert (
            client.get(
                "/auth/callback",
                params={"state": query["state"][0], "code": "offline-code"},
                follow_redirects=False,
            ).status_code
            == 401
        )
    else:
        assert callback.status_code in (401, 403)
        assert client.get("/api/session").status_code == 401
    assert all(url.startswith("https://accounts.google.com/") for url in requests)
