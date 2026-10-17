# Changelog

## Public replay and prospective free-tier experiment

- Added a GitHub Pages interactive replay of actual recorded synthetic API responses, with no login, backend/model calls or persistent approvals. Desktop/mobile checks cover citation inspection, simulated decisions, visitor isolation, reset and unknown queries.
- Added 24 new project-authored questions after freezing the policy and corrected query-aware extractive prompt. The template scored 17/24, with six inappropriate completions and one false abstention; failures remain preserved.
- Corrected the provider payload to include the user's question and versioned the prompt. Added a one-attempt experiment option while preserving existing defaults.
- Added an opt-in Gemini free-tier adapter with no-billing attestation, call ceiling, pacing, quota-failure halt, strict local validation and no paid fallback. No actual model result is claimed without a successful live execution.
- Added a reproducible paired experiment and blank independent review/effort packets. Actual reviewers and measured human time remain unavailable.
- Kept v0.1.0 artifacts unchanged; the new diagnostic is not a hidden, independently labeled predictive holdout.

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
