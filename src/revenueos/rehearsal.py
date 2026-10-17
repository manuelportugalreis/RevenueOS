"""Paired fictitious pilot rehearsal; scripted inputs never become client outcomes."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    evidence_class: Literal["synthetic_scripted"]
    pair_id: str = Field(min_length=1, max_length=80)
    arm: Literal["baseline", "assisted"]
    prep_seconds: int | None = Field(ge=0, le=7200)
    review_seconds: int | None = Field(ge=0, le=7200)
    rework_seconds: int | None = Field(ge=0, le=7200)
    queue_seconds: int | None = Field(ge=0, le=7200)
    completed: bool
    acceptable: bool | None
    missing_reason: Literal["instrumentation_missing"] | None
    no_activity_attested: bool = False

    @property
    def effort(self) -> int | None:
        values = (self.prep_seconds, self.review_seconds, self.rework_seconds, self.queue_seconds)
        return None if any(v is None for v in values) else sum(v for v in values if v is not None)

    @model_validator(mode="after")
    def consistency(self) -> "Task":
        if (self.effort is None) != (self.missing_reason is not None):
            raise ValueError("missing_timing_requires_reason")
        if self.effort == 0 and not self.no_activity_attested:
            raise ValueError("zero_effort_requires_observation_attestation")
        return self


def analyze(tasks: list[Task]) -> dict[str, Any]:
    pairs: dict[str, dict[str, Task]] = {}
    for task in tasks:
        pair = pairs.setdefault(task.pair_id, {})
        if task.arm in pair:
            raise ValueError("duplicate_assignment")
        pair[task.arm] = task
    if not pairs or any(set(pair) != {"baseline", "assisted"} for pair in pairs.values()):
        raise ValueError("complete_pair_assignments_required")
    counts: dict[str, dict[str, Any]] = {}
    for arm in ("baseline", "assisted"):
        rows = [pair[arm] for pair in pairs.values()]
        known = [row.effort for row in rows if row.effort is not None]
        counts[arm] = {
            "assigned": len(rows),
            "timing_missing": len(rows) - len(known),
            "complete_case_mean_seconds": sum(known) / len(known) if known else None,
            "all_assigned_mean_seconds": sum(known) / len(rows)
            if len(known) == len(rows)
            else None,
            "completion_rate": sum(row.completed for row in rows) / len(rows),
            "acceptable_rate_all_assigned": sum(row.acceptable is True for row in rows) / len(rows),
            "quality_missing": sum(row.acceptable is None for row in rows),
        }
    b, a = counts["baseline"], counts["assisted"]
    reduction = (
        (b["all_assigned_mean_seconds"] - a["all_assigned_mean_seconds"])
        / b["all_assigned_mean_seconds"]
        if b["all_assigned_mean_seconds"] and a["all_assigned_mean_seconds"] is not None
        else None
    )
    if any(counts[arm]["timing_missing"] or counts[arm]["quality_missing"] for arm in counts):
        decision = "inconclusive_missingness"
    elif (
        a["completion_rate"] - b["completion_rate"] < -0.05
        or a["acceptable_rate_all_assigned"] - b["acceptable_rate_all_assigned"] < -0.05
    ):
        decision = "guardrail_failed"
    else:
        decision = (
            "scenario_meets_assumed_thresholds"
            if reduction is not None and reduction >= 0.2
            else "time_target_failed"
        )
    return {
        "evidence_class": "synthetic_scripted_rehearsal",
        "pairs": len(pairs),
        "arms": counts,
        "assumed_time_reduction": reduction,
        "scenario_decision": decision,
        "actual_pilot_status": "not_run_no_company",
        "real_participants": 0,
        "measured_human_time_saved": None,
        "realized_roi": None,
        "uncertainty": "Scripted inputs; no human observations or pilot confidence claim.",
    }
