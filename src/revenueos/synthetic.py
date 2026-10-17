"""Seeded, explicitly synthetic CRM bundles. No network or real contact identities."""

from __future__ import annotations

import csv
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from revenueos.contracts import CONTRACTS

SYNTHETIC_ORG = UUID("11111111-1111-4111-8111-111111111111")
AS_OF = datetime(2026, 10, 1, tzinfo=UTC)


def manifest(org: UUID = SYNTHETIC_ORG) -> dict[str, Any]:
    return {
        "schema_version": "crm_snapshot_v1",
        "mapping_version": "canonical_v1",
        "organization_id": str(org),
        "organization_name": "SYNTHETIC RevenueOS Demo",
        "data_mode": "synthetic",
        "source_system": "synthetic_crm",
        "observed_at": AS_OF.isoformat(),
        "reporting_timezone": "UTC",
        "default_currency": "USD",
        "column_mapping": {},
    }


def write_bundle(
    path: Path, metadata: dict[str, Any], rows: dict[str, list[dict[str, Any]]]
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "manifest.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    for entity, contract in CONTRACTS.items():
        with (path / f"{entity}.csv").open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=list(contract.model_fields), lineterminator="\n"
            )
            writer.writeheader()
            for row in rows.get(entity, []):
                writer.writerow(
                    {
                        key: ("true" if value is True else "false" if value is False else value)
                        for key, value in row.items()
                    }
                )


def golden_rows() -> dict[str, list[dict[str, Any]]]:
    """Small fixture with independently hand-computed analytics; plus quarantined edges."""
    mode = {"data_mode": "synthetic"}
    version = {**mode, "source_updated_at": "2026-09-30T00:00:00Z"}
    rows: dict[str, list[dict[str, Any]]] = {name: [] for name in CONTRACTS}
    rows["accounts"] = [
        {
            **version,
            "external_id": "A1",
            "name": "SYNTHETIC Example One",
            "domain": "one.example",
            "industry": "Software",
            "employee_band": "11-50",
        },
        {
            **version,
            "external_id": "A2",
            "name": "SYNTHETIC Example Two",
            "domain": "two.example",
            "industry": "",
            "employee_band": "",
        },
    ]
    for index in range(1, 9):
        rows["leads"].append(
            {
                **version,
                "external_id": f"L{index}",
                "account_external_id": "A1",
                "source": "test" if index == 6 else "website",
                "status": "qualified" if index == 1 else "new",
                "created_at": "2026-09-20T00:00:00Z" if index == 4 else "2026-08-01T00:00:00Z",
                "do_not_contact": index == 7,
                "deleted_at": "2026-09-01T00:00:00Z" if index == 8 else "",
                "name": f"SYNTHETIC Person {index}",
                "email": f"lead{index}@one.example",
                "lawful_use_status": "unknown" if index == 5 else "approved",
            }
        )
    for external, lead, occurred, actor in (
        ("I1", "L1", "2026-08-01T00:01:00Z", "automation"),
        ("I2", "L1", "2026-08-01T02:00:00Z", "human"),
        ("I3", "L1", "2026-08-01T03:00:00Z", "human"),
        ("I4", "L2", "2026-08-01T04:00:00Z", "human"),
        ("I5", "L4", "2026-09-20T01:00:00Z", "human"),
        ("I6", "L3", "2026-08-01T00:01:00Z", "automation"),
        ("I_BAD", "NO_LEAD", "2026-08-01T01:00:00Z", "human"),
    ):
        rows["interactions"].append(
            {
                **version,
                "external_id": external,
                "lead_external_id": lead,
                "occurred_at": occurred,
                "direction": "outbound",
                "channel": "email",
                "actor_type": actor,
                "summary": "SYNTHETIC interaction",
            }
        )
    for external, stage, amount, currency, closed in (
        ("O1", "won", "1000.00", "USD", "2026-09-10T00:00:00Z"),
        ("O2", "lost", "2000.00", "USD", "2026-09-15T00:00:00Z"),
        ("O3", "proposal", "3000.10", "USD", ""),
        ("O4", "demo", "4000.20", "EUR", ""),
        ("O_BAD", "won", "-1", "USD", ""),
    ):
        rows["opportunities"].append(
            {
                **version,
                "external_id": external,
                "account_external_id": "A1",
                "stage": stage,
                "amount": amount,
                "currency": currency,
                "created_at": "2026-08-02T00:00:00Z",
                "closed_at": closed,
            }
        )
    rows["opportunity_leads"] = [
        {**mode, "opportunity_external_id": "O1", "lead_external_id": "L1"},
        {**mode, "opportunity_external_id": "O3", "lead_external_id": "L1"},
        {**mode, "opportunity_external_id": "O_BAD", "lead_external_id": "L2"},
    ]
    rows["opportunity_stage_events"] = [
        {
            **version,
            "external_id": "E1",
            "opportunity_external_id": "O1",
            "from_stage": "proposal",
            "to_stage": "won",
            "effective_at": "2026-09-10T00:00:00Z",
        }
    ]
    for index in (1, 2, 3, 4, 7):
        rows["lead_outcomes"].append(
            {
                **mode,
                "lead_external_id": f"L{index}",
                "definition_version": "qualified_30d_v1",
                "qualified_at": "2026-08-15T00:00:00Z" if index == 1 else "",
                "observation_complete": index in (1, 2, 7),
                "observed_through": "2026-09-30T00:00:00Z",
            }
        )
    # One exact repeated source record, one malformed timestamp, one ambiguous source ID.
    rows["leads"].append(dict(rows["leads"][0]))
    bad = {**rows["leads"][0], "external_id": "L_BAD", "created_at": "not-a-date"}
    rows["leads"].append(bad)
    rows["accounts"].extend(
        [
            {**rows["accounts"][0], "external_id": "A_CONFLICT", "name": "SYNTHETIC Conflict 1"},
            {**rows["accounts"][0], "external_id": "A_CONFLICT", "name": "SYNTHETIC Conflict 2"},
        ]
    )
    return rows


def generate(path: Path, *, seed: int = 42, leads: int = 1000, golden: bool = False) -> None:
    if golden:
        write_bundle(path, manifest(), golden_rows())
        return
    if not 1 <= leads <= 2000:
        raise ValueError("leads must be between 1 and 2000 (CSV interaction row budget)")
    rng = random.Random(seed)
    rows: dict[str, list[dict[str, Any]]] = {name: [] for name in CONTRACTS}
    version = {"data_mode": "synthetic", "source_updated_at": AS_OF.isoformat()}
    account_count = max(1, leads // 5)
    for index in range(account_count):
        rows["accounts"].append(
            {
                **version,
                "external_id": f"A{index}",
                "name": f"SYNTHETIC Software Company {index}",
                "domain": f"company{index}.example",
                "industry": rng.choice(["Software", "Services", ""]),
                "employee_band": rng.choice(["1-10", "11-50", "51-200", ""]),
            }
        )
    for index in range(leads):
        created = AS_OF - timedelta(days=rng.randint(1, 150), hours=rng.randint(0, 23))
        qualified = rng.random() < 0.18  # A simulator assumption, never model-performance evidence.
        account = f"A{index % account_count}"
        lead = f"L{index}"
        rows["leads"].append(
            {
                **version,
                "external_id": lead,
                "account_external_id": account,
                "source": rng.choice(["website", "demo_request", "webinar", "referral"]),
                "status": "qualified"
                if qualified
                else rng.choice(["new", "working", "disqualified"]),
                "created_at": created.isoformat(),
                "do_not_contact": index % 23 == 0,
                "deleted_at": "",
                "name": f"SYNTHETIC Contact {index}",
                "email": ""
                if index % 11 == 0
                else f"contact{index}@company{index % account_count}.example",
                "lawful_use_status": "unknown" if index % 13 == 0 else "approved",
            }
        )
        for activity in range(rng.randint(0, 4)):
            occurred = min(AS_OF, created + timedelta(hours=rng.randint(1, 72)))
            rows["interactions"].append(
                {
                    **version,
                    "external_id": f"I{index}-{activity}",
                    "lead_external_id": lead,
                    "occurred_at": occurred.isoformat(),
                    "direction": rng.choice(["inbound", "outbound"]),
                    "channel": "email",
                    "actor_type": "automation" if activity == 0 else "human",
                    "summary": "SYNTHETIC sales interaction",
                }
            )
        mature = created + timedelta(days=30) <= AS_OF
        qualified_at = min(AS_OF, created + timedelta(days=10)) if qualified else None
        if index % 17 != 0:
            rows["lead_outcomes"].append(
                {
                    "data_mode": "synthetic",
                    "lead_external_id": lead,
                    "definition_version": "qualified_30d_v1",
                    "qualified_at": qualified_at.isoformat() if qualified_at else "",
                    "observation_complete": mature and index % 19 != 0,
                    "observed_through": AS_OF.isoformat(),
                }
            )
        if index % 3 == 0:
            stage = rng.choice(["discovery", "demo", "proposal", "won", "lost"])
            opp = f"O{index}"
            rows["opportunities"].append(
                {
                    **version,
                    "external_id": opp,
                    "account_external_id": account,
                    "stage": stage,
                    "amount": f"{rng.randint(1, 100) * 100}.00",
                    "currency": rng.choice(["USD", "EUR"]),
                    "created_at": created.isoformat(),
                    "closed_at": min(AS_OF, created + timedelta(days=20)).isoformat()
                    if stage in ("won", "lost")
                    else "",
                }
            )
            rows["opportunity_leads"].append(
                {"data_mode": "synthetic", "opportunity_external_id": opp, "lead_external_id": lead}
            )
    write_bundle(path, manifest(), rows)
