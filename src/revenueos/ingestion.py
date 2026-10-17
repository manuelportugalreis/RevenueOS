"""Read-only preview, deterministic quarantine, and atomic confirmed publication."""

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from pydantic import ValidationError
from sqlalchemy import Connection, Engine, text

from revenueos.contracts import CONTRACTS, WINDOW, Manifest

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 10_000


class BundleError(ValueError):
    """A fatal file/schema/scope error; no data can be committed."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def identity(org: UUID, source: str, entity: str, external_id: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"revenueos:{org}:{source}:{entity}:{external_id}")


@dataclass(frozen=True)
class Issue:
    entity: str
    row_number: int
    field: str
    code: str


@dataclass
class Preview:
    manifest: Manifest
    bundle_hash: str
    base_version: int
    rows: dict[str, list[dict[str, Any]]]
    issues: list[Issue] = field(default_factory=list)
    duplicates: int = 0
    total_rows: int = 0

    @property
    def accepted(self) -> int:
        return sum(len(rows) for rows in self.rows.values())

    @property
    def quarantined(self) -> int:
        return len({(issue.entity, issue.row_number) for issue in self.issues})

    @property
    def preview_hash(self) -> str:
        return digest(
            {
                "bundle": self.bundle_hash,
                "base_version": self.base_version,
                "rows": self.rows,
                "issues": [asdict(issue) for issue in self.issues],
                "duplicates": self.duplicates,
            }
        )

    def summary(self) -> dict[str, Any]:
        return {
            "organization_id": str(self.manifest.organization_id),
            "data_mode": self.manifest.data_mode,
            "bundle_hash": self.bundle_hash,
            "preview_hash": self.preview_hash,
            "base_version": self.base_version,
            "total_rows": self.total_rows,
            "accepted": self.accepted,
            "quarantined": self.quarantined,
            "duplicates": self.duplicates,
            "accepted_by_entity": {name: len(rows) for name, rows in self.rows.items()},
            "issues": [asdict(issue) for issue in self.issues],
        }


def _read(path: Path, limit: int = MAX_FILE_BYTES) -> bytes:
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise BundleError(f"file_too_large:{path.name}")
    return content


def _key(entity: str, row: dict[str, Any]) -> str:
    if entity == "opportunity_leads":
        return f"{row['opportunity_external_id']}:{row['lead_external_id']}"
    return str(row.get("external_id", row.get("lead_external_id")))


def preview_bundle(path: Path, connection: Connection) -> Preview:
    """Read files and SELECT database state only. Input values never appear in errors."""
    try:
        manifest_bytes = _read(path / "manifest.json", 64 * 1024)
        manifest = Manifest.model_validate_json(manifest_bytes)
        files = {name: _read(path / f"{name}.csv") for name in CONTRACTS}
    except (OSError, ValidationError, ValueError) as exc:
        raise BundleError("invalid_or_missing_bundle_file_or_manifest") from exc
    if set(manifest.column_mapping) - set(CONTRACTS):
        raise BundleError("unknown_mapping_entity")
    org = (
        connection.execute(
            text("SELECT * FROM organizations WHERE id=:id"), {"id": manifest.organization_id}
        )
        .mappings()
        .first()
    )
    if org is None or org["data_mode"] != manifest.data_mode:
        raise BundleError("unknown_organization_or_mode_mismatch")
    if (org["reporting_timezone"], org["default_currency"]) != (
        manifest.reporting_timezone,
        manifest.default_currency,
    ):
        raise BundleError("organization_reporting_configuration_mismatch")
    latest = (
        connection.execute(
            text(
                "SELECT version, observed_at, source_system FROM datasets "
                "WHERE organization_id=:org ORDER BY version DESC LIMIT 1"
            ),
            {"org": manifest.organization_id},
        )
        .mappings()
        .first()
    )
    bundle_hash = digest(
        {
            "manifest": manifest_bytes.hex(),
            "files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()},
        }
    )
    if latest and latest["source_system"] != manifest.source_system:
        raise BundleError("one_source_per_organization_in_v1")
    replay = connection.execute(
        text("SELECT 1 FROM import_batches WHERE organization_id=:org AND bundle_hash=:hash"),
        {"org": manifest.organization_id, "hash": bundle_hash},
    ).first()
    if latest and manifest.observed_at <= latest["observed_at"] and not replay:
        raise BundleError("non_increasing_snapshot_time")
    report = Preview(
        manifest, bundle_hash, latest["version"] if latest else 0, {name: [] for name in CONTRACTS}
    )
    for entity, model in CONTRACTS.items():
        mapping = manifest.column_mapping.get(entity, {})
        if set(mapping) - set(model.model_fields) or len(set(mapping.values())) != len(mapping):
            raise BundleError(f"invalid_column_mapping:{entity}")
        headers = {name: mapping.get(name, name) for name in model.model_fields}
        if len(set(headers.values())) != len(headers):
            raise BundleError(f"ambiguous_column_mapping:{entity}")
        try:
            stream = io.StringIO(files[entity].decode("utf-8-sig"), newline="")
            reader = csv.DictReader(stream, strict=True)
            if (
                reader.fieldnames is None
                or len(reader.fieldnames) != len(headers)
                or set(reader.fieldnames) != set(headers.values())
            ):
                raise BundleError(f"header_mismatch:{entity}")
            candidates: dict[str, list[dict[str, Any]]] = {}
            for number, raw in enumerate(reader, 2):
                report.total_rows += 1
                if number > MAX_ROWS + 1:
                    raise BundleError(f"too_many_rows:{entity}")
                if None in raw or any(value is None for value in raw.values()):
                    report.issues.append(Issue(entity, number, "row", "column_count"))
                    continue
                try:
                    normalized = model.model_validate({k: raw[v] for k, v in headers.items()})
                    row = normalized.model_dump(mode="json")
                    if row["data_mode"] != manifest.data_mode:
                        raise BundleError(f"mixed_data_modes:{entity}")
                    for value in normalized.model_dump().values():
                        if isinstance(value, datetime) and value > manifest.observed_at:
                            raise ValueError("future_timestamp")
                    if entity == "accounts" and manifest.data_mode == "synthetic":
                        domain = row["domain"]
                        if domain and not domain.endswith((".example", ".invalid")):
                            raise ValueError("synthetic_domain")
                    row["_row"] = number
                    candidates.setdefault(_key(entity, row), []).append(row)
                except ValidationError as exc:
                    for error in exc.errors():
                        field_name = ".".join(str(part) for part in error["loc"]) or "row"
                        report.issues.append(Issue(entity, number, field_name, error["type"]))
                except BundleError:
                    raise
                except ValueError:
                    report.issues.append(Issue(entity, number, "row", "chronology_or_domain"))
            for group in candidates.values():
                hashes = {digest({k: v for k, v in row.items() if k != "_row"}) for row in group}
                if len(hashes) > 1:
                    report.issues.extend(
                        Issue(entity, row["_row"], "external_id", "conflicting_duplicate")
                        for row in group
                    )
                else:
                    report.rows[entity].append(group[0])
                    report.duplicates += len(group) - 1
        except (UnicodeDecodeError, csv.Error) as exc:
            raise BundleError(f"invalid_csv_encoding_or_syntax:{entity}") from exc
    _validate_history(report, connection)
    _validate_relationships(report)
    if report.total_rows != report.accepted + report.quarantined + report.duplicates:
        raise AssertionError("unreconciled preview")
    return report


def _validate_history(report: Preview, connection: Connection) -> None:
    params = {"org": report.manifest.organization_id}
    for entity in (
        "accounts",
        "leads",
        "opportunities",
        "interactions",
        "opportunity_stage_events",
    ):
        # Entity names are hard-coded, never supplied by the CSV or model.
        history = connection.execute(
            text(
                "SELECT DISTINCT ON (r.external_id) "
                "r.external_id, r.source_updated_at, r.row_hash "
                f"FROM {entity} r JOIN datasets d ON d.id=r.dataset_id "
                "WHERE r.organization_id=:org ORDER BY r.external_id,d.version DESC"
            ),
            params,
        ).mappings()
        previous = {row["external_id"]: row for row in history}
        keep = []
        for row in report.rows[entity]:
            row_hash = digest({k: v for k, v in row.items() if not k.startswith("_")})
            old = previous.get(row["external_id"])
            updated = datetime.fromisoformat(row["source_updated_at"])
            code = None
            if old and updated < old["source_updated_at"]:
                code = "stale_source_version"
            elif old and updated == old["source_updated_at"] and row_hash != old["row_hash"]:
                code = "source_version_conflict"
            if code:
                report.issues.append(Issue(entity, row["_row"], "source_updated_at", code))
            else:
                row["_hash"] = row_hash
                keep.append(row)
        report.rows[entity] = keep
    tombstones = connection.execute(
        text(
            "SELECT * FROM suppression_tombstones WHERE organization_id=:org AND source_system=:src"
        ),
        {**params, "src": report.manifest.source_system},
    ).mappings()
    tombstone_by_id = {row["lead_id"]: row for row in tombstones}
    for row in report.rows["leads"]:
        lead_id = identity(
            report.manifest.organization_id,
            report.manifest.source_system,
            "leads",
            row["external_id"],
        )
        old = tombstone_by_id.get(lead_id)
        if old:
            row["do_not_contact"] = row["do_not_contact"] or old["do_not_contact"]
            if old["deleted_at"]:
                row["deleted_at"] = old["deleted_at"].isoformat()


def _validate_relationships(report: Preview) -> None:
    lookup: dict[str, dict[str, dict[str, Any]]] = {}
    refs = {
        "leads": [("account_external_id", "accounts")],
        "opportunities": [("account_external_id", "accounts")],
        "interactions": [("lead_external_id", "leads")],
        "opportunity_leads": [
            ("opportunity_external_id", "opportunities"),
            ("lead_external_id", "leads"),
        ],
        "opportunity_stage_events": [("opportunity_external_id", "opportunities")],
        "lead_outcomes": [("lead_external_id", "leads")],
    }
    for entity in CONTRACTS:
        keep = []
        for row in report.rows[entity]:
            code = None
            for column, parent in refs.get(entity, []):
                if row[column] and row[column] not in lookup[parent]:
                    code = "missing_or_quarantined_parent"
            if not code and entity in ("interactions", "lead_outcomes"):
                lead = lookup["leads"][row["lead_external_id"]]
                created = datetime.fromisoformat(lead["created_at"])
                if entity == "interactions":
                    if datetime.fromisoformat(row["occurred_at"]) < created:
                        code = "event_before_lead"
                else:
                    through = datetime.fromisoformat(row["observed_through"])
                    qualified = (
                        datetime.fromisoformat(row["qualified_at"]) if row["qualified_at"] else None
                    )
                    if through < created or (qualified and qualified < created):
                        code = "invalid_outcome_chronology"
                    elif row["observation_complete"] and through < created + WINDOW:
                        code = "incomplete_30_day_window"
            if not code and entity == "opportunity_leads":
                lead = lookup["leads"][row["lead_external_id"]]
                opp = lookup["opportunities"][row["opportunity_external_id"]]
                if lead["account_external_id"] != opp["account_external_id"]:
                    code = "account_link_mismatch"
            if not code and entity == "opportunity_stage_events":
                opp = lookup["opportunities"][row["opportunity_external_id"]]
                if datetime.fromisoformat(row["effective_at"]) < datetime.fromisoformat(
                    opp["created_at"]
                ):
                    code = "event_before_opportunity"
            if code:
                report.issues.append(Issue(entity, row["_row"], "row", code))
            else:
                keep.append(row)
        report.rows[entity] = keep
        lookup[entity] = {_key(entity, row): row for row in keep}


@dataclass(frozen=True)
class CommitResult:
    dataset_id: UUID
    version: int
    replayed: bool


def commit_bundle(path: Path, engine: Engine, confirmed_hash: str) -> CommitResult:
    """Re-preview under an organization lock; immutable inputs and state must still match."""
    try:
        manifest = Manifest.model_validate_json(_read(path / "manifest.json", 64 * 1024))
    except (OSError, ValueError) as exc:
        raise BundleError("invalid_manifest") from exc
    with engine.begin() as connection:
        connection.execute(
            text("SELECT id FROM organizations WHERE id=:id FOR UPDATE"),
            {"id": manifest.organization_id},
        )
        report = preview_bundle(path, connection)
        if report.manifest != manifest:
            raise BundleError("manifest_changed_during_commit")
        existing = (
            connection.execute(
                text(
                    "SELECT d.id,d.version,b.preview_hash FROM datasets d "
                    "JOIN import_batches b ON b.id=d.import_batch_id "
                    "WHERE b.organization_id=:org AND b.bundle_hash=:hash"
                ),
                {"org": manifest.organization_id, "hash": report.bundle_hash},
            )
            .mappings()
            .first()
        )
        if existing:
            # Original approval or a fresh preview of the same exact bundle is acceptable.
            if confirmed_hash not in (existing["preview_hash"], report.preview_hash):
                raise BundleError("preview_confirmation_mismatch")
            return CommitResult(existing["id"], existing["version"], True)
        if confirmed_hash != report.preview_hash:
            raise BundleError("preview_changed_repreview_required")
        batch_id, dataset_id = uuid4(), uuid4()
        scope = {"org": manifest.organization_id, "dataset": dataset_id}
        connection.execute(
            text(
                "INSERT INTO import_batches "
                "(id,organization_id,source_system,bundle_hash,preview_hash,"
                "schema_version,mapping_version,observed_at,"
                "accepted_count,quarantined_count,duplicate_count)"
                " VALUES (:id,:org,:source,:hash,:preview,:schema,:mapping,"
                ":observed,:accepted,:bad,:dup)"
            ),
            {
                "id": batch_id,
                "org": manifest.organization_id,
                "source": manifest.source_system,
                "hash": report.bundle_hash,
                "preview": confirmed_hash,
                "schema": manifest.schema_version,
                "mapping": manifest.mapping_version,
                "observed": manifest.observed_at,
                "accepted": report.accepted,
                "bad": report.quarantined,
                "dup": report.duplicates,
            },
        )
        connection.execute(
            text(
                "INSERT INTO datasets "
                "(id,organization_id,import_batch_id,version,data_mode,source_system,"
                "observed_at) VALUES (:dataset,:org,:batch,:version,:mode,:source,:observed)"
            ),
            {
                **scope,
                "batch": batch_id,
                "version": report.base_version + 1,
                "mode": manifest.data_mode,
                "source": manifest.source_system,
                "observed": manifest.observed_at,
            },
        )
        for issue in report.issues:
            connection.execute(
                text(
                    "INSERT INTO import_errors "
                    "(organization_id,import_batch_id,entity,row_number,field,code)"
                    " VALUES (:org,:batch,:entity,:row_number,:field,:code)"
                ),
                {"org": manifest.organization_id, "batch": batch_id, **asdict(issue)},
            )
        for entity, rows in report.rows.items():
            for row in rows:
                _insert_row(connection, manifest, dataset_id, entity, row)
        return CommitResult(dataset_id, report.base_version + 1, False)


def _insert(connection: Connection, table: str, values: dict[str, Any]) -> None:
    columns = ",".join(values)
    params = ",".join(f":{column}" for column in values)
    connection.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), values)


def _insert_row(
    connection: Connection, manifest: Manifest, dataset: UUID, entity: str, row: dict[str, Any]
) -> None:
    values = {k: v for k, v in row.items() if not k.startswith("_") and k != "data_mode"}
    values.update(organization_id=manifest.organization_id, dataset_id=dataset)
    for foreign_entity, column in (
        ("accounts", "account"),
        ("leads", "lead"),
        ("opportunities", "opportunity"),
    ):
        external = f"{column}_external_id"
        if external in values:
            value = values.pop(external)
            values[f"{column}_id"] = (
                identity(manifest.organization_id, manifest.source_system, foreign_entity, value)
                if value
                else None
            )
    if "external_id" in row:
        values["id"] = identity(
            manifest.organization_id, manifest.source_system, entity, row["external_id"]
        )
        values["row_hash"] = row["_hash"]
    if entity == "leads":
        private = {key: values.pop(key) for key in ("name", "email", "lawful_use_status")}
        _insert(connection, entity, values)
        _insert(
            connection,
            "lead_private",
            {
                "organization_id": manifest.organization_id,
                "dataset_id": dataset,
                "lead_id": values["id"],
                **private,
            },
        )
        if values["do_not_contact"] or values["deleted_at"]:
            connection.execute(
                text(
                    "INSERT INTO suppression_tombstones "
                    "(organization_id,source_system,lead_id,do_not_contact,deleted_at) "
                    "VALUES (:org,:src,:lead,:dnc,:deleted) "
                    "ON CONFLICT (organization_id,source_system,lead_id) DO UPDATE SET "
                    "do_not_contact=suppression_tombstones.do_not_contact "
                    "OR EXCLUDED.do_not_contact,"
                    "deleted_at=COALESCE(suppression_tombstones.deleted_at,EXCLUDED.deleted_at)"
                ),
                {
                    "org": manifest.organization_id,
                    "src": manifest.source_system,
                    "lead": values["id"],
                    "dnc": values["do_not_contact"],
                    "deleted": values["deleted_at"],
                },
            )
    else:
        _insert(connection, entity, values)
