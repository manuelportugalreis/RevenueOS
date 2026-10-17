# Changelog

## v0.1.0 — Portfolio presentation release

First public release of the complete synthetic RevenueOS engineering demonstration.

- Validated CSV ingestion, immutable CRM snapshots, migrations and SQL analytics.
- Explainable rule-based priorities with batched reads and equal-score verification.
- Approved document retrieval, exact citations and structured offline recommendations.
- Bounded workflows, permission checks, redacted audit, immutable draft review and no external delivery endpoint.
- Executive dashboard, synthetic personas, Google Workspace adapter with offline OIDC tests, and a restricted database runtime role.
- Organization/document RLS, idempotency and interruption reconciliation.
- Four-arm reproducible diagnostics, cost accounting, retained failures and scripted business scenarios.
- Automated tests, CI, container configuration, operations documentation and interview walkthrough.

Recorded evidence: 207 Python/PostgreSQL tests and two Chromium journeys passed locally; eight runtime tests were additionally repeated after ACL hardening. The current authored diagnostic records 66/85/99/99 task successes out of 100. These are previously exposed synthetic tasks, not hidden-test model accuracy. One inappropriate completion remains. Local restore integrity and restricted native login checks passed.

Publication preparation corrected the Docker frontend data-copy path, updated the interview walkthrough and made fixture serialization preserve original CRLF bytes explicitly on every host. The first Linux CI run exposed that newline discrepancy (206 passing tests, one reproducibility failure); subsequent Actions runs retain its history. The GitHub Actions run for the published commit is the authority for hosted checks; historical reports describe their own recorded environments.

No live LLM, client dataset, pilot company, actual Workspace tenant or realized ROI is included. This release is ready to present as an engineering portfolio, not certified for production or customer deployment. Existing evidence archives preserve earlier snapshots and are explicitly historical.
