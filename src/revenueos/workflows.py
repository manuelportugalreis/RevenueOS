"""Bounded, read-only tool dispatch followed by a separately validated draft proposal."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import Connection, Engine, text

from revenueos.analytics import metrics
from revenueos.audit import record
from revenueos.ingestion import digest
from revenueos.knowledge import Principal, authorize, search
from revenueos.providers import Provider
from revenueos.recommendations import PriceCard, recommend
from revenueos.scoring import lead_context, score_context

POLICY_VERSION = "bounded_reads_v1"
_monotonic = time.monotonic


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class SearchArguments(Arguments):
    query: str = Field(min_length=1, max_length=500)


class MetricArguments(Arguments):
    metric: Literal["inbound_leads", "qualification_rate", "win_rate", "open_pipeline_by_currency"]
    start: AwareDatetime
    end: AwareDatetime


class ToolCall(Arguments):
    name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any]


class Plan(Arguments):
    calls: list[ToolCall] = Field(min_length=1, max_length=4)


TOOLS: dict[str, type[Arguments]] = {
    "get_lead_context": Arguments,
    "get_priority_explanation": Arguments,
    "search_approved_knowledge": SearchArguments,
    "get_metric": MetricArguments,
}


def tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "name": name,
            "description": "Read-only; scope is supplied by server policy.",
            "parameters": contract.model_json_schema(),
            "side_effects": False,
        }
        for name, contract in TOOLS.items()
    ]


class Planner(Protocol):
    def plan(self, schemas: list[dict[str, Any]], attempt: int) -> str: ...


@dataclass
class ScriptedPlanner:
    """Offline adversarial model-output fixture; never calls a model API."""

    script: Callable[[list[dict[str, Any]], int], str]
    calls: int = field(default=0, init=False)

    def plan(self, schemas: list[dict[str, Any]], attempt: int) -> str:
        self.calls += 1
        return self.script(schemas, attempt)


@dataclass(frozen=True)
class Scope:
    principal: Principal
    dataset: UUID
    lead: UUID


def dispatch(connection: Connection, scope: Scope, call: ToolCall, now: datetime) -> dict[str, Any]:
    authorize(connection, scope.principal)
    if call.name not in TOOLS:
        raise PermissionError("tool_not_allowlisted")
    arguments = TOOLS[call.name].model_validate_json(json.dumps(call.arguments))
    context = lead_context(connection, scope.principal.organization_id, scope.dataset, scope.lead)
    if context["data_mode"] != "synthetic":
        raise PermissionError("real_data_workflows_disabled")
    current = connection.scalar(
        text("SELECT id FROM current_datasets WHERE organization_id=:org"),
        {"org": scope.principal.organization_id},
    )
    if current != scope.dataset:
        raise PermissionError("snapshot_no_longer_current")
    if call.name == "get_lead_context":
        result = {
            "lead_id": str(scope.lead),
            "dataset_id": str(scope.dataset),
            "source": context["source"],
            "status": context["status"],
            "employee_band": context["employee_band"],
            "observed_at": context["observed_at"].isoformat(),
        }
    elif call.name == "get_priority_explanation":
        result = score_context(context)
    elif isinstance(arguments, SearchArguments):
        result = {
            "citations": [
                citation.model_dump(mode="json")
                for citation in search(
                    connection, scope.principal, arguments.query, limit=5, at=now
                )
            ]
        }
    else:
        assert isinstance(arguments, MetricArguments)
        if arguments.start >= arguments.end or arguments.end - arguments.start > timedelta(
            days=366
        ):
            raise ValueError("metric_interval_out_of_bounds")
        values = metrics(
            connection,
            scope.principal.organization_id,
            scope.dataset,
            arguments.start,
            arguments.end,
        )
        if arguments.metric == "open_pipeline_by_currency":
            value = values[arguments.metric]
        elif arguments.metric == "win_rate":
            value = values["opportunities"]
        else:
            value = values["leads"]
        result = {
            "metric": arguments.metric,
            "value": value,
            "lineage": {
                key: values[key]
                for key in ("metric_version", "dataset_id", "observed_at", "interval")
            },
        }
    if len(json.dumps(result, default=str).encode()) > 16384:
        raise ValueError("tool_result_size_limit")
    return result


def _terminal(
    engine: Engine,
    scope: Scope,
    workflow: UUID,
    state: str,
    code: str | None,
    recommendation: UUID | None = None,
) -> dict[str, Any]:
    with engine.begin() as connection:
        connection.execute(
            text("SELECT id FROM organizations WHERE id=:org FOR UPDATE"),
            {"org": scope.principal.organization_id},
        )
        current = (
            connection.execute(
                text("""SELECT state,failure_code,recommendation_id
            FROM bounded_workflows WHERE organization_id=:org AND id=:id FOR UPDATE"""),
                {"org": scope.principal.organization_id, "id": workflow},
            )
            .mappings()
            .one()
        )
        if current["state"] == "failed" and current["failure_code"] == "interrupted_reconciled":
            return {
                "workflow_id": str(workflow),
                "state": "failed",
                "failure_code": "interrupted_reconciled",
                "recommendation_id": None,
                "policy_version": POLICY_VERSION,
                "external_delivery_enabled": False,
            }
        record(
            connection,
            scope.principal,
            "workflow_finished",
            state,
            {"code": code, "recommendation_id": str(recommendation)},
            workflow,
        )
        connection.execute(
            text("""
            UPDATE bounded_workflows SET state=:state,failure_code=:code,
              recommendation_id=:recommendation,completed_at=now() WHERE id=:id
        """),
            {"state": state, "code": code, "recommendation": recommendation, "id": workflow},
        )
    return {
        "workflow_id": str(workflow),
        "state": state,
        "failure_code": code,
        "recommendation_id": str(recommendation) if recommendation else None,
        "policy_version": POLICY_VERSION,
        "external_delivery_enabled": False,
    }


def run_workflow(
    engine: Engine,
    principal: Principal,
    dataset: UUID,
    lead: UUID,
    query: str,
    *,
    planner: Planner | None = None,
    provider: Provider | None = None,
    price: PriceCard | None = None,
    deadline_seconds: float = 30,
    evidence_at: datetime | None = None,
    quality_profile: Literal["legacy_v1", "focused_v2"] = "focused_v2",
    on_started: Callable[[UUID], None] | None = None,
) -> dict[str, Any]:
    evidence_at = evidence_at or datetime.now(UTC)
    if evidence_at.tzinfo is None:
        raise ValueError("aware_evidence_time_required")
    if not 0 < deadline_seconds <= 30 or not 0 < len(query.strip()) <= 500:
        raise ValueError("invalid_workflow_request_bounds")
    # Planning is deliberately offline. Remote planner accounting is not implemented.
    if planner is not None and type(planner) is not ScriptedPlanner:
        raise PermissionError("only_offline_scripted_planner_supported")
    scope, workflow = Scope(principal, dataset, lead), uuid4()
    started = _monotonic()
    with engine.begin() as connection:
        authorize(connection, principal)
        context = lead_context(connection, principal.organization_id, dataset, lead)
        if context["data_mode"] != "synthetic":
            raise PermissionError("real_data_workflows_disabled")
        connection.execute(
            text("""
            INSERT INTO bounded_workflows(id,organization_id,dataset_id,lead_id,actor_id,state,
              policy_version,request_hash)
            VALUES(:id,:org,:dataset,:lead,:actor,'planning',:policy,:hash)
        """),
            {
                "id": workflow,
                "org": principal.organization_id,
                "dataset": dataset,
                "lead": lead,
                "actor": principal.actor_id,
                "policy": POLICY_VERSION,
                "hash": digest({"query": query, "dataset": str(dataset), "lead": str(lead)}),
            },
        )
        record(
            connection,
            principal,
            "workflow_started",
            "planning",
            {"query_hash": digest(query)},
            workflow,
        )
    if on_started:
        on_started(workflow)
    plan = None
    for attempt in (1, 2):
        if _monotonic() - started >= deadline_seconds:
            return _terminal(engine, scope, workflow, "failed", "deadline_exceeded")
        try:
            raw = (
                planner.plan(tool_schemas(), attempt)
                if planner
                else json.dumps(
                    {
                        "calls": [
                            {"name": "get_lead_context", "arguments": {}},
                            {"name": "get_priority_explanation", "arguments": {}},
                            {"name": "search_approved_knowledge", "arguments": {"query": query}},
                            {
                                "name": "get_metric",
                                "arguments": {
                                    "metric": "inbound_leads",
                                    "start": (
                                        context["observed_at"] - timedelta(days=90)
                                    ).isoformat(),
                                    "end": context["observed_at"].isoformat(),
                                },
                            },
                        ]
                    }
                )
            )
            if len(raw.encode()) > 8192:
                raise ValueError("plan_size_limit")
            plan = Plan.model_validate_json(raw)
            outcome = "validated"
        except Exception:
            outcome = "invalid_plan"
        with engine.begin() as connection:
            record(
                connection, principal, "planner_attempt", outcome, {"attempt": attempt}, workflow
            )
            connection.execute(
                text("UPDATE bounded_workflows SET planner_attempts=:n WHERE id=:id"),
                {"n": attempt, "id": workflow},
            )
        if plan is not None:
            break
    if plan is None:
        return _terminal(engine, scope, workflow, "failed", "planner_retry_limit")
    seen: set[str] = set()
    for index, call in enumerate(plan.calls, 1):
        if _monotonic() - started >= deadline_seconds:
            return _terminal(engine, scope, workflow, "failed", "deadline_exceeded")
        failure = None
        with engine.begin() as connection:
            record(
                connection,
                principal,
                "tool_requested",
                "reading",
                {"name": call.name, "arguments_hash": digest(call.arguments)},
                workflow,
            )
            connection.execute(
                text("UPDATE bounded_workflows SET state='reading',tool_calls=:n WHERE id=:id"),
                {"n": index, "id": workflow},
            )
            fingerprint = digest(call.model_dump())
            try:
                if fingerprint in seen:
                    raise PermissionError("repeated_tool_call")
                seen.add(fingerprint)
                # DB errors/timeouts roll back the read savepoint, retaining the denial audit.
                with connection.begin_nested():
                    connection.execute(text("SET LOCAL statement_timeout='1500ms'"))
                    result = dispatch(connection, scope, call, evidence_at)
                record(connection, principal, "tool_result", "success", result, workflow)
            except Exception:
                failure = "tool_permission_schema_or_query_denied"
                record(
                    connection,
                    principal,
                    "tool_result",
                    failure,
                    {"name_hash": digest(call.name)},
                    workflow,
                )
        if failure:
            return _terminal(engine, scope, workflow, "failed", failure)
    remaining = deadline_seconds - (_monotonic() - started)
    if remaining <= 0:
        return _terminal(engine, scope, workflow, "failed", "deadline_exceeded")
    with engine.begin() as connection:
        record(connection, principal, "proposal_requested", "recommending", {}, workflow)
        connection.execute(
            text("UPDATE bounded_workflows SET state='recommending' WHERE id=:id"), {"id": workflow}
        )
    try:
        result = recommend(
            engine,
            principal,
            dataset,
            lead,
            query,
            provider=provider,
            price=price,
            deadline_seconds=remaining,
            now=evidence_at,
            quality_profile=quality_profile,
        )
    except Exception:
        return _terminal(engine, scope, workflow, "failed", "proposal_generation_failed")
    return _terminal(
        engine, scope, workflow, result["state"], result["failure_code"], UUID(result["run_id"])
    )
