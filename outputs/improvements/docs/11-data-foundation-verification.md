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
