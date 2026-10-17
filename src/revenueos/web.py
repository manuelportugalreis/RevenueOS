"""Same-origin synthetic executive dashboard API. No external-action endpoint."""

import json
import logging
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlparse
from uuid import UUID, uuid4

from authlib.integrations.starlette_client import OAuth  # type: ignore[import-untyped]
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from revenueos.analytics import metrics
from revenueos.approvals import decide_action, inspect_action
from revenueos.db import actor_context, tenant_context
from revenueos.knowledge import authorize, resolve_citation
from revenueos.recommendations import open_recommendation
from revenueos.reliability import RequestConflict, submit_workflow
from revenueos.scoring import rank_leads
from revenueos.security import runtime_posture
from revenueos.web_auth import (
    COOKIE,
    WebSettings,
    authenticate,
    google_identity,
    hashed,
    issue_session,
    login_password,
)

logger = logging.getLogger("revenueos.http")


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(Input):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


class Generate(Input):
    lead_id: UUID
    query: str = Field(min_length=1, max_length=500)


class Decision(Input):
    version: int = Field(ge=1)
    payload_hash: str = Field(pattern="^[a-f0-9]{64}$")
    decision: Literal["approve", "reject"]


def create_app(
    engine: Engine,
    settings: WebSettings,
    static: Path | None = None,
    evaluation: Path | None = None,
) -> FastAPI:
    settings.validate()
    if settings.mode == "google":
        with engine.connect() as connection:
            if not runtime_posture(connection)["restricted"]:
                raise ValueError("google_mode_requires_non_owner_runtime_database_role")
    app = FastAPI(title="RevenueOS", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.state.requests = Counter()
    app.state.elapsed = 0.0
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=[urlparse(settings.origin).hostname or "localhost"]
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.state_secret,
        session_cookie="revenueos_oidc",
        max_age=600,
        same_site="lax",
        https_only=settings.mode == "google",
    )
    oauth = OAuth()
    app.state.oauth = oauth
    if settings.mode == "google":
        oauth.register(
            "google",
            client_id=settings.client_id,
            client_secret=settings.client_secret,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email", "code_challenge_method": "S256"},
        )

    @app.middleware("http")
    async def boundary(request: Request, call_next: Any) -> Response:
        request_id, started = str(uuid4()), time.monotonic()
        tenant_token = tenant_context.set(None)
        actor_token = actor_context.set(None)
        request.state.request_id = request_id
        try:
            if settings.mode == "local" and (
                not request.client or request.client.host not in ("127.0.0.1", "::1")
            ):
                raise HTTPException(403, "local_auth_requires_loopback_peer")
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                if request.headers.get("origin") != settings.origin:
                    raise HTTPException(403, "origin_denied")
                if len(await request.body()) > 16384:
                    raise HTTPException(413, "request_too_large")
            response = await call_next(request)
        except HTTPException as exc:
            response = JSONResponse(
                {"error": {"code": exc.detail, "request_id": request_id}},
                status_code=exc.status_code,
            )
        except Exception:
            response = JSONResponse(
                {"error": {"code": "service_unavailable", "request_id": request_id}},
                status_code=503,
            )
        elapsed = time.monotonic() - started
        app.state.requests[str(response.status_code)] += 1
        app.state.elapsed += elapsed
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": request_id,
                    "status": response.status_code,
                    "duration_ms": round(elapsed * 1000),
                }
            )
        )
        response.headers.update(
            {
                "X-Request-ID": request_id,
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "Content-Security-Policy": (
                    "default-src 'self'; script-src 'self'; style-src 'self'; "
                    "img-src 'self' data:; frame-ancestors 'none'; "
                    "base-uri 'none'; form-action 'self'"
                ),
            }
        )
        if settings.mode == "google":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        tenant_context.reset(tenant_token)
        actor_context.reset(actor_token)
        return cast(Response, response)

    async def denied(request: Request, exc: Exception) -> JSONResponse:
        status = (
            exc.status_code
            if isinstance(exc, HTTPException)
            else (
                403
                if isinstance(exc, PermissionError)
                else 409
                if isinstance(exc, ValueError)
                else 422
                if isinstance(exc, RequestValidationError)
                else 503
            )
        )
        code = (
            exc.detail
            if isinstance(exc, HTTPException)
            else {
                403: "access_denied",
                409: "stale_or_invalid_state",
                422: "invalid_request",
                503: "service_unavailable",
            }[status]
        )
        return JSONResponse(
            {"error": {"code": code, "request_id": request.state.request_id}}, status_code=status
        )

    for exception in (
        HTTPException,
        PermissionError,
        ValueError,
        RequestValidationError,
        SQLAlchemyError,
    ):
        app.add_exception_handler(exception, denied)

    @app.get("/health/live")
    def live() -> dict[str, str]:
        return {"status": "live"}

    @app.get("/health/ready")
    def ready() -> dict[str, str]:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT version_num FROM alembic_version")) != "0008":
                raise HTTPException(503, "migration_required")
        return {"status": "ready"}

    @app.get("/api/auth/config")
    def config() -> dict[str, str]:
        return {"mode": settings.mode}

    @app.post("/api/auth/login")
    def login(body: Login, response: Response) -> dict[str, bool]:
        principal = login_password(engine, settings, body.username, body.password)
        issue_session(engine, settings, principal, response)
        return {"authenticated": True}

    @app.get("/auth/google")
    async def google_start(request: Request) -> Response:
        if settings.mode != "google":
            raise HTTPException(404, "not_enabled")
        return cast(
            Response,
            await oauth.google.authorize_redirect(
                request, settings.origin + "/auth/callback", hd=settings.workspace_domain
            ),
        )

    @app.get("/auth/callback")
    async def google_callback(request: Request) -> Response:
        if settings.mode != "google":
            raise HTTPException(404, "not_enabled")
        try:
            token = await oauth.google.authorize_access_token(request)
            principal = google_identity(settings, dict(token["userinfo"]))
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(401, "identity_verification_failed") from None
        response = RedirectResponse("/", status_code=303)
        issue_session(engine, settings, principal, response)
        request.session.clear()
        return response

    @app.get("/api/session")
    def session(request: Request) -> dict[str, Any]:
        principal, csrf = authenticate(request)
        with engine.connect() as connection:
            reviewer = bool(
                connection.scalar(
                    text("""SELECT active FROM workflow_reviewers
                WHERE organization_id=:org AND actor_id=:actor"""),
                    {"org": principal.organization_id, "actor": principal.actor_id},
                )
            )
        return {"csrf": csrf, "reviewer": reviewer, "mode": settings.mode}

    @app.post("/api/auth/logout")
    def logout(request: Request, response: Response) -> dict[str, bool]:
        authenticate(request)
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM web_sessions WHERE token_hash=:hash"),
                {"hash": hashed(request.cookies[COOKIE])},
            )
        response.delete_cookie(COOKIE, path="/")
        return {"authenticated": False}

    def snapshot(connection: Any, principal: Any) -> Any:
        row = (
            connection.execute(
                text("SELECT * FROM current_datasets WHERE organization_id=:org"),
                {"org": principal.organization_id},
            )
            .mappings()
            .first()
        )
        if not row:
            raise HTTPException(404, "no_dataset")
        return row

    @app.get("/api/dashboard")
    def dashboard(
        request: Request, start: datetime | None = None, end: datetime | None = None
    ) -> Any:
        principal, _ = authenticate(request)
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL statement_timeout='10000ms'"))
            dataset = snapshot(connection, principal)
            stop = end or dataset["observed_at"]
            begin = start or stop - timedelta(days=90)
            if (
                not begin.tzinfo
                or not stop.tzinfo
                or not begin < stop
                or stop - begin > timedelta(days=366)
            ):
                raise HTTPException(422, "invalid_interval")
            values = metrics(connection, principal.organization_id, dataset["id"], begin, stop)
            priorities = rank_leads(connection, principal.organization_id, dataset["id"])
            scores = {item["lead_id"]: item for item in priorities["scores"]}
            top = [scores[key] for key in priorities["queues"]["rules"][:20]]
            runs = list(
                connection.execute(
                    text("""SELECT id,state,failure_code,created_at FROM ai_runs
                WHERE organization_id=:org AND actor_id=:actor
                ORDER BY created_at DESC LIMIT 20"""),
                    {"org": principal.organization_id, "actor": principal.actor_id},
                ).mappings()
            )
            actions = list(
                connection.execute(
                    text("""SELECT a.id,a.state,a.current_version,a.created_at
                FROM outreach_actions a WHERE a.organization_id=:org
                  AND EXISTS(SELECT 1 FROM workflow_reviewers r WHERE r.organization_id=:org
                             AND r.actor_id=:actor AND r.active)
                ORDER BY a.created_at DESC LIMIT 20"""),
                    {"org": principal.organization_id, "actor": principal.actor_id},
                ).mappings()
            )
            usage = list(
                connection.execute(
                    text("""SELECT a.cost_basis,a.state,count(*) AS attempts,
                sum(a.estimated_cost_usd) AS estimated_cost_usd
                FROM ai_attempts a WHERE a.organization_id=:org GROUP BY a.cost_basis,a.state"""),
                    {"org": principal.organization_id},
                ).mappings()
            )
        evidence = (
            json.loads(evaluation.read_text()) if evaluation and evaluation.exists() else None
        )
        return jsonable_encoder(
            {
                "metrics": values,
                "priorities": top,
                "recommendations": runs,
                "actions": actions,
                "costs": usage,
                "evaluation": evidence,
                "quality_notice": (
                    "Recommendation quality gate remains failed; "
                    "no predictive model or measured ROI."
                ),
                "generated_at": datetime.now(UTC),
                "external_delivery_enabled": False,
            }
        )

    @app.get("/api/recommendations/{run}")
    def recommendation(run: UUID, request: Request) -> Any:
        principal, _ = authenticate(request)
        with engine.connect() as connection:
            return jsonable_encoder(open_recommendation(connection, principal, run))

    @app.get("/api/citations/{chunk}")
    def citation(chunk: UUID, request: Request) -> Any:
        principal, _ = authenticate(request)
        with engine.connect() as connection:
            return resolve_citation(connection, principal, chunk).model_dump(mode="json")

    @app.post("/api/workflows")
    def generate(body: Generate, request: Request) -> Any:
        principal, _ = authenticate(request)
        try:
            key = UUID(request.headers.get("Idempotency-Key", str(uuid4())))
        except ValueError:
            raise HTTPException(422, "invalid_idempotency_key") from None
        try:
            result = submit_workflow(engine, principal, body.lead_id, body.query, key)
        except RequestConflict as exc:
            raise HTTPException(
                429 if str(exc) == "workflow_rate_limited" else 409, str(exc)
            ) from None
        return jsonable_encoder(result)

    @app.get("/api/actions/{action}")
    def inspect(action: UUID, request: Request) -> Any:
        principal, _ = authenticate(request)
        return jsonable_encoder(inspect_action(engine, principal, action))

    @app.post("/api/actions/{action}/decision")
    def review(action: UUID, body: Decision, request: Request) -> Any:
        principal, _ = authenticate(request)
        return decide_action(
            engine, principal, action, body.version, body.payload_hash, body.decision
        )

    @app.get("/api/monitoring")
    def monitoring(request: Request) -> dict[str, Any]:
        principal, _ = authenticate(request)
        with engine.connect() as connection:
            authorize(connection, principal, steward=True)
            posture = runtime_posture(connection)
        return {
            "requests_by_status": dict(app.state.requests),
            "duration_seconds_sum": app.state.elapsed,
            "scope": "this process since start",
            "database_posture": posture,
            "external_delivery_enabled": False,
        }

    if static and (static / "assets").exists():
        app.mount("/assets", StaticFiles(directory=static / "assets"), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(static / "index.html")

    return app


def application() -> FastAPI:
    import os

    from revenueos.db import get_engine

    return create_app(
        get_engine(),
        WebSettings.environment(),
        Path(os.environ.get("REVENUEOS_STATIC", "frontend/dist")),
        Path("data/dashboard/evaluation.json"),
    )
