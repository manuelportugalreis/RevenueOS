# Data foundation: scope, inspection, and acceptance

Date: 2026-10-16. The owner authorized implementation of the approved data foundation. AI, scoring, UI, CRM APIs, and external messaging remain out of scope.

## Inspection before implementation

Only the nine planning documents and their two review exports existed. No application, package metadata, migrations, tests, Git repository, or applicable ancestor `AGENTS.md` was present. Python 3.12 is available. Docker, PostgreSQL, and `psql` were not on PATH; no database URL was supplied. Python initially had only pip. Dependencies will be isolated in `.venv`; downloaded PostgreSQL binaries and a disposable test cluster will live under ignored `work/`, without a Windows service or changes to existing databases.

## Incremental delivery and acceptance criteria

1. **Schema and migrations:** PostgreSQL-native UUIDs, timezone-aware timestamps, fixed-precision money, explicit enums/checks, organization/dataset-consistent foreign keys, and indexed joins. Upgrade an empty database, downgrade to base, and upgrade again. No application `create_all` substitute for migrations.
2. **Synthetic fixtures:** byte-reproducible CSV bundles with explicit synthetic provenance, stable IDs, reserved `.example` identities, a fixed as-of time, a small hand-computable fixture, and a larger seeded dataset. Include missing optional values, suppression/deletion, duplicates, malformed fields, orphan references, automated acknowledgments, recent/censored leads, multiple currencies, and chronological boundaries.
3. **Preview and validation:** typed normalized rows, bounded strict UTF-8 CSV parsing, field-level redacted errors, explicit mappings, duplicate policy, referential validation, mode isolation, and no database mutations during preview. Required-schema/file errors reject the bundle; isolated row errors quarantine rows and dependent rows. Counts reconcile exactly.
4. **Commit and history:** explicit preview-hash confirmation, atomic dataset publication with persisted errors and lineage, database-backed idempotency under replay/concurrency, rejection of stale/conflicting source versions, sticky suppression/deletion, and immutable historical snapshots. Failure rolls back all writes.
5. **SQL analytics:** parameterized SQL over a pinned immutable dataset; inbound volume, first-human-response median/p90 and unresolved count, mature 30-day qualification, closed-period win rate, and open pipeline separated by currency. Return denominators, exclusions, freshness, mode, and version. Hand-calculated fixture assertions, empty-cohort behavior, and organization separation must pass.
6. **Quality and reproducibility:** locked dependencies, env template, Compose, CLI, CI with real PostgreSQL, unit/integration tests, lint/type checks, documented commands/design decisions, and an honest execution report. Skipped integration tests never count as database verification.

## Implementation decision: immutable full-export datasets

Use dataset-scoped CRM rows as the canonical history rather than mutable current tables plus separate JSON history tables. Each published dataset is a complete accepted export snapshot, with UUID identity stable across versions and composite `(organization_id, dataset_id, id)` keys. Latest-dataset views provide the current projection. This directly supports pinned analytics and simplifies audit/replay; it is a physical-schema refinement of the approved versioned data model. It uses more storage but avoids dual-write drift at the expected small pilot scale. A simpler alternative is mutable tables only, which cannot reproduce old metric results.

Each bundle covers one source and includes all seven required CSV files, even when empty. Missing rows mean absent from this export, **not** a deletion or a negative outcome. No historical coverage is inferred. A complete-observation flag on an outcome is an explicit source assertion, not something inferred merely from calendar age. Stale/conflicting records are quarantined; the preview reports them. Suppression/deletion tombstones survive later exports, including disappearance/reappearance. Source timestamps must not exceed the bundle's declared observation time. More complex incremental API merge semantics remain deferred.
