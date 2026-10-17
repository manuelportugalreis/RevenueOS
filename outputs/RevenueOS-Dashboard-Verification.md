# Dashboard and portfolio verification

Date: 2026-10-16, America/Phoenix. The owner authorized dashboard/authentication/deployment/monitoring, then the evaluation/portfolio increment while work continued. Google Workspace was explicitly selected. Offline model execution and no external delivery remain in force.

| Check | Actual result |
|---|---|
| Final combined Python/PostgreSQL suite | **174 passed, zero failures/errors/skips; 223.80 seconds** |
| Comparison harness subset | Eight passed, 3.42 seconds |
| Final API guard subset before combined run | 14 passed, 34.73 seconds |
| Offline signed OIDC + API intermediate suite | 17 passed, 39.36 seconds; later issuer/replay/guard cases included in final suite |
| Final Chromium journeys | **Two passed, 16.3 seconds**, actual API and separate synthetic PostgreSQL database |
| Automated axe scans | Zero violations on overview, approval inspection and mobile evaluation |
| Frontend production build | Strict TypeScript + Vite passed; JS 239.67 kB / 74.70 kB gzip |
| Python lint/format | Passed for source/migrations/tests; new helper scripts checked separately |
| Strict mypy | Passed, 19 source files |
| Dependency consistency | `pip check` passed; Python/npm locks recorded |
| Migrations | Full downgrade/re-upgrade passed; 30 application tables/two views at 0006 |
| Paired synthetic evaluation | 408 raw records; 400 measured/eight warm-ups; zero provider attempts |

The suite includes prior data/intelligence/workflow tests; scoped metrics/draft-review HTTP tests; CSRF/origin/body/Host/loopback guards; opaque session expiry/logout/membership revocation; login/generation throttles; synthetic-only admission; redacted validation/DB-outage errors; exact approval conflicts; and offline Google signature/audience/issuer/nonce/expiry/Workspace failures. State replay is rejected. Application state uses real PostgreSQL; Google HTTP is mocked, not a real tenant.

The browser journey logs in as a synthetic executive, reads exact golden metrics, opens score explanations, generates a cited template, resolves its source, observes reader review denial, signs in through a separate reviewer context, inspects recipient/hash and approves, sees the failed quality gate, then logs out and verifies unauthenticated denial. The second checks 390-pixel mobile navigation/overflow, hostile-origin denial, simulated API outage and session loss. The final loopback peer guard is additionally exercised by API regression. No browser test performs external delivery or live Google login.

Desktop/mobile screenshots were visually inspected. Automated accessibility scans cover three views, not every browser, screen reader or breakpoint. No client user study, load certification, penetration test or full dependency vulnerability audit is claimed.

## Corrections retained

An initial API setup run failed because local PostgreSQL started on 5432 instead of configured test port 55432. The service was restarted correctly; connection/pool waits now have explicit five-second limits. That failure was not treated as authentication verification.

The first full dashboard run had 164 passes/one failed test setup: it tried to change an organization's synthetic mode while a dataset correctly referenced it. The corrected test provisions a separate real-mode identity and verifies login denial, preserving the integrity constraint. Initial failure evidence is retained separately. A scenario assertion exposed binary-float monetary noise; Decimal arithmetic now passes positive/neutral/downside checks. Neither correction changes the recommendation quality gate into a pass.

## Remaining risks

- Live Google client/domain/subject enrollment, consent, HTTPS callback and network behavior are unverified; signed offline tokens are not a tenant trial.
- Docker/Caddy and hosted GitHub Actions are configured but unexecuted in their target environments. No deployment/push, production runtime-role/RLS, restore, retention/deletion drill or real-data admission is claimed.
- Monitoring provides actual health endpoints, redacted logs and protected process counters. Collection, alerts, fleet metrics and backup operations remain deployment work; thresholds are proposed.
- Logical timeouts are not forced cancellation. Recovery and atomic workflow/action preparation remain open. Per-lead SQL ranking needs batching/load work before scale claims.
- Historical recommendation gates remain failed; the new diagnostic confirms answerability/relevance limitations. Tests do not establish live-model quality, business value or real-world security guarantees.
- No clients, human time savings, actual invoices, conversion lift or realized ROI were measured.

Temporary local services are stopped after verification/export. Restart with docs/19-dashboard-guide.md. Source remains an uncommitted snapshot; hashes establish content, not a Git release.
