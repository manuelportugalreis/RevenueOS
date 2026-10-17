"""Strict CSV contracts shared by generation, preview, and persistence."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

Mode = Literal["synthetic", "real"]
Stage = Literal["discovery", "demo", "proposal", "won", "lost"]
Currency = Literal["USD", "EUR", "GBP", "CAD", "AUD"]
Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("*", mode="before")
    @classmethod
    def blank_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("NUL characters are not supported")
        return None if value == "" else value

    @field_validator("*", mode="after")
    @classmethod
    def utc(cls, value: Any) -> Any:
        return value.astimezone(UTC) if isinstance(value, datetime) else value


class Manifest(Contract):
    schema_version: Literal["crm_snapshot_v1"]
    mapping_version: Identifier
    organization_id: UUID
    organization_name: Annotated[str, Field(min_length=1, max_length=200)]
    data_mode: Mode
    source_system: Identifier
    observed_at: AwareDatetime
    reporting_timezone: str = "UTC"
    default_currency: Currency = "USD"
    column_mapping: dict[str, dict[str, str]] = Field(default_factory=dict)

    @field_validator("reporting_timezone")
    @classmethod
    def valid_zone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("invalid reporting timezone") from exc
        return value

    @field_validator("source_system", "mapping_version")
    @classmethod
    def short_identifier(cls, value: str) -> str:
        if len(value) > 64:
            raise ValueError("identifier too long")
        return value


class Row(Contract):
    data_mode: Mode


class VersionedRow(Row):
    external_id: Identifier
    source_updated_at: AwareDatetime


class Account(VersionedRow):
    name: Annotated[str, Field(min_length=1, max_length=200)]
    domain: Annotated[str | None, Field(max_length=253)]
    industry: Annotated[str | None, Field(max_length=100)]
    employee_band: Literal["1-10", "11-50", "51-200", "201-1000", "1000+"] | None


class Lead(VersionedRow):
    account_external_id: Identifier | None
    source: Literal["website", "demo_request", "webinar", "referral", "test", "internal"]
    status: Literal["new", "working", "qualified", "disqualified"]
    created_at: AwareDatetime
    do_not_contact: bool
    deleted_at: AwareDatetime | None
    name: Annotated[str | None, Field(max_length=200)]
    email: Annotated[str | None, Field(max_length=254)]
    lawful_use_status: Literal["approved", "unknown", "blocked"]

    @field_validator("do_not_contact", mode="before")
    @classmethod
    def boolean(cls, value: Any) -> bool:
        return parse_boolean(value)

    @field_validator("email")
    @classmethod
    def email_shape(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("invalid email shape")
        return value

    @model_validator(mode="after")
    def dates_and_synthetic(self) -> Lead:
        if self.source_updated_at < self.created_at:
            raise ValueError("update_before_creation")
        if self.deleted_at and not self.created_at <= self.deleted_at <= self.source_updated_at:
            raise ValueError("invalid_deletion_time")
        if self.data_mode == "synthetic" and self.email:
            if not self.email.rsplit("@", 1)[1].endswith((".example", ".invalid")):
                raise ValueError("synthetic_email_must_use_reserved_domain")
        return self


class Interaction(VersionedRow):
    lead_external_id: Identifier
    occurred_at: AwareDatetime
    direction: Literal["inbound", "outbound"]
    channel: Literal["email", "phone", "meeting", "web"]
    actor_type: Literal["human", "automation"]
    summary: Annotated[str | None, Field(max_length=2000)]

    @model_validator(mode="after")
    def chronology(self) -> Interaction:
        if self.source_updated_at < self.occurred_at:
            raise ValueError("update_before_event")
        return self


class Opportunity(VersionedRow):
    account_external_id: Identifier
    stage: Stage
    amount: Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False)]
    currency: Currency
    created_at: AwareDatetime
    closed_at: AwareDatetime | None

    @model_validator(mode="after")
    def chronology(self) -> Opportunity:
        if self.source_updated_at < self.created_at:
            raise ValueError("update_before_creation")
        if (self.stage in ("won", "lost")) != (self.closed_at is not None):
            raise ValueError("terminal_stage_requires_close_time")
        if self.closed_at and not self.created_at <= self.closed_at <= self.source_updated_at:
            raise ValueError("invalid_close_time")
        return self


class OpportunityLead(Row):
    opportunity_external_id: Identifier
    lead_external_id: Identifier


class StageEvent(VersionedRow):
    opportunity_external_id: Identifier
    from_stage: Stage | None
    to_stage: Stage
    effective_at: AwareDatetime

    @model_validator(mode="after")
    def chronology(self) -> StageEvent:
        if self.source_updated_at < self.effective_at:
            raise ValueError("update_before_event")
        return self


class Outcome(Row):
    lead_external_id: Identifier
    definition_version: Literal["qualified_30d_v1"]
    qualified_at: AwareDatetime | None
    observation_complete: bool
    observed_through: AwareDatetime

    @field_validator("observation_complete", mode="before")
    @classmethod
    def boolean(cls, value: Any) -> bool:
        return parse_boolean(value)

    @model_validator(mode="after")
    def chronology(self) -> Outcome:
        if self.qualified_at and self.qualified_at > self.observed_through:
            raise ValueError("qualification_after_observation")
        return self


def parse_boolean(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value == "true":
        return True
    if value == "false":
        return False
    raise ValueError("boolean must be true or false")


CONTRACTS: dict[str, type[Row]] = {
    "accounts": Account,
    "leads": Lead,
    "opportunities": Opportunity,
    "interactions": Interaction,
    "opportunity_leads": OpportunityLead,
    "opportunity_stage_events": StageEvent,
    "lead_outcomes": Outcome,
}
WINDOW = timedelta(days=30)
