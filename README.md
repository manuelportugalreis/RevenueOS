# RevenueOS

**Revenue intelligence with evidence, bounded permissions and human review.**

[![Offline checks](https://github.com/manuelportugalreis/RevenueOS/actions/workflows/data-foundation.yml/badge.svg)](https://github.com/manuelportugalreis/RevenueOS/actions/workflows/data-foundation.yml)

RevenueOS is a synthetic, offline portfolio system for B2B SaaS inbound RevOps. It connects validated CRM snapshots, SQL business metrics, explainable priorities, approved sales knowledge and cited drafts in an authenticated executive dashboard. It is an engineering demonstration, not a client deployment.

**[Explore the public interactive replay](https://manuelportugalreis.github.io/RevenueOS/)** — no installation or password. It uses recorded synthetic API results and browser-local simulated decisions; it does not host the authenticated backend or call a model. [Demo and free-model experiment guide](docs/32-public-demo-and-free-evaluation-guide.md).

**New prospective diagnostic:** the unchanged focused template passed **17/24 newly authored tasks**, with six inappropriate completions and one false abstention. This harder set was not used to tune the policy. Actual LLM comparison is pending a configured free-tier credential; independent human review remains unperformed. Previous 99/100 results below describe the earlier exposed fixture set, not these new questions.

![RevenueOS executive dashboard using synthetic data](docs/dashboard-preview.png)

[Architecture diagram](docs/22-architecture-current.md) · [Five-minute demo](docs/26-interview-demo.md)

## Observed results and limits

| Evidence | Result | Interpretation |
|---|---|---|
| v0.1.0 Python/PostgreSQL regressions | **207 passed; zero failures/skips** | Historical release; current hosted checks are linked in the badge above |
| Chromium end-to-end | **Two journeys passed** | Actual browser → API → restricted PostgreSQL login, human approval, idempotency and mobile/error behavior |
| Automated accessibility | Zero violations on three scanned views | Not certification |
| Four-arm synthetic diagnostic | **66 / 85 / 99 / 99 successes out of 100 authored tasks** | Title, legacy lexical, focused direct, focused bounded; templates, previously exposed cases |
| Remaining quality error | **One inappropriate completion** | Independent human review remains unavailable; no general accuracy claim |
| Ranking | **4 versus 3,001 client SQL statements for 1,000 synthetic leads** | Equal score explanations; local three-sample comparison |
| Recovery / restore | Native role/RLS, idempotency and isolated restore exercised | No cloud/password/TLS/production recovery guarantee |
| Client time, conversion uplift, ROI | **Not measured** | Everything is fictitious; no pilot company or participants |

The final diagnostic recorded 800 measured attempts plus 16 warm-ups across four arms and two repetitions. Focused direct versus legacy lexical: +14 percentage points, descriptive family-bootstrap interval +5 to +25; the previously exposed test subset interval includes no improvement. Focused direct and bounded had equal task quality; mean software times were 33.7 and 203.6 ms respectively. Tools add permissions/audit, not demonstrated semantic benefit. All arms used templates with zero provider attempts; actual hosting/labor/invoices remain unknown.

Read the [current executed report](docs/29-improvements-verification.md), [design and reproduction guide](docs/28-improvements-guide.md) and [current evidence index](outputs/improvements/RevenueOS-Improvements-Index.md). The original [85/100 versus 66/100 report](docs/23-comparison-report.md) and root portfolio exports remain historical. No fresh hidden holdout, independent human labels, real model quality or client outcomes are claimed.

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

Local native runtime-role/RLS, isolated restore, idempotency and crash reconciliation are now tested. Live Google enrollment, hosted CI/container execution, real-model quality, production retention, encrypted/off-site recovery and sustained load remain outstanding. The optional live-provider adapter has fake-transport contract tests only. Historical evaluations were offline; the free-tier experiment now requires a configured key and explicit no-billing attestation. Real data is blocked by the web service. Passing tests does not establish production readiness.

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

Open `http://127.0.0.1:8000`. Accounts `executive` and `reviewer` use your supplied password. The helper migrates and seeds the small hand-checkable golden CRM/corpus idempotently, binds loopback, requires synthetic data and assigns a synthetic reviewer persona. For the tested restricted configuration, separately provision the runtime capability/login and set `REVENUEOS_RUNTIME_DATABASE_URL`; see the current design guide. Without it the local helper uses the administrator connection and must not be treated as a restricted deployment. It is not a client-account enrollment tool.

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

The commands above reproduce the historical two-arm comparison. For the current four-arm experiment, use `--variant ablation --split all` and a new output directory; see the [current reproduction guide](docs/28-improvements-guide.md). `export_portfolio.py` is the historical exporter; `export_improvements.py` packages the current preserved artifacts. Keep new experiments separate; never overwrite a failed run to present success. Historical source hashes identify the exact prepublication workspace snapshot. Git tags identify published source; no hosted application deployment is implied.

The [business scenario inputs](data/evaluation/business-assumptions.json) are simulations with positive, neutral and downside cases; realized ROI remains null. The [empty pilot collection template](data/pilot/task-observations-template.csv) is a future contract, not client observations. A real pilot needs approved data, independently reviewed quality, measured human work and actual cost evidence.

## Presentation and release

Start with the [five-minute demonstration](docs/26-interview-demo.md), [architecture](docs/22-architecture-current.md), [case study](docs/30-presentation-case-study.md), and [measured evidence](docs/29-improvements-verification.md). The repository includes complete source, migrations, reproducible synthetic fixtures, tests, operations instructions and preserved evaluation artifacts. [Release notes](CHANGELOG.md) distinguish implemented behavior from unverified production capabilities. [Security reporting](SECURITY.md) explains how to report a concern without posting credentials or records publicly.

The published portfolio is an offline synthetic demonstration. Running it does not require a model API key. Live model evaluation, an actual Google Workspace tenant and a business pilot remain future validation work.
