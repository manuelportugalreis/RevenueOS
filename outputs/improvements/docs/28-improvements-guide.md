# Five improvements: design and operator guide

This increment follows [the acceptance criteria](27-improvements-acceptance.md). Everything remains fictitious, as explicitly confirmed by the owner. No company, live model, actual Google tenant, independent reviewer or customer outcome is represented. Historical reports remain intact.

## 1. More relevant, explainable recommendations

`evidence.select_evidence` applies a versioned policy to up to 20 authorized lexical candidates. PostgreSQL English stemming compares query terms against passage bodies, with metadata coverage breaking ties. At least half of query terms must match a body. Equally ranked evidence must share a claim key; at most five passages survive. Lifecycle/confidentiality qualifiers must occur in the passage; numerical precision requests require numerical evidence. The generator quotes whole original passages, never synthesized source text. Existing global claim-conflict, revocation, lawful-use, access and citation checks remain authoritative.

Why: it addresses metadata-only matches and irrelevant context without model expense or a new service. Simpler alternative: keep the lexical top five and accept more manual rejection. Limitation: this is an English lexical heuristic, not semantic entailment. A digit is insufficient to prove that an exact amount answers a question. Negation, paraphrases and multilingual questions can still fail. The retained `deadlines-3` error demonstrates that grounded text can be inappropriate. No serving code reads expected labels, case IDs or fixture paths.

`ai_runs` records retrieval method, evidence profile and selection summary. Historical rows are `unrecorded`, not retrospectively relabeled. `legacy_v1` remains available to reproduce earlier comparisons. No predictive model is trained: real labels and point-in-time feature history are still unavailable.

## 2. Stronger evaluation and honest ablation

Four arms share the same eligible synthetic lead, approved corpus, evidence time and output validation: title/template reference, legacy lexical/template, focused direct/template and focused bounded/template. The last two isolate tool orchestration from evidence selection. Two serial repetitions plus 16 warm-ups produce 816 raw rows for 100 authored tasks. Primary quality counts unique first repetitions; technical errors never count as successful abstentions. Twenty correlated families support a descriptive paired bootstrap, not a population confidence claim.

Why: a weak title baseline alone exaggerates the apparent value of agents. Simpler alternative: compare direct focused retrieval with legacy lexical retrieval only. Bounded tools remain useful for permissions and audit; the current experiment shows no quality improvement over the same direct template. The original test split was already exposed in earlier work. Development cases guided this policy; all subsequent test results are diagnostic, never a fresh held-out estimate. Supplemental cases and blank reviewer packets are also not independent review. Do not tune against the retained test failure and call the rerun a new test.

Reproduce after migrating and seeding an isolated synthetic dataset:

```powershell
./.venv/Scripts/python -m revenueos.comparison --organization ORGANIZATION_UUID --dataset DATASET_UUID --variant ablation --split dev --output work/dev-comparison
# Freeze the selector before inspecting previously exposed test diagnostics.
./.venv/Scripts/python -m revenueos.comparison --organization ORGANIZATION_UUID --dataset DATASET_UUID --variant ablation --split all --output work/final-comparison
```

Use a new output directory for every execution. Keep source hashes, fixture hashes, JSONL attempts and report together. All four arms here are templates, not a live LLM evaluation. Provider attempts are observed zero; invoice, hosting and labor costs remain unknown.

## 3. Database permission boundaries

Migrations `0007` and `0008` add request binding, organization RLS, document membership restrictions, invoker-security views and evidence lineage. A separately provisioned login inherits the narrowly granted `revenueos_runtime` capability role. It owns no application tables and cannot bypass RLS, create schema objects, alter membership/reviewer assignments, truncate CRM data or insert delivery receipts. Explicit table grants avoid silently granting future tables. Session bootstrap uses one SECURITY DEFINER function with fixed search path, hashed opaque-session lookup and revoked PUBLIC execution.

Why: application predicates alone are vulnerable to omitted organization filters. Simpler alternative: a separate synthetic database per demo organization and application checks, with no multi-tenant claim. Owners/admins still bypass RLS; request context variables trust the application process and parameterized SQL. This is not protection against a compromised database owner or arbitrary malicious SQL in the server. Actor-level recommendation/approval checks remain service responsibilities; document visibility also has database policies. The runtime has limited write powers needed by the application and must never be exposed as a user SQL console.

Run administrator migrations and `python -m revenueos.operations provision-runtime` before serving. An administrator must create a separate non-owner LOGIN and grant it `revenueos_runtime`, with credentials delivered through environment variables/secret management. Provisioning does not create a password. `python -m revenueos.operations runtime-check` reports flags and inherited relation ownership; Google mode refuses an unrestricted database role. It does not establish that Google credentials or TLS work.

For the loopback synthetic helper only, `DATABASE_URL` performs migration/seeding and optional `REVENUEOS_RUNTIME_DATABASE_URL` serves HTTP. Hosted factory `DATABASE_URL` itself must be the runtime login; migrations are a separate administrator step. The default owner-backed local helper remains convenient but is not a restricted deployment. Never reuse fixture passwords outside disposable tests.

The local restore uses `--no-acl`: grants **and PUBLIC revokes** must be reapplied with `provision-runtime`, followed by tenant/document/no-context tests before admission. The executed follow-up did this with a native non-owner login. Local trust authentication means password verification and encrypted network transport were not tested. PostgreSQL references: [row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), [invoker views](https://www.postgresql.org/docs/current/sql-createview.html), [restore ACL behavior](https://www.postgresql.org/docs/current/app-pgrestore.html).

## 4. Recovery and bounded performance

The browser retains a UUID request key for an unchanged lead/query after an uncertain response. Server requests bind organization, actor, key and payload hash. An advisory lock rejects concurrent duplicates, different payloads conflict, and a per-organization quota bounds new work. Terminal replays revalidate eligibility; completed recommendations can reuse one prepared action. A crash before action preparation can resume preparation without regenerating. Active or unlinked interrupted generation is never automatically retried. Approval is still a separate exact-version human decision; no delivery endpoint exists.

Why: retrying a network request must not create duplicate drafts or duplicate paid generations. Simpler alternative: disable repeat submissions and require an operator to resolve every ambiguous response. Request history currently has no automated retention schedule; queueing and background retry infrastructure are intentionally absent.

An authorized steward may run:

```powershell
./.venv/Scripts/python -m revenueos.operations reconcile --organization ORGANIZATION_UUID --actor STEWARD_UUID --age-minutes 15
```

It fails old active work with an audit event, marks reserved model attempts `usage_unknown` and retains reservations. It never generates, approves or sends. Minimum age is five minutes; choose an age longer than the maximum legitimate execution time. There is no scheduled reconciliation in this demo. Reconcile can terminate an unusually long run; a late completion cannot overwrite the failed workflow state.

Ranking now batches lead/context/interaction reads: four client SQL statements including transaction scope, instead of 3,001 for the 1,000-lead reference. Explanations and scores are compared with the unchanged single-lead scorer. Simpler alternative: retain per-lead reads for eight-row fixtures. Whole-dataset memory and dashboard payload size remain scaling limits; pagination and bounded SQL aggregation should precede a large tenant.

Restore drill, localhost and synthetic databases only:

```powershell
$env:PG_BINDIR='PATH_TO_POSTGRES_CLIENT_BIN'
./.venv/Scripts/python -m revenueos.restore_drill --target revenueos_restore_check_UNIQUE_SUFFIX --output work/restore-report.json
```

Use lowercase suffix characters. Existing targets/artifacts are refused; no database is dropped. Row fingerprints, policies and schema version are checked. Then re-provision privileges and verify a native restricted login. The dump contains synthetic data and is ignored under `work/backups`; it is not an encrypted/off-site backup plan. Local execution seconds are not production recovery objectives.

## 5. Fictitious business rehearsal

`data/pilot/fictitious-rehearsal.json` defines three explicitly scripted scenarios, each with 12 baseline/assisted pairs. The strict contract tracks preparation, review, rework, queue time, completion, acceptability and missingness. Missing time is never zero. All assigned tasks enter quality/completion denominators. A favorable assumption produces a scenario decision; a rework downside fails; one missing measurement makes aggregate time savings inconclusive. Real participants remain zero and realized ROI remains null.

```powershell
./.venv/Scripts/python -m revenueos.operations rehearse-pilot --input data/pilot/fictitious-rehearsal.json --output work/rehearsal.json
```

Why: business value depends on review burden and completion, not generation latency alone. Simpler alternative: a documented spreadsheet scenario with no claim of an experiment. No real pilot is being recruited or run. To obtain future business evidence, first authorize a participant/data agreement, security review, independent quality rubric and preregistered randomized/counterbalanced task protocol. Measure total human effort, rework, errors, actual invoices and opportunity costs; report uncertainty and all assigned tasks. Any conversion study needs sufficient sample size and follow-up. Assumed ROI may support a business case, but realized ROI requires observed incremental margin and costs.

## Interview walkthrough

Show the synthetic banner and explained priority first. Generate a configuration-checklist recommendation; inspect exact source/version and human approval. Repeat the same request key to show one workflow. Show the evaluation tab's independent-review warning, the 99/100 diagnostic and retained failure. Explain that direct focused retrieval has the same quality as bounded tools at lower software latency. End with the downside/missingness rehearsal and null ROI. This demonstrates engineering judgment without inventing a client story.
