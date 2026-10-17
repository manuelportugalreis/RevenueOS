# Five improvements: executed verification and remaining risks

Everything is fictitious. There is no pilot company, real participant, authorized client dataset or live model evaluation. This increment implements the five improvements under [predeclared acceptance criteria](docs/27-improvements-acceptance.md). Source and reproduction instructions: [operator guide](docs/28-improvements-guide.md).

## Observed synthetic evaluation

The final source-matched four-arm execution completed on 2026-10-17T03:31:15.722190+00:00. It contains **800 measured attempts plus 16 warm-ups**, two repetitions of 100 authored tasks, with first repetitions used for unique quality counts. The earlier v2 execution is retained separately; the final repeat followed a restore ACL hardening change, without evidence-policy tuning. Old v1 results are preserved rather than overwritten.

| Offline template arm | Authored task successes | False abstentions | Inappropriate completions | Mean / p95 software ms |
|---|---:|---:|---:|---:|
| baseline_title_template | 66/100 | 33/40 | 1 | 28.3 / 45.8 |
| legacy_lexical_template | 85/100 | 9/40 | 6 | 32.6 / 48.7 |
| focused_direct_template | 99/100 | 0/40 | 1 | 33.7 / 49.8 |
| focused_bounded_template | 99/100 | 0/40 | 1 | 203.6 / 227.8 |

Both focused arms answered all 40 answerable fixtures with relevant grounded passages, correctly abstained on 59/60 abstention fixtures, and had zero unsupported completions or technical failures across 200 measured attempts each. The two configured abstention gates pass (false abstentions <=10%, correct abstentions >=95%); **independent human quality approval remains unavailable**. This is fixture task success, not predictive accuracy, general model quality or customer readiness. The selector is an English lexical heuristic; exactness, negation and unfamiliar paraphrases remain risks.

**Retained failure:** `deadlines-3` asks an unanswerable deadline question; the focused policy returns grounded but inappropriate material. The case was not patched after inspecting test diagnostics. It requires refusal or clarification. Previously exposed test-only results are 39/40, including 15/15 answerable and 24/25 correct abstentions. The original split was already seen in earlier work; no fresh hidden test or independent annotations are claimed.

Focused direct versus legacy lexical improves authored task success by 14 percentage points, with a descriptive 20-family bootstrap interval +5 to +25. In the previously exposed eight-family test subset the difference is +7.5 points, interval -5 to +20; uncertainty includes no improvement. Focused bounded versus focused direct is zero, interval [0,0] on these tasks. These intervals describe fixture sensitivity, not population inference. Tool orchestration adds audit/permissions, not demonstrated semantic benefit. Prefer the direct focused pipeline when those workflow controls are unnecessary.

Provider calls and attempts: **zero** in all arms. Actual invoices, hosting and labor costs are null, not asserted zero. Human time, conversion and ROI were not measured. Predictive training remains blocked for insufficient real point-in-time labels. No live LLM performance claim is made.

## Executed engineering checks

- Combined Python/PostgreSQL suite: **207 passed in 291.51 seconds**, no failures or skips. JUnit: `python-tests.xml`.
- After the PUBLIC-permission restoration fix: **8 runtime security regressions passed in 17.53 seconds**, including the additional PUBLIC-function ACL assertion. This is a targeted repeat of tests in the 207, not 215 unique tests.
- Chromium: two journeys passed in 16.2 seconds, including actual browser/API/native restricted PostgreSQL login, exact-version human approval, same-key replay, logout/error handling and mobile evaluation. Three axe scans found no violations; this is not accessibility certification. Current JUnit and screenshots accompany the report.
- Ruff lint and formatting passed; 57 source/migration/test files formatted. Strict mypy passed for 25 source modules. TypeScript/Vite production build passed. Dependency check found no broken requirements. Offline wheel build also passed. No dependencies were added for this increment.
- Ranking experiment: 1,000 synthetic leads, three samples per implementation. Four client SQL statements including context versus 3,001 in the single-lead reference. All score explanations matched. Median local software time was 190.3 ms versus 3,823.9 ms. The reference excludes queue sorting; this is not a production benchmark or human time saving.
- Small API exercise: 25 authenticated requests with five concurrent clients, correct golden KPI for every response, zero failures, local HTTP p95 597.5 ms. Fixture: eight leads. No sustained-load or capacity claim.
- Restore drill: a new, isolated database was created without deleting any existing database. All table row fingerprints matched before/source-after/restore, schema `0008`, 30 tenant policies restored. Local dump 1.62 seconds; restore 2.63 seconds. These are not production RPO/RTO guarantees.
- Post-restore runtime grants and PUBLIC revokes were reapplied. Actual non-owner login saw zero unscoped leads, 1,000 correctly scoped leads and zero management documents for a reader; PUBLIC had neither session-lookup execution nor schema CREATE. Local trust authentication means password verification/TLS were not tested.
- Recovery tests cover duplicate concurrency, changed-payload conflict, interrupted action preparation, stale workflow failure, retained unknown-cost reservations and safe abstention replay. Reconciliation never sends or approves; unknown generations are not retried.

The first runtime test attempt used a connection-scoped SET ROLE that the connection pool reset; it failed the posture assertion. The fixture was corrected to use an actual separate PostgreSQL LOGIN before the passing full and browser runs. No failure was counted as a successful check. Hosted GitHub Actions configuration now uses the separate runtime login for browser checks; the hosted job itself has not been executed here.

## Scripted business rehearsal

Three scenarios each contain 12 paired baseline/assisted tasks with scripted time and quality inputs. Favorable assumptions imply 38.1% less total effort; review/rework downside implies 28.6% more effort and fails quality; missing timing produces no aggregate time-saving estimate. These are deliberately constructed assumptions. They are **not observed human effort or client outcomes**. All scenarios retain zero real participants, null measured human savings and null realized ROI.

A 400-row shuffled review packet has empty independent ratings. A separate coordinator key contains automated labels and arm identities. Preparing a packet is not conducting a human review. Do not count these empty rows as observations.

## Risk and next-step register

| Risk | Current control / evidence | Remaining decision or next step |
|---|---|---|
| Grounded but irrelevant answer | Focused policy, retained failure, abstention and citation checks | Independent rubric review; new unseen challenge set before broader quality claims |
| Synthetic overfitting / weak baseline | Legacy lexical and direct-focused controls; exposed split disclosed | Author-independent prospective tasks; no claim of held-out predictive accuracy |
| Privilege/context errors | Actual native login, org/document RLS, no-context/cross-org/DDL/membership denials | Application is trusted to set tenant/actor; administrator or arbitrary server SQL compromise remains outside this boundary |
| External identity / transport | Offline signed OIDC tests; unrestricted DB rejected for Google mode | No actual domain, Workspace login, TLS ingress or cloud deployment validated; keep real data blocked |
| Duplicate requests / interrupted cost | Bound idempotency keys, stale reconciliation and retained reservations | Operator scheduling/retention still needed; never automatically retry unknown provider spend |
| Large tenant performance | Batched scoring and small bounded observations | Whole-dataset memory/payload scaling; pagination, sustained load and resource limits unverified |
| Backup confidentiality / recovery | Actual isolated restore, row fingerprints and privilege re-provisioning | Encrypted off-site backups, credentials, retention and production recovery objectives untested |
| Adoption / economics | Rework/downside/missingness scenarios, null ROI | No company or participants; future pilot only with explicit authorization and measured total effort/cost |
| Live model behavior / spend | Live transport disabled; templates and zero observed attempts | Provider, budget, privacy review and independent live evaluation required before enabling |

Next engineering priority is an independent, newly authored quality set and explicit clarification behavior for ambiguous questions, preserving this report as diagnostic history. Next business priority, only if the owner chooses it later, is an authorized participant and measurement protocol. The current deliverable is a defensible synthetic engineering demonstration, not production or pilot certification.

## Evidence provenance

Use `outputs/improvements/final-ablation/` for the final comparison JSON and raw JSONL. Its source/fixture/raw hashes are verified during export. `RevenueOS-Performance.json`, `RevenueOS-Restore-Drill.json`, `RevenueOS-Restore-Security-Check.json`, `RevenueOS-Fictitious-Rehearsal.json` and JUnit files contain the observations cited above. The source archive and manifest identify an uncommitted workspace snapshot, not a published Git commit. Earlier root exports and v1 documents are historical and remain unchanged.
