# Data foundation delivery and verification

Date: 2026-10-16 (America/Phoenix). Scope authorized by the owner's follow-up: database, synthetic CRM, CSV ingestion/validation, migrations, and SQL analytics. No AI, scoring, frontend, or CRM API features were implemented.

## Delivered

- Installable Python package and local synthetic-only operator CLI.
- Three reversible Alembic migrations: 13 application tables, two views, composite scope constraints, fixed-precision money, timezone-aware dates, indexed joins, dataset-mode checks, and append-only snapshot guards.
- Two checked-in synthetic bundles: a hand-computable error fixture and a deterministic 1,000-lead seed-42 CRM export. SHA256SUMS and regeneration tests verify fixture bytes.
- Bounded CSV validation with canonical/custom header mapping, typed rows, explicit mode, field errors without raw values, duplicate/conflict handling, dependent-row quarantine, chronology checks, and exact count reconciliation.
- Read-only preview, preview-hash confirmation, organization-serialized publication, atomic rollback, source-version checks, sticky suppression/deletion, and concurrent idempotent replay.
- SQL metrics for inbound lead/source counts, first human response, mature qualification, closed-period win rate, and open pipeline by currency. Metrics include lineage, denominator/exclusion, snapshot, and freshness metadata.
- Dependency version lock, env template, Compose configuration, PostgreSQL CI workflow, setup/operating documentation, and automated tests.
- Git repository initialized locally; files are uncommitted. No remote, push, or deployment was performed. Existing planning work was preserved; its README now records approval and implementation links.

## Observed verification

Environment: Windows, Python 3.12, isolated virtualenv, actual PostgreSQL 18.6 on a temporary loopback-only test cluster. SQLAlchemy 2.0.55, Alembic 1.20.0, psycopg 3.3.6, Pydantic 2.14.1, pytest 9.1.1. No SQLite substitution.

| Check | Observed result |
|---|---|
| Final `pytest --require-db` suite | **52 passed, 0 failed, 0 errors, 0 skipped; 23.71 seconds** |
| Ruff lint | Passed |
| Ruff format check | Passed; 17 Python files |
| Strict mypy on src | Passed; seven source files |
| pip check | Passed; no broken requirements |
| Editable package installation | Passed |
| Wheel build and SQL resource inspection | Passed; all four SQL query files included |
| Migration round-trip | Passed against PostgreSQL: downgrade to base leaves only alembic_version, upgrade recreates 13 tables and two views |
| Concurrent identical commit | Passed; same dataset, one publication and one replay |
| Injected mid-write failure | Passed; all tested batch/snapshot/error/domain/tombstone writes rolled back |
| Snapshot UPDATE/DELETE guards | Passed; database rejects accidental mutation |
| 1,000-lead import | Passed; all 1,000 leads imported, zero quarantined/duplicate rows in seeded clean bundle |
| CLI end-to-end and redacted failures | Passed; preview/confirmed commit/replay/analytics, bad confirmation, and malformed manifest without raw-value echo |
| Separate synthetic demo export | Executed; preview, replay, and SQL result JSON saved under outputs |

Tests cover aware-date normalization, malformed/missing fields, exact money boundaries, reserved synthetic domains, strict booleans, NUL handling, invalid timezone, row/file limits, header mapping, invalid UTF-8, orphan/invalid parent propagation, future source timestamps, incomplete outcomes, stale/conflicting source versions, disappearance/reappearance suppression, interval boundaries, empty denominators, cross-scope rejection, and historical metric stability. This is evidence for those scenarios, not exhaustive correctness or a production security certification.

The first full test run had 38 passing tests and two failures caused by incorrect fixture count expectations; direct source-row reconciliation established 35 total and 28 accepted, and the expectations were corrected. Additional database, CLI, and input-safety tests brought the final passing suite to 52. An early sandbox-only unit invocation had two temporary-directory errors; using workspace-local test temporary directories resolved that environment issue. Package tooling likewise used workspace-local temporary directories. No failing or skipped tests are hidden in the final report.

## Synthetic metric demonstration

Golden input: **35 rows = 28 accepted + six quarantined + one duplicate-skipped**. Accepted rows: two accounts, eight leads, four opportunities, six interactions, two opportunity links, one stage event, five outcomes. Quarantines are two conflicting account rows, one malformed-date lead, one invalid opportunity, one orphan interaction, and the invalid opportunity's dependent link.

For [2026-08-01, 2026-10-01) UTC:

| Metric | Synthetic observed SQL result |
|---|---|
| Eligible inbound leads | 6; one test/internal and one deleted lead excluded |
| Human response observations | 3; three have no recorded human response |
| Response median / p90 | 2 / 3.6 elapsed hours; automated acknowledgments excluded |
| Mature complete qualification | 1 / 3; one immature and two mature unknown/incomplete cases excluded |
| Closed-period wins | 1 / 2 |
| Snapshot open pipeline | EUR 4000.20 and USD 3000.10, kept separate |

These are synthetic fixture calculations, not business performance or ROI. Saved demo commit attempts may both show replayed=true because the final evidence refresh reused the already-created immutable dataset. Initial creation plus replay is separately covered by the automated tests.

## Design decisions and practical limits

Immutable dataset-scoped rows implement the planned history without dual-writing current CRM tables and JSON history. This consumes more storage but keeps every metric tied to an exact accepted snapshot. The simpler mutable-only alternative would lose historical reproducibility. SQLAlchemy Core and explicit SQL keep joins/metrics inspectable; a full ORM adds little to this import/reporting slice. A CLI provides a small verifiable boundary before FastAPI/UI work. The following implementation guide explains each key decision, its simpler alternative, the data contract, and all metric definitions.

One complete seven-file export from one source is supported per organization. Missing rows mean absent from that export; imports never infer deletion, complete interaction coverage, or failed qualification. Partial quarantine can reduce the accepted snapshot population, which is why quality counts accompany analytics. Stage-event history is preserved as supplied, not asserted complete. Currency conversion is not supported.

The temporary cluster used trust authentication only for local synthetic tests and was stopped after verification. No Windows service or existing database was changed. Production authentication, runtime roles/RLS, real-data provider review, erasure/retention, backup/restore, and deployment operations remain future gates. Snapshot triggers must have a controlled privileged erasure path before real personal data is admitted.

Docker Compose and GitHub Actions configuration were authored but **not executed**: Docker is unavailable here and no remote CI was run. Linux behavior, production-scale load, 100,000-interaction performance, API/dashboard latency, and operational recovery remain unverified. The dependency lock fixes versions but does not include artifact hashes; artifact-integrity hardening remains available before production.

## Next steps

1. Review the data dictionary, quarantine examples, and metric denominator definitions against the intended pilot business.
2. Add the deterministic FastAPI endpoints and dashboard in the next scoped increment; use these fixtures and pinned SQL contracts.
3. Implement the explainable rules baseline only when requested. Keep AI features deferred.
4. Execute supplied CI/Compose in their target environment and complete the security/operations gates before any real-data pilot.


---

# Data foundation implementation guide

## Scope and principal decisions

The owner's implementation instruction approved the prior architecture. This increment implements its deterministic data slice only. The code is a Python package with typed Pydantic contracts, SQLAlchemy Core connection/transaction management, hand-written PostgreSQL schema and SQL analytics, and Alembic migrations. FastAPI/UI work is deferred because a local operator CLI is enough to verify the data boundary.

| Decision | Reason | Simpler alternative and cost |
|---|---|---|
| PostgreSQL only | Tests the actual UUID, numeric, FK, timestamptz, percentile, locking, and trigger behavior used by the product | SQLite is easy locally but would leave important production semantics unverified |
| SQLAlchemy Core, no ORM | Explicit SQL is easy to inspect and parameterize for this reporting/import slice | Direct psycopg is slightly smaller; Core gives consistent transactions and migration ecosystem integration |
| Pydantic row contracts | Typed normalization, enums, lengths, aware dates, strict booleans and decimal checks shared with fixture headers | Hand-written dict checks have fewer dependencies but duplicate normalization rules |
| Immutable dataset-scoped CRM rows | Pins metric results; avoids dual writes to current tables plus separate history; stable entity UUIDs across snapshots | Mutable CRM tables save storage but lose reproducibility; later incremental sync may justify current projections plus history |
| Full seven-file export bundle | One atomic boundary for references; no ordering assumptions across separately uploaded files | A single leads CSV is easier but cannot validate the full CRM model |
| Explicit preview hash | Binds approval to file bytes, accepted rows, quarantines, and database version | One-step import is simpler but silently accepts data loss from quarantine |
| Organization lock and DB uniqueness | Serializes source history/version allocation and concurrent replay | Hash lookup alone races under concurrent commits |
| Reserved domains and fixed seeded generator | Repeatable demos without invented real customer identities | Static CSV is simpler but cannot create varied workloads |
| SQL views plus parameterized metric queries | Inspectable definitions without cache-refresh complexity | Python aggregates are easy to prototype but separate metric semantics from the database |
| Source snapshots and explicit outcome coverage | Prevents treating overwritten current state as history or unknown follow-up as failure | Age-only labels are simpler but can fabricate negative outcomes |
| Sticky tombstones | Suppression/deletion survives exports that omit and later reintroduce a lead | Trusting each export is simpler but can reactivate suppressed contacts |
| Five explicitly supported currencies | Blocks accidental cross-currency totals without an unmaintained full currency catalog | USD only is smaller; conversion/FX valuation remains deferred |

Supporting references: [SQLAlchemy composite constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html), [Alembic migration workflow](https://alembic.sqlalchemy.org/en/latest/tutorial.html), and [PostgreSQL aggregate/percentile semantics](https://www.postgresql.org/docs/current/functions-aggregate.html). These explain library behavior, not RevenueOS measured quality.

## Schema and lineage

Three migrations create 13 application tables and two views. `0001` creates organizations, import batches/errors, datasets, accounts, leads, restricted lead_private, interactions, opportunities, opportunity_leads, opportunity_stage_events, lead_outcomes, and suppression_tombstones. `0002` adds current_datasets and lead_response_facts_v1. `0003` adds dataset-mode consistency and UPDATE/DELETE rejection triggers on published snapshot tables. Upgrade/downgrade are explicit; application startup does not silently create tables.

Every CRM key includes organization and dataset. UUIDv5 entity IDs derive from organization/source/entity/external ID; IDs persist across snapshots and never merge people by email. A dataset is one complete **accepted** export, not guaranteed complete business truth. Partial ingestion publishes only valid rows and visible error counts; missing or quarantined parents quarantine dependent rows. Snapshot storage replaces the separate `lead_versions`/`opportunity_versions` tables proposed in the logical plan. `current_datasets` selects the newest published version; all analytics require an explicit dataset UUID.

The row hash records normalized **source** content before sticky tombstone policy is applied. This distinction permits the same source version to reappear with its original source values while suppression remains effective. Source-update timestamps older than any previously accepted version are quarantined. Equal timestamps with changed source content are conflicts, not last-write-wins updates. A later dataset must have a strictly greater observed time; byte-identical replay returns its original dataset even after newer datasets exist. One source per organization is enforced in this version to avoid an incomplete cross-source current view.

Published snapshots reject ordinary in-place UPDATE/DELETE. Administrators still control the database, can disable triggers, and can insert directly; this is an accidental-mutation guard, not tamper-proof or multi-tenant security. Privacy erasure will require an explicit privileged workflow before real-data admission, because ordinary snapshot deletion is intentionally blocked.

## CSV contract and data dictionary

Each directory requires `manifest.json` and these seven UTF-8 CSVs, including headers for empty files. A UTF-8 BOM is supported. All canonical columns must be present, optional **values** may be blank, and extra/duplicate headers fail the bundle. Detailed field types/enums/limits live in `src/revenueos/contracts.py`; CSV headers are generated from those contracts.

| File/table | Data meaning and important fields |
|---|---|
| accounts | external_id, source_updated_at, company name, optional domain/industry/employee band |
| leads | external_id, source_updated_at, optional account reference, inbound source/status, created_at, do_not_contact, deleted_at; name/email/lawful-use fields split into lead_private |
| opportunities | external_id, source_updated_at, required account reference, stage, exact amount/currency, creation/close times |
| interactions | external_id, source_updated_at, lead reference, occurred_at, direction/channel, human vs automation, optional summary |
| opportunity_leads | explicit opportunity/lead pair; referenced records must share an account |
| opportunity_stage_events | stable source event ID, source_updated_at, opportunity reference, optional from_stage, to_stage, effective_at |
| lead_outcomes | lead reference, fixed qualified_30d_v1 definition, optional qualified_at, observation_complete, observed_through |

Every CSV row has `data_mode`; mixed synthetic/real mode rejects the entire bundle. The manifest declares schema/mapping versions, source, organization, data mode, observation time, timezone, and default currency. All timestamps must contain an offset, normalize to UTC, and cannot exceed observed_at. Reporting timezone must resolve through the timezone database. Only explicit `true`/`false` booleans are accepted. Money is finite, nonnegative, at most two fractional digits and twelve integer digits. Scientific notation with an exact representable value is normalized by Decimal. No binary floating-point money arithmetic is used.

Mappings use canonical-to-source header names, for example `"column_mapping": {"leads": {"external_id": "LeadID"}}`. Mapping targets must be unique. Advance mapping_version when changing mapping semantics; mapping bytes are included in the bundle hash. Unknown status/stage values require upstream mapping to approved enums; they are not guessed.

## Validation and publication

Preview only reads files and SELECTs database state; organization initialization is a separate explicit command. File/manifest/header/encoding errors reject the bundle; field and relationship errors quarantine individual logical CSV records. Error reports store entity, logical record number (header is row 1), field name, and error code, without raw values. Multiline CSV fields mean this record number is not always a physical source line number.

Limits: 10 MiB per CSV, 10,000 data records per CSV, 64 KiB manifest, field-specific lengths, and the CSV parser's field-size guard. All seven bounded files are read to bind preview to exact bytes. V1 is deliberately a bounded batch importer, not a streaming service for arbitrarily large exports. Exact normalized duplicates keep the first and count subsequent duplicates; conflicting valid duplicates quarantine all competing records. Reconciliation is total input = accepted + quarantined + duplicate-skipped.

For explicit commit, copy preview_hash into `commit --confirm`. The transaction locks the organization, rereads files, checks the locked database version, recomputes preview, and either rejects stale approval or inserts batch/error/snapshot data atomically. If bytes, manifest, or relevant state change, preview again. Failed writes roll back everything. Commit replay returns the original dataset ID/version and does not duplicate domain records. The preview can change on replay because database history has advanced; the original confirmed hash remains valid only for those exact already-committed bytes.

Suppression/deletion remains sticky across snapshots; ordinary source imports cannot lift it. No deletion is inferred from absence. The code does not contact an external system. Stage events preserve supplied evidence; they do not assert a complete stage chain or synthesize missing transitions.

## SQL metric contracts

Use timezone-aware `[start, end)` intervals. Cohort dates apply to lead creation; opportunity win rate uses close date. Dataset observation time is the as-of boundary. Inbound-only CRM exports are assumed; source is a controlled inbound acquisition channel. Test/internal and deleted leads are excluded with separate counts; disqualified and suppressed leads remain in reporting denominators to avoid inflating conversion by removing unsuccessful or uncontactable leads.

- Inbound volume counts distinct lead IDs in the accepted snapshot, with source breakdown.
- First response is earliest recorded **human outbound** interaction after creation. Automated acknowledgment never counts. Median/p90 are SQL continuous percentiles in elapsed hours, only among observed responses. No-recorded-response means unknown contact status, not proven failure; no business-hours timing is claimed.
- Qualification uses only calendar-mature 30-day leads whose source explicitly asserts observation_complete and coverage through creation + 30 days. Qualified_at must be within that window, inclusive at day 30. Report immature and mature-but-missing/incomplete separately. Status alone cannot imply a dated qualification.
- Win rate is won / (won + lost) closed in the interval. No opportunities means a null rate, not 0%.
- Open pipeline sums open opportunities at the snapshot observation time, grouped by currency and independent of the selected period. It is not revenue and cannot be summed across currencies. The output states this distinct scope.

Responses include metric version, dataset/source versions, hash, data mode, observed/published timestamps, interval, exclusions/denominators, and import quality. Money serializes as decimal strings in CLI JSON to preserve exactness. No historic as-of is reconstructed from a later export.

## Reproducible setup and verification

See the root README for commands. Requirements.lock pins the installed direct/transitive tools for the tested Python 3.12 environment; it is a version lock, not a cryptographic supply-chain lock. Use `pip install -r requirements.lock`, then install this package with `--no-build-isolation --no-deps -e .` so pyproject ranges do not upgrade locked packages. Linux CI uses the same version lock but must be observed separately before claiming cross-platform verification. SQL package resources are included in wheels; migrations are repository resources and deployments must include the repository's migration directory.

The local verification cluster is an ignored, temporary PostgreSQL runtime under work/, listening only on 127.0.0.1:55432. It uses trust authentication solely for synthetic disposable testing; it is not the Compose deployment's security configuration. No system PostgreSQL service was installed. Tests require an explicit local database named revenueos_test and reset consent. Run unit-only checks with `pytest -m 'not integration'`; run complete checks with `pytest --require-db`.

## Remaining limits and next work

No RLS/production role setup, authentication service, backup/restore/erasure workflow, real-data admission, CRM sync, UI, lead scoring, RAG, LLM, or message delivery is included. DB schema constraints and query scoping do not establish tenant security. Source completeness and qualification truth are source assertions, not independently verified facts. Performance at 10,000 leads/100,000 interactions, API latency, deployment recovery, Docker execution, and hosted CI require separate verification. Snapshot storage grows with each export; profile before incremental sync or archival changes.

Next: review metric definitions and sample errors; then implement the deterministic API/dashboard slice and rules baseline in a separately authorized increment. Preserve the no-AI constraint until the owner requests AI work.
