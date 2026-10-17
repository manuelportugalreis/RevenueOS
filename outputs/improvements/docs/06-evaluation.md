# Evaluation strategy and measurable release gates

All targets below are proposed. Current results: **not run; no dataset, model, latency, cost, or business results exist**. A failure or inconclusive outcome must remain visible. Synthetic quality results never establish real-world conversion lift.

## Dataset and experiment protocol

Build deterministic, seeded synthetic CRM fixtures with plausible missingness, duplicates, out-of-order updates, skewed outcomes, multiple currencies, and timestamp edge cases. Document generation rules; never evaluate a scorer solely against labels generated from its own rules. Use separate seeds and independent label mechanisms to test mechanics, not predictive validity.

Build 100 human-authored knowledge/recommendation cases: 40 answerable, 20 unanswerable, 10 conflicting/expired-source, 15 injected-instruction, and 15 access-restriction cases. Add separate denial tests for external messaging, SQL/URL injection, and stale approvals. Freeze a 60-case development set and 40-case held-out set with each category represented. Record exact split, case IDs, expected evidence, adjudication, and corpus versions; use a future hidden challenge set to limit overfitting.

Two reviewers independently label factual correctness, evidence support, action appropriateness, and usability for all held-out generation cases. Adjudicate disagreement and report agreement counts. A separate test verifies that each golden source locator opens the expected passage. Compare fixed templates, lexical retrieval, lexical plus LLM, and optional hybrid plus LLM using identical case inputs. Evaluation cases are data, never prompt instructions that can grant permissions.

Real scoring evaluation uses mature, leakage-safe chronological cohorts described in the AI design. Real operational evaluation uses randomized prospective assignment described in the pilot plan. Keep these evidence types separate in reports.

## Gates, baselines, and measurement

| Area | Baseline | Measurement | Proposed gate |
|---|---|---|---|
| Import integrity | Expected fixture rows and source totals | Valid/quarantined reconciliation, repeat replay, referential constraints, conflicts | 100% fixture counts reconciled; zero duplicate business records after replay |
| Analytics | Hand-calculated fixture values | Every metric numerator/denominator, exclusions, timezone/currency edge cases | Exact integer matches; money correct to currency precision; null denominator stays undefined |
| Priority explanations | Versioned hand-computed points | Component sum and eligibility, tie order, missingness | 100% fixture match; every score traceable to as-of evidence |
| Optional predictive model | FIFO, newest-first, actual routing, rules | Precision@K/recall@K at actual rep capacity; PR-AUC; account bootstrap 95% CI | Promote only if lower CI of precision@K improvement over strongest baseline >0 and no material operational harm; otherwise retain rules |
| Retrieval | Keyword/title and lexical search | Recall@5 of human-labeled relevant passages on answerable cases | ≥90% recall@5; report counts and interval; semantic retrieval must improve held-out quality without breaking budgets |
| Citation integrity | Golden source records | IDs resolve to authorized approved versions; quotation check | 100% resolvable authorized citations; zero fabricated IDs accepted |
| Groundedness | Fixed templates and lexical excerpts | Supported verifiable factual claims / all verifiable factual claims, human-reviewed | ≥95%; zero unsupported pricing/contract/customer claims accepted |
| Abstention | Always abstain + template system | Correct abstentions / cases requiring abstention; false abstention on answerable cases | ≥95% correct abstention and ≤10% false abstention; also report coverage |
| Action/draft quality | Existing template/process | Reviewer rubric 1–5 for correctness, usefulness, tone; edit/reject reasons | ≥80% of eligible held-out drafts score ≥4 on each dimension; safety failures override average |
| Schema reliability | Typed deterministic template | First-attempt and final valid outputs, failure/abstention counts | ≥95% first attempt and ≥99% after bounded retry on repeated run suite; failed runs never shown as validated |
| Safety | Deny-by-default policy | Injection, privilege, send, stale approval and revocation tests | Zero unauthorized reads/actions/approvals in the defined suite; any failure blocks release |
| API reliability | Deterministic endpoints without provider | 200 workflow runs including ≥20 timeout/rate-limit/malformed-provider cases | ≥99% terminal responses within deadline, counting explicit safe failures separately from useful completions |
| Latency | SQL/rules/template path | 200 measured warm runs, five concurrent users, planning dataset; separate cold starts | Metrics p95 ≤2s; draft p95 ≤15s; hard workflow deadline 30s |
| Cost | Zero-model template workflow | Total generation spend / all attempted workflows, including failures/retries | Mean ≤$0.03 and p95 ≤$0.05 per workflow; enforce provisional $100/month demo ceiling |
| User value | Existing manual workflow | Intention-to-treat time, quality, rework, mature qualification | Pilot target ≥20% task-time reduction; quality and business intervals reported; no lift claim without evidence |

Small held-out samples produce wide intervals. Report counts, intervals, and case-level failures even if a percentage passes. For example, a 95% target with few abstention cases can require every case to succeed. Zero suite violations establishes only the tested cases. The repeated-run suite should run held-out cases five times for nondeterministic behavior; repeated cases do not increase the number of independent semantic cases. Expand the suite for real pilot risks before claiming broader reliability.

For optional ML, capacity K is selected from actual daily rep capacity before scoring, not chosen to maximize test performance. Report segment/source/company-size coverage and false-negative workload; do not optimize for protected characteristics. Compare calibrated probability quality with constant-prevalence predictions if probabilities are shown. Do not equate predictive association with the effect of contacting a lead.

## Measurement implementation plan

Store per-case outputs, reviewer decisions, exact source IDs, dataset hashes, Git commit, dependency lock hash, prompt/model/config versions, runtime environment, start/end timestamps, token counts, timeout/failure codes, and costs. Use a monotonic clock for duration. Capture queue wait, retrieval, generation, validation, and human review separately. When provider usage is unavailable, mark cost estimated/unknown and reconcile later; do not count it as free. Embedding/indexing and fixed hosting costs appear separately in monthly totals.

CI after approval: Python lint/type checks/unit tests, actual PostgreSQL integration tests, frontend type/build checks, and a small browser end-to-end path. Use pytest, Ruff, a selected Python type checker, and Playwright where suitable. Mock providers for deterministic contracts/failure injection; run a controlled live-model evaluation manually or on an explicitly budgeted release job. No live model calls with private data from ordinary PR CI. Security negative tests must use the runtime database role. Migration/restore checks run before a pilot release.

Evaluation reports include a results ledger with columns: claim, evidence type (synthetic observed / real retrospective / real randomized / assumption / simulation), sample/period, version, point estimate, interval, caveats, and pass/fail/inconclusive. Never replace a failed held-out set after seeing results without declaring a new experiment.

## Simpler alternative

For an early slice, use fixed fixture assertions plus 20 manually reviewed cases. This is sufficient for development feedback, not the release or pilot gates above. Add benchmark breadth as capabilities arrive, rather than an elaborate evaluation platform before the first working workflow.
