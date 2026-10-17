"""Server-mapped identities and revocable opaque sessions; no browser-owned scope."""

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, Request, Response
from sqlalchemy import Engine, text

from revenueos.db import actor_context, tenant_context
from revenueos.knowledge import Principal, authorize

COOKIE = "revenueos_session"


def hashed(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000).hex()
    return f"{salt}:{value}"


@dataclass(frozen=True)
class WebSettings:
    origin: str
    mode: str
    identities: dict[str, Any]
    state_secret: str
    workspace_domain: str = ""
    client_id: str = ""
    client_secret: str = ""

    @classmethod
    def environment(cls) -> "WebSettings":
        settings = cls(
            os.environ["REVENUEOS_ORIGIN"].rstrip("/"),
            os.environ["REVENUEOS_AUTH_MODE"],
            json.loads(os.environ["REVENUEOS_IDENTITIES"]),
            os.environ["REVENUEOS_STATE_SECRET"],
            os.environ.get("GOOGLE_WORKSPACE_DOMAIN", ""),
            os.environ.get("GOOGLE_CLIENT_ID", ""),
            os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        url = urlparse(self.origin)
        if len(self.state_secret) < 32 or url.path or url.query or url.fragment or url.username:
            raise ValueError("invalid_origin_or_state_secret")
        if self.mode == "local":
            if url.scheme != "http" or url.hostname not in ("localhost", "127.0.0.1"):
                raise ValueError("local_auth_is_loopback_only")
        elif self.mode == "google":
            if url.scheme != "https" or not all(
                (self.workspace_domain, self.client_id, self.client_secret)
            ):
                raise ValueError("google_https_configuration_required")
        else:
            raise ValueError("unsupported_auth_mode")
        for identity in self.identities.values():
            Principal.model_validate(
                {key: identity[key] for key in ("organization_id", "actor_id")}
            )


def mapped(settings: WebSettings, key: str) -> Principal:
    row = settings.identities.get(key)
    if not row:
        raise HTTPException(403, "identity_not_provisioned")
    return Principal(organization_id=row["organization_id"], actor_id=row["actor_id"])


def google_identity(settings: WebSettings, claims: dict[str, Any]) -> Principal:
    # Called only after Authlib verifies token signature, issuer/audience, expiry and nonce.
    if claims.get("hd") != settings.workspace_domain or claims.get("email_verified") is not True:
        raise HTTPException(403, "workspace_identity_required")
    return mapped(settings, "google:" + str(claims.get("sub", "")))


def issue_session(
    engine: Engine, settings: WebSettings, principal: Principal, response: Response
) -> None:
    tenant_context.set(principal.organization_id)
    actor_context.set(principal.actor_id)
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    with engine.begin() as connection:
        authorize(connection, principal)
        mode = connection.scalar(
            text("SELECT data_mode FROM organizations WHERE id=:org"),
            {"org": principal.organization_id},
        )
        if mode != "synthetic":
            raise HTTPException(403, "real_data_not_enabled")
        connection.execute(text("DELETE FROM web_sessions WHERE expires_at<=now()"))
        connection.execute(
            text("""INSERT INTO web_sessions
            (token_hash,organization_id,actor_id,csrf_token,expires_at)
            VALUES(:hash,:org,:actor,:csrf,:expiry)"""),
            {
                "hash": hashed(token),
                "org": principal.organization_id,
                "actor": principal.actor_id,
                "csrf": csrf,
                "expiry": datetime.now(UTC) + timedelta(hours=2),
            },
        )
    response.set_cookie(
        COOKIE,
        token,
        max_age=7200,
        httponly=True,
        samesite="strict",
        secure=settings.mode == "google",
        path="/",
    )


def authenticate(request: Request) -> tuple[Principal, str]:
    engine = request.app.state.engine
    token = request.cookies.get(COOKIE, "")
    if len(token) > 100 or not token:
        raise HTTPException(401, "sign_in_required")
    with engine.connect() as connection:
        row = (
            connection.execute(
                text("SELECT * FROM public.lookup_web_session(:hash)"),
                {"hash": hashed(token)},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(401, "session_expired")
        principal = Principal(organization_id=row["organization_id"], actor_id=row["actor_id"])
    tenant_context.set(principal.organization_id)
    actor_context.set(principal.actor_id)
    with engine.connect() as connection:
        try:
            authorize(connection, principal)
        except PermissionError:
            raise HTTPException(401, "session_revoked") from None
        if (
            connection.scalar(
                text("SELECT data_mode FROM organizations WHERE id=:org"),
                {"org": principal.organization_id},
            )
            != "synthetic"
        ):
            raise HTTPException(403, "real_data_not_enabled")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), row["csrf_token"]):
            raise HTTPException(403, "csrf_failed")
    return principal, row["csrf_token"]


def login_password(
    engine: Engine, settings: WebSettings, username: str, password: str
) -> Principal:
    if settings.mode != "local":
        raise HTTPException(403, "password_login_disabled")
    key = hashed(username)
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": int(key[:15], 16)})
        connection.execute(
            text("DELETE FROM web_login_attempts WHERE occurred_at<now()-interval '1 day'")
        )
        count = connection.scalar(
            text("""SELECT count(*) FROM web_login_attempts
            WHERE key_hash=:key AND occurred_at>now()-interval '15 minutes'"""),
            {"key": key},
        )
        if count >= 5:
            raise HTTPException(429, "login_temporarily_limited")
        connection.execute(
            text("INSERT INTO web_login_attempts(key_hash) VALUES(:key)"), {"key": key}
        )
        stored = settings.identities.get(username, {}).get("password_hash", "dummy:" + "0" * 64)
        salt, _, expected = stored.partition(":")
        valid = hmac.compare_digest(password_hash(password, salt).partition(":")[2], expected)
    if not valid:
        raise HTTPException(401, "invalid_credentials")
    return mapped(settings, username)
