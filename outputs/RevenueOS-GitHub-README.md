# RevenueOS

**Revenue intelligence with evidence, bounded permissions and human review.**

RevenueOS is a synthetic, offline portfolio system for B2B SaaS inbound RevOps. It connects validated CRM snapshots, SQL business metrics, explainable priorities, approved sales knowledge and cited drafts in an authenticated executive dashboard. It is an engineering demonstration, not a client deployment.

![RevenueOS executive dashboard using synthetic data](docs/dashboard-preview.png)

[Architecture diagram](docs/22-architecture-current.md) · [Five-minute demo](docs/26-interview-demo.md)

## Observed results and limits

| Evidence | Result | Interpretation |
|---|---|---|
| Python/PostgreSQL regressions | **174 passed; zero failures/skips** | Data, migration, workflow, API, signed offline OIDC and comparison checks |
| Chromium end-to-end | **Two journeys passed** | Actual browser → API → PostgreSQL, including draft/citation/reviewer/logout/mobile/error behavior |
| Automated accessibility | Zero violations on three scanned views | Overview, approval inspection, mobile evaluation; not certification |
| Paired synthetic diagnostic | **85/100 vs 66/100 fixture task successes** | Bounded lexical/template vs title/template reference, not live LLM/human workflow accuracy |
| Recommendation quality gates | **Failed** | Nine false abstentions and six inappropriate completions across 100 authored tasks |
| Client time, conversion uplift, ROI | **Not measured** | No retrospective client dataset or pilot; no fabricated outcomes |

The diagnostic recorded 400 measured attempts plus eight warm-ups, two repetitions and 20 correlated case families. Paired success difference: +19 percentage points; descriptive family-bootstrap interval +3 to +36. Previously seen cases are disclosed; no new hidden holdout is claimed. Mean software latency was 202.0 ms versus 27.6 ms under shared-machine test load. Human preparation/review time was not measured. Both arms used templates with zero provider attempts; actual hosting/labor/invoices remain unknown.

Read the [technical evaluation](docs/23-comparison-report.md), [business case](docs/24-business-case.md), [engineering case study](docs/25-case-study.md), and [five-minute interview demo](docs/26-interview-demo.md). The [locked protocol](docs/21-comparison-acceptance.md) predates this run. Raw evidence and review copies are exported in `outputs/`.

## Implemented slice

- CSV preview, quarantine, explicit commit, replay protection and immutable synthetic CRM snapshots.
- PostgreSQL analytics with currency, interval, outcome-maturity and missingness definitions.
- Transparent attention points with component evidence; FIFO/newest/seeded-random diagnostics. Predictive training remains gated off for insufficient real/as-of evidence.
- Stewarded lexical retrieval, exact document/version/character citations, scope and revocation checks.
- Structured recommendations, quotation validation, abstention, bounded read tools, cost reservations and failure evidence.
- Dashboard for pipeline KPIs, explained lead queue, recommendations, exact-version review, evaluation failures and accounting.
- Google Workspace OIDC adapter with signed offline token/claim tests; loopback password login for synthetic demos. Opaque revocable DB sessions, Origin/CSRF checks and server-mapped organization/actor.
- Transactional redacted audit, immutable draft versions and explicit reviewer decisions. **No web send endpoint or external messaging connector.** Operator-only rehearsal records `delivered=false`.
- Readiness/liveness, redacted request IDs/status/timing, protected process counters, CI and container/TLS deployment configuration.

Live Google enrollment, hosted CI/container execution, real-model quality, production runtime-role/RLS/restore/retention/load validation and crash recovery remain outstanding. The optional live-provider adapter has fake-transport contract tests only. The owner has kept evaluations offline. Real data is blocked by the web service. Passing tests does not establish production readiness.

## Local dashboard

Prerequisites: Python 3.12+, Node 24 and PostgreSQL 18. Create a separate empty **synthetic** database. Set secrets through your shell/secret manager; Python does not auto-load `.env`. Windows commands are shown; use `.venv/bin/python` and `npm` on Linux/macOS.

```powershell
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.lock
./.venv/Scripts/python -m pip install --no-build-isolation --no-deps -e .
npm.cmd ci --prefix frontend --no-audit --no-fund
npm.cmd run build --prefix frontend
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/revenueos_web_demo'
# Set REVENUEOS_DEMO_PASSWORD securely, at least 16 characters; never use test passwords.
./.venv/Scripts/python scripts/serve_dashboard_demo.py
```

Open `http://127.0.0.1:8000`. Accounts `executive` and `reviewer` use your supplied password. The helper migrates and seeds the small hand-checkable golden CRM/corpus idempotently, binds loopback, requires synthetic data and assigns a synthetic reviewer persona. It is not a client-account enrollment tool.

Google hosting, environment mappings, monitoring/incident instructions and deployment limits: [operations guide](docs/19-dashboard-guide.md). See [current architecture](docs/22-architecture-current.md) and the [planning pack](docs/README.md) for design decisions and simpler alternatives.

## Reproduce verification

Only a disposable local database named `revenueos_test` may be reset. Migration tests deliberately remove/recreate the application schema. Never use customer data.

```powershell
$env:TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/revenueos_test'
$env:REVENUEOS_TEST_ALLOW_RESET='1'
./.venv/Scripts/python -m pytest --require-db --junitxml=outputs/portfolio-tests.xml
./.venv/Scripts/python -m ruff check src migrations tests
./.venv/Scripts/python -m ruff format --check src migrations tests
./.venv/Scripts/python -m mypy src
./.venv/Scripts/python -m pip check
```

Without DB configuration integration cases skip; `--require-db` prevents skipped database work being called verified. For browser tests, keep the separate demo server running and set its operator password in `REVENUEOS_DEMO_PASSWORD`:

```powershell
./frontend/node_modules/.bin/playwright.cmd install chromium
npm.cmd run test:e2e --prefix frontend
```

Browser decisions use synthetic personas and create no deliveries. CI uses actual PostgreSQL, but remote execution is not claimed. [Verification](docs/20-dashboard-verification.md) records measured results and corrections.

## Reproduce the comparison

Import the large seeded synthetic bundle and seed approved knowledge using the [data guide](docs/10-data-foundation-guide.md) and [intelligence guide](docs/13-intelligence-guide.md). Use its current organization/dataset UUID and a new output directory:

```powershell
./.venv/Scripts/python -m revenueos.comparison --organization ORG_UUID --dataset DATASET_UUID --output outputs/new-comparison-run
./.venv/Scripts/python scripts/export_portfolio.py
```

The exporter expects canonical completed comparison artifacts in `outputs/`. Keep new experiments separate; never overwrite a failed run to present success. Source hashes identify the uncommitted workspace snapshot; there is no released Git commit or remote deployment to cite.

The [business scenario inputs](data/evaluation/business-assumptions.json) are simulations with positive, neutral and downside cases; realized ROI remains null. The [empty pilot collection template](data/pilot/task-observations-template.csv) is a future contract, not client observations. A real pilot needs approved data, independently reviewed quality, measured human work and actual cost evidence.
