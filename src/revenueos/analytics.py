"""SQL-backed analytics on a caller-selected immutable snapshot."""

from datetime import datetime
from importlib.resources import files
from typing import Any
from uuid import UUID

from sqlalchemy import Connection, text


def metrics(
    connection: Connection, organization_id: UUID, dataset_id: UUID, start: datetime, end: datetime
) -> dict[str, Any]:
    if start.tzinfo is None or end.tzinfo is None or start >= end:
        raise ValueError("interval requires timezone-aware start < end")
    dataset = (
        connection.execute(
            text(
                "SELECT d.*,b.bundle_hash,b.quarantined_count,b.accepted_count,b.duplicate_count "
                "FROM datasets d JOIN import_batches b ON b.id=d.import_batch_id "
                "WHERE d.organization_id=:org AND d.id=:dataset"
            ),
            {"org": organization_id, "dataset": dataset_id},
        )
        .mappings()
        .first()
    )
    if dataset is None:
        raise ValueError("dataset_not_found_in_organization")
    params = {
        "org": organization_id,
        "dataset": dataset_id,
        "start": start,
        "end": end,
        "as_of": dataset["observed_at"],
    }

    def query(name: str) -> list[dict[str, Any]]:
        sql = files("revenueos").joinpath(f"sql/{name}.sql").read_text(encoding="utf-8")
        return [dict(row) for row in connection.execute(text(sql), params).mappings()]

    leads = query("lead_metrics")[0]
    denominator = leads["qualification_denominator"]
    leads["qualification_rate"] = leads["qualified_30d"] / denominator if denominator else None
    opportunities = query("opportunity_metrics")[0]
    closed = opportunities["closed_denominator"]
    opportunities["win_rate"] = opportunities["won"] / closed if closed else None
    return {
        "metric_version": "revenue_metrics_v1",
        "dataset_id": str(dataset_id),
        "dataset_version": dataset["version"],
        "data_mode": dataset["data_mode"],
        "source_system": dataset["source_system"],
        "source_hash": dataset["bundle_hash"],
        "observed_at": dataset["observed_at"].isoformat(),
        "published_at": dataset["published_at"].isoformat(),
        "interval": {"start_inclusive": start.isoformat(), "end_exclusive": end.isoformat()},
        "freshness_note": "Snapshot as observed; no continuous CRM coverage is asserted.",
        "coverage_note": "No recorded response is unknown contact status, not proof of no contact.",
        "import_quality": {
            key: dataset[key] for key in ("accepted_count", "quarantined_count", "duplicate_count")
        },
        "leads": leads,
        "lead_sources": query("lead_sources"),
        "opportunities": opportunities,
        "open_pipeline_by_currency": query("pipeline"),
        "pipeline_scope": (
            "All open opportunities at snapshot observation time, independent of interval"
        ),
    }
