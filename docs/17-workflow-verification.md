# Bounded workflow increment: executed verification

Date: 2026-10-16, America/Phoenix. Scope: synthetic offline bounded workflows, scoped internal reads, cited recommendations/drafts, explicit approval, audit and security tests. No external model call or message delivery occurred.

## Outcome

Implemented typed read-tool schemas, server-owned scope, four-call dispatch limits, two offline planner attempts, recommendation retry/cost integration, persisted workflow states, transactional audit, immutable action versions, explicit reviewer assignment/inspection/decisions, and single-use approval rehearsal. Migration 0005 adds seven tables; the complete application now has 28 tables and two views. No third-party dependency was added. Prior architecture, CRM data, ingestion, SQL analytics, scoring, retrieval and evaluation work is preserved.

Inspection and acceptance criteria preceded implementation. Verification progressed through the workflow dispatcher, approval boundary, and complete operator flow. The pre-existing recommendation expiry assertion was unreachable inside an expected-exception block; it is now a separate executed test. The historical 109-test result is preserved as a past run, not represented as evidence that the unreachable assertion executed.

## Observed checks

| Check | Executed result |
|---|---|
| Pre-existing regressions after migration/expiry-test correction | 110 passed, 71.39 seconds |
| New dispatcher tests | 19 passed, 12.73 seconds |
| Dispatcher plus approval tests | 34 passed, 32.52 seconds |
| Final full suite, PostgreSQL 18.6, `--require-db` | **145 passed, zero failures/errors/skips; 103.88 seconds** |
| Ruff lint and format | Passed; 36 Python files formatted |
| Strict mypy | Passed; 16 source files |
| Dependency consistency | `pip check` passed |
| Migration reversal/re-upgrade | Passed in full suite; all 28 application tables and both views restored |
| Packaging | Offline wheel build passed; no dependency download |
| Operator flow | Automated CLI regression plus separate synthetic demo walkthrough passed |

The full suite includes 35 new workflow/approval/CLI cases plus the corrected independent expiry case. It exercises unknown send/approval/SQL tools; actor/organization/lead/role/URL argument injection; invalid JSON, excess plan calls and strict schemas; repeated calls; deadline checks; retrieved instruction text; parameterized SQL-like queries; audit failure rollback and UPDATE denial; unauthorized audit access; missing/wrong/stale approval; edited payloads; rejection; inactive reviewer; source revocation; suppression; proposal expiry; cross-organization action access; synthetic recipient matching; immutable versions/approvals; and two simultaneous consumers producing exactly one receipt. Existing provider tests still exercise at-most-two retries, refusals, fabricated citations, unknown usage, retained reservations, concurrent budgets and scoped stored-draft access.

These are specific adversarial fixture results, not a comprehensive proof against all prompt injection, inference leakage, or production threats. The deadline test checks stage gating; it does not establish forcible cancellation or a 30-second runtime SLO. Concurrent receipt testing establishes local database single use; no remote-delivery guarantee follows.

Reproduce the full tests using the disposable-database commands in README. The executed test command was:

```powershell
./.venv/Scripts/python -m pytest --require-db --basetemp=work/workflows-final-tests -q --tb=short --junitxml=outputs/workflow-tests.xml
```

The environment explicitly pointed `TEST_DATABASE_URL` at local `revenueos_test` and set `REVENUEOS_TEST_ALLOW_RESET=1`. No production database was used. The loopback PostgreSQL service is stopped after verification. Its ignored synthetic data remains in `work/` for local restart. Hosted CI, Docker execution, deployment, load behavior and backup/restore remain unverified.

## Reviewable evidence

- `outputs/RevenueOS-Tool-Schemas.json`: four exported read contracts with additional fields forbidden.
- `outputs/RevenueOS-Bounded-Workflow-Trace.json`: fixed offline workflow, prepared synthetic payload and failed scripted `send_email` request.
- `outputs/RevenueOS-Approval-Rehearsal.json`: inspected message/hash, missing-approval denial, explicit synthetic reviewer decision, one rehearsal receipt with `delivered=false`, and repeated-use denial.
- `outputs/RevenueOS-Workflow-Audit.json`: redacted events and verified organization audit chain. Raw recipient and document text are absent from audit subjects.
- `outputs/workflow-tests.xml`: actual combined JUnit results.

The walkthrough uses a scripted reviewer persona to test the human-facing command boundary. It does not claim a real human approved an external action. It ran against the separate 1,000-lead synthetic intelligence demo database while tests used their disposable database. Default template generation made zero model attempts; actual provider billing is unmeasured. Existing fictional price-card examples remain simulated.

## Remaining risks and next steps

1. **Recommendation quality remains blocked.** The prior frozen synthetic test had four false abstentions among 15 answerable cases (26.7%, exceeding the 10% target). This increment does not change retrieval/recommendation semantics or rerun a tuned held-out benchmark. Passing workflow tests does not resolve that quality gate. Improve evidence selection on development data and commission a fresh independently labeled challenge set before a new quality claim.
2. **Identity and security are local-demo boundaries.** Actor UUIDs come from a trusted operator. There is no OIDC/session service, authenticated human UI, least-privilege production role deployment or RLS validation. Explicit reviewer assignment cannot prove the caller is human without that identity layer. Keep real customer data and external connectors disabled until those controls and privacy/retention policies are verified.
3. **Prompt injection defenses are layered and incomplete.** Tool authority is allowlisted and server-scoped; output claims must quote approved evidence. Suspicious-text patterns can miss attacks or over-abstain. No live planner or independently evaluated live model is present. A future planner needs counted token reservations, live refusal/timeout tests and a new adversarial evaluation before enablement.
4. **Audit assurance has limits.** Transactional append-only rows and chain verification detect ordinary inconsistency under a trusted database. They do not resist a malicious administrator, full-chain rewrite or suffix truncation. Some pre-action denials and infrastructure failures are not audited. Add authenticated security-event capture, export checkpoints, retention controls and recovery procedures before pilot operation.
5. **Runtime durability is bounded, not fully orchestrated.** Logical stage deadlines and dispatcher statement timeouts do not forcibly stop trusted callbacks or all connection/lock waits. A crash can strand a nonterminal workflow or orphan a completed recommendation. Add worker timeouts, reconciliation, explicit stuck-run recovery and measured concurrency/load tests before promising runtime SLOs.
6. **External actions remain unavailable even after approval.** Future delivery requires a separately authorized connector and outbox/idempotency/reconciliation design. Current receipts explicitly record no delivery. Source revocation and consumption serialize through service locks; direct administrative writes outside those paths remain trusted and require a stronger production policy.
7. **Business evidence is still absent.** No real-business pilot, predictive accuracy, conversion uplift, outreach acceptance rate, realized cost or ROI is claimed. First validate usefulness through an authenticated review-only pilot with agreed outcome definitions and a baseline comparison.

The next useful increment is authenticated review-only access plus recovery/security hardening, alongside development-only retrieval-quality improvements. Live evaluation, real-data admission and delivery each require their outstanding design decisions and explicit authorization. No remote push or deployment was performed; current source remains uncommitted.
