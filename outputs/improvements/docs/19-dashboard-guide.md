# Authenticated executive dashboard and operations

The same-origin React/TypeScript dashboard is served by the existing Python modular monolith through FastAPI. No model API, external message transport, warehouse, Redis, or UI component framework is required. All web admission remains **synthetic only**, including Google-authenticated deployments. Do not use this increment as approval to process client data.

## User experience and data lineage

Overview shows acquisition-cohort counts, mature qualification numerator/denominator, closed-opportunity win rate, unknown recorded response status, open pipeline separately by currency, and import quality. UTC interval filters affect cohort/closed metrics; open pipeline is explicitly snapshot-wide. There are no invented historical trends or combined-currency totals. Snapshot ID/version/time and synthetic labels remain visible.

Lead priorities expose the top 20 eligible leads, exact score components, missingness warnings and the distinction between attention points and conversion probabilities. A bounded template workflow prepares a cited recommendation and draft for an eligible lead. Recommendations display only the requester's recent 20 runs; opening rechecks current authorization, expiry, suppression and evidence. Reviewers see the latest 20 organization action references, then must inspect through the existing source-scope checks before seeing recipient/message/evidence/version/hash. An explicit decision binds the inspected version/hash. No auto-send or reviewer-assignment web endpoint exists.

Evaluation displays a hashed summary of the **historical** frozen synthetic evaluation, its failed recommendation gate, and the organization attempt-cost ledger. The summary is a versioned artifact, not a live performance monitor. Missing artifacts show unavailable evidence. Unknown invoice/ROI/business impact remains unknown. Default templates create no provider attempts; this does not establish zero operating cost.

The browser provides loading/empty/error/session-expiry states, disables actions while requests run, avoids automatically retrying approval decisions, and clears displayed draft/source/lead state on logout or session loss. React escapes text; citations are displayed as text, not rendered untrusted HTML. Keyboard focus, labeled inputs, table headings, responsive navigation and automated accessibility checks support usability. Automated scans do not replace assistive-technology/user review.

## Identity, sessions and permission boundaries

Google Workspace is the owner's chosen hosted identity provider. Authlib handles the authorization-code flow with state, nonce, PKCE S256, discovery and signed ID-token validation. After cryptographic validation, the application requires exact `hd`, boolean `email_verified=true`, and a preprovisioned `google:SUBJECT` mapping to existing organization/actor memberships. Email suffix alone never grants access; there is no public registration or just-in-time role assignment. OAuth scopes are only `openid email`, not Drive/Gmail access. Tokens remain transient and are not persisted or logged.

Opaque 256-bit random session tokens are stored only as SHA-256 digests in PostgreSQL. Sessions expire absolutely after two hours and are revoked on logout. Active DB membership and synthetic organization mode are checked on every authenticated request. Cookies are HttpOnly, SameSite Strict and Secure in Google mode. The short-lived signed OIDC state cookie is SameSite Lax to allow the callback; it is separate from the application session. State-signing secrets and client secrets belong in environment variables.

Mutations require an exact configured Origin plus a per-session CSRF header. Login has exact-Origin protection without requiring an existing session. Schemas forbid additional scope/role fields; actor and organization always come from the server-mapped session. No permissive CORS or arbitrary redirects are configured. Host allowlisting, CSP, no-store, nosniff, referrer policy and Google-mode HSTS are set. Password login is disabled in Google mode.

Local demo login uses salted PBKDF2-SHA256 with 600,000 iterations, operator-provided password hashes, loopback origin and loopback peer checks. Five login attempts per username in 15 minutes are allowed; successful attempts also count. This is a development convenience with no password-reset, MFA or public-account lifecycle. Workspace policy/MFA remains the identity administrator's responsibility. Do not reverse-proxy local mode publicly.

Web generation is limited to ten attempted requests per actor per minute using serialized DB quota records; failed eligibility attempts count. At most four tools/two proposal attempts and existing cost controls remain in force. `web_login_attempts` also stores hashed generation-quota keys; it is a generic short-lived attempt ledger despite its migration name. Login activity prunes records older than one day. Add scheduled retention in hosted operations; quotas alone do not protect expensive analytics from volumetric attacks.

The application has a 16 KiB post-read request check, while the supplied proxy enforces the body limit before forwarding. The Python check alone is not a streaming memory defense. DB connections/pool waits have five-second limits; dashboard SQL uses per-statement timeouts. These are not a measured hard end-to-end deadline. Original workflow deadline/recovery limitations still apply.

## Design choices and simpler alternatives

| Choice | Reason | Simpler alternative |
|---|---|---|
| FastAPI over existing services | Reuses tested SQL/approval/citation policy; thin HTTP composition | Server-rendered pages; fewer build tools but less fit for approved separate UI |
| React + TypeScript + Vite | One small static bundle, typed view contracts, no SSR requirement | Templates with small JavaScript enhancements |
| Native semantic tables and CSS | Clear denominators, accessible content, modest bundle | Read-only metric report; no workflow interaction |
| Google OIDC through Authlib | Owner-selected enterprise identity; avoids hand-written JWT/OAuth verification | Loopback synthetic password demo only; not a hosted pilot substitute |
| Opaque DB sessions | Revocation and membership changes take effect immediately | Signed stateless session; harder immediate revocation |
| Same-origin API/static assets | Avoids credentialed cross-origin complexity | API docs/operator CLI; not a dashboard |
| Preprovisioned subject mapping | Explicit identity-to-business/role enrollment | One fixed demo account; unsuitable for multiple users |
| Process-local counters + structured logs | Low-cost first operational signals without a new service | Health checks alone; insufficient diagnostic context |
| One application container + TLS proxy + PostgreSQL | Matches modular monolith and modest workload | Virtualenv + local PostgreSQL, used in verification |

Google requires checking the hosted-domain claim rather than email suffix; see [Google OIDC reference](https://developers.google.com/identity/openid-connect/reference). The maintained integration is described in [Authlib's Starlette guide](https://docs.authlib.org/en/latest/client/starlette.html). Origin/CSRF controls supplement SameSite as recommended by [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html). None of these references establishes RevenueOS production security certification.

## Local demonstration

Install the locked Python dependencies and editable project, Node 24 and PostgreSQL 18. Create a **separate synthetic demo database**; never point the seed helper at client/production data. It runs migrations and idempotently publishes the golden synthetic CRM/corpus and a synthetic reviewer role.

```powershell
npm.cmd ci --prefix frontend --no-audit --no-fund
npm.cmd run build --prefix frontend
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/revenueos_web_demo'
# Set REVENUEOS_DEMO_PASSWORD through your secret manager/shell, at least 16 characters.
./.venv/Scripts/python scripts/serve_dashboard_demo.py
```

Open `http://127.0.0.1:8000`. Accounts `executive` and `reviewer` use the operator-supplied demo password; the helper binds only loopback and never prints it. The browser test fixture password is deliberately public test data and must never be used for hosted access. Local login throttles persist across restarts for 15 minutes; do not interpret a throttled test account as a broken server.

For a 1,000-lead demonstration, initialize a separate database with the documented seeded large bundle before knowledge seeding. Current ranking performs per-lead reads and needs batching/caching before scale claims. The browser fixture uses the small hand-checkable golden dataset; it is not a load benchmark.

## Google deployment configuration

1. Create a Google OAuth web client in the approved Workspace project. Register exactly `https://YOUR_HOST/auth/callback`; set the consent/audience policy with the Workspace administrator. No credentials were provisioned in this task.
2. Set `REVENUEOS_AUTH_MODE=google`, exact HTTPS `REVENUEOS_ORIGIN`, a random ≥32-character `REVENUEOS_STATE_SECRET`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and exact `GOOGLE_WORKSPACE_DOMAIN`.
3. Provision existing DB memberships and reviewer assignments using trusted administration. Set `REVENUEOS_IDENTITIES` to JSON such as `{"google:GOOGLE_SUBJECT":{"organization_id":"ORG_UUID","actor_id":"ACTOR_UUID"}}`. Use verified Google subject IDs, not user-entered email as authority. Do not expose the JSON in frontend environment variables.
4. Apply Alembic migrations with an owner/migration identity; run the app using a separately reviewed runtime identity. Remove real-data admission from the deployment plan until runtime roles/RLS, retention, restore and privacy controls are verified. Current runtime-role/RLS deployment is still outstanding.
5. Build the Dockerfile, configure the persistent PostgreSQL URL, TLS hostname and secrets, then deploy `deploy/compose.yaml` behind Caddy. No automatic schema migration runs at application startup; readiness requires migration 0006. The Dockerfile uses a non-root user; Compose supplies a read-only filesystem/no extra capabilities.
6. Execute real Google sign-in, wrong-tenant denial, logout/revocation, HTTPS cookie, proxy-host and restore smoke tests in the intended environment before granting users access. Offline signed-token tests do not prove real tenant enrollment/consent/network behavior.

Deployment config is supplied; Docker/cloud execution and actual Google sign-in remain unverified. Pin image digests through your deployment process after validating the target platform. No cloud resources were created and no remote push/deployment occurred.

## Monitoring and incident runbook

- `/health/live`: process response only. `/health/ready`: DB reachable and exact migration version. Both return no business records. Probe readiness every 30 seconds; page an operator after three consecutive failures. These are proposed external probe settings, not an installed monitor.
- Structured `revenueos.http` logs include request ID, status and duration; they omit URL/query, bodies, credentials and document text. Error envelopes include the same request ID. Disable ordinary access logs as in the supplied command to avoid OAuth code/query capture. Aggregate logs into an approved host collector; log retention/access controls require deployment configuration.
- `/api/monitoring`: authenticated steward-only counts by HTTP status and cumulative request duration for the current process. Counters reset on restart and are not durable totals or fleet-wide metrics. Use logs for percentiles. Review 5xx rate and latency by window; proposed alerts are >1% 5xx for five minutes and dashboard p95 >2 seconds, after measuring baseline load. No such SLO has been demonstrated.
- On suspected identity/permission/approval failure: deny access at the edge, deactivate affected membership/reviewer, delete affected `web_sessions`, preserve audit/log evidence and stop new generation. Revocation is rechecked on subsequent requests; a stolen UI screenshot/manual copy cannot be recalled.
- On DB failure: readiness fails and clients see a redacted 503/reference. Restore the service, check migration/backup state, and reconcile nonterminal workflows; do not replay approval decisions blindly. Existing service functions may leave a completed recommendation without an action if preparation fails between transactions.
- Backups: schedule encrypted managed PostgreSQL backups, document RPO/RTO with the owner, and perform an isolated restore/integrity test before real-data admission. No restore drill or deletion lifecycle has been executed here. Prune expired sessions and one-day rate records using a reviewed maintenance job; application cleanup alone is opportunistic.

CI now installs locked Python/Node dependencies, runs lint/types/PostgreSQL regressions, builds the frontend and executes Chromium against an actual seeded API/database. Hosted CI execution remains unverified locally. No live model call, OIDC credential or real data belongs in ordinary PR CI.
