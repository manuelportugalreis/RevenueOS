# RevenueOS: paired workflow evaluation

Executed 2026-10-16, America/Phoenix (raw UTC execution timestamps fall on 2026-10-17). Protocol: `paired_synthetic_workflow_v1`; source protocol was recorded before this comparison in docs/21-comparison-acceptance.md. This is an **observed synthetic software experiment**, not a client case study, human productivity trial, predictive validation or live-LLM benchmark.

## Decision

The bounded lexical/template workflow completes more authored tasks than the title/template reference, but incurs additional software latency and **fails the recommendation quality gates**. Keep it as a review-only synthetic demonstration. Do not claim production recommendation readiness, human time savings, conversion uplift or realized ROI.

Both arms use deterministic templates. “AI-assisted” refers to the implemented retrieval/workflow architecture operating in its approved offline mode; this experiment establishes no LLM reasoning advantage. The operational manual baseline has not been observed.

## Design and reproducibility

The source contains a deterministic 1,000-lead CRM snapshot, 19 synthetic sales documents and 100 authored knowledge cases in 20 families. The original 60-case dev/40-case test allocation is retained (12/8 disjoint families). All these cases were used in previous work. This rerun is post-exposure diagnostics, not a fresh hidden test; no behavior was tuned on the new results.

| Arm | Work performed | Deliberately shared controls |
|---|---|---|
| Baseline software reference | Title-keyword retrieval → fixed outreach template → validation/persistence | Same eligible lead, corpus, evidence time, scope, suppression, conflict/instruction checks, schema/quotation validation |
| Assisted software workflow | Four approved reads → lexical retrieval → same fixed template → validation/persistence + workflow audit | Same business/knowledge policy; no live planner or model |

Each case runs twice per arm, with seeded randomized case/arm order and four paired warm-up tasks: **400 measured attempts + eight separately labeled warm-ups = 408 raw records**. Each arm has 200 measured attempts and 100 unique tasks. Quality uses the first repetition only; repeated variants/repetitions never inflate the independent sample. No failures were omitted. The procedure times service invocation with a monotonic clock; evaluation grading/output inspection happens afterward.

The comparison is a bundled retrieval/orchestration contrast. It cannot isolate the effect of lexical retrieval from the effect of tools/audit, and it says nothing about the incremental effect of an LLM. Title-only matching is a deliberately simple reproducible reference, not a claim about an actual commercial team's manual workflow or the strongest available search engine. FIFO is reported separately as the queue reference; ranking does not influence the fixed-lead knowledge tasks.

`recommend(..., retrieval_method='title_keyword')` is a server-only evaluation option, never a browser permission. `run_workflow(..., evidence_at=FIXED_TIME)` fixes source validity for repeatable synthetic fixtures; web users cannot select historical evidence time. Actual audit/run execution timestamps remain actual execution time. Dataset currentness and organization/lead checks remain enabled. Default web behavior is unchanged.

Reproduce from the repository root after synthetic CRM import and `seed-knowledge` (see existing CLI guide):

```powershell
$env:DATABASE_URL='postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/revenueos_synthetic_evaluation'
./.venv/Scripts/python -m alembic upgrade head
./.venv/Scripts/python -m revenueos.comparison --organization ORG_UUID --dataset DATASET_UUID --output outputs/new-comparison-run
```

Use a new output destination. Existing attempt/report files cause refusal rather than overwrite. The harness verifies fixture checksums, records source/dependency/fixture hashes, PostgreSQL/Python/platform versions, actual start/end times, fixed source-evidence time, run/workflow IDs, output/state/failure, provider-attempt counts and raw JSONL SHA-256. Raw outputs permit independent regrading. Semantic reproduction requires the same approved fixture snapshot/config; elapsed times and UUIDs are not byte-deterministic.

## Quality results: unique tasks

| Measure | Title/template baseline | Bounded lexical/template |
|---|---:|---:|
| Fixture task success, all 100 tasks | 66/100 (66%) | 85/100 (85%) |
| Relevant answers, 40 answerable tasks | 7/40 (17.5%) | 31/40 (77.5%) |
| False abstentions, 40 answerable tasks | 33/40 (82.5%) | 9/40 (22.5%) |
| Expected abstentions, 60 abstention-required tasks | 59/60 (98.3%) | 54/60 (90%) |
| Completed responses inappropriate for the task | 1 | 6 |
| Mechanically unsupported completed responses | 0 | 0 |

“Fixture task success” means a gold-relevant completed answer on an answerable case or an actual abstention on an abstention-required case. A technical failure is never counted as a correct abstention. “Mechanically supported” means exact quotations resolve to the authorized source text; it is not human entailment/action-quality adjudication. An accurately quoted paragraph can still fail to answer the question.

The paired success difference is **+19 percentage points**, with a seeded 2,000-resample family-cluster descriptive 95% percentile interval of **+3 to +36 points**. Families, including their paired arms/variants, are resampled together. This describes sensitivity to the authored fixture, not a probability guarantee for a business population. The success metric also weights safe abstentions alongside answers, so answer coverage and errors are reported separately.

| Original split | Baseline success | Assisted success | Paired difference; descriptive family interval |
|---|---:|---:|---|
| Dev: 60 tasks, 12 families | 37/60 | 49/60 | +20 points; −5 to +46.7 |
| Previously seen test: 40 tasks, eight families | 29/40 | 36/40 | +17.5 points; +5 to +35 |

The test split is not relabeled as newly held out. Small authored family groups, shared corpus, automatic grading and exposure limit inference; repeated deterministic runs do not repair those limitations. Zero unstable case/arm outcomes across two repetitions establishes repeatability only under these local deterministic conditions.

## Gates and failure cases

Both arms fail the ≤10% false-abstention target. The assisted arm also fails the ≥95% expected-abstention target over all tasks (90%). On the original test subset it abstains correctly on 25/25 required cases, yet wrongly abstains on four of 15 answerable cases (26.7%). These reproduce the previously disclosed test-quality failure; they do not replace it with an aggregate success percentage.

Assisted failures include:

- `integrations-4`: answerable but stopped as `unsafe_source` because broad lexical candidates contained instruction-like text.
- `export-5`, `deployment-1`, `deployment-5`: answerable but stopped as `conflicting_sources`; unrelated candidate conflicts reduced coverage.
- `exact-price-1`, `exact-price-2`, `exact-price-5`: a supported billing paragraph was returned where the task required abstention from an unsupported exact-price answer. No exact price was fabricated, but the task was not correctly answered.
- `expired-1`, `expired-3`, `expired-5`: other currently authorized billing content was returned instead of an abstention. This is answerability failure, not an observed expired-document disclosure.

There are nine assisted false abstentions and six inappropriate completions in total. All case outcomes remain in the raw artifact. Prompt-injection cases and access restrictions are part of the authored fixture; separate automated negative tests cover unauthorized tools, roles, stale approval, revocation and cross-scope access. Neither suite exhausts adversarial attacks.

## Software time, human time and cost

| Observation | Baseline | Assisted |
|---|---:|---:|
| Measured software attempts | 200 | 200 |
| Mean invocation time | 27.6 ms | 202.0 ms |
| p95 invocation time | 43.9 ms | 256.5 ms |
| Technical failed attempts | 0/200 | 0/200 |
| Provider attempts | 0 | 0 |
| Measured human minutes/task | Unavailable | Unavailable |

The assisted path is slower in software due to additional reads and transactionally persisted audit/state. The measured p95 difference is approximately +212.6 ms; it must not be translated into human productivity. Timing excludes browser interaction, source reading, approval/review/editing/rework, queue handling and actual delivery. Both experiment arms ran serially on one local Windows/Python 3.12/PostgreSQL 18.6 machine. Separate regression tests ran concurrently against another database on the same machine, so these timings include uncontrolled shared-machine load. They are descriptive runtime observations, not an isolated capacity benchmark, five-user load test, cold-start/provider/network result or promised SLO. A dedicated-load benchmark remains necessary for deployment sizing.

No provider transport was configured and the run-scoped attempt ledger records zero model attempts across all 408 attempts, including warm-up. Actual provider invoices, hosting/compute expenditure, engineering cost and sales labor were **not collected** and remain null. There is no measured dollar operating-cost total. Historical scripted-token/rate examples are simulations and are not added to actual costs or used as current provider prices.

## Synthetic retrospective diagnostic

The separate queue check selects K=20 at the same synthetic snapshot: rules has 20 known outcomes/four positive synthetic outcomes; FIFO has 17 known/five positive; newest-first has zero mature known; seeded random has 12 known/three positive. Coverage and current-status selection differ. These counts do not establish rules beating FIFO or predict future conversions. All 1,000 lead records lack verified pre-outcome feature reconstruction, and labels are synthetic. Predictive training remains blocked; predictive accuracy remains null. No real-business retrospective analysis is available.

## Evidence ledger and pilot status

| Claim/category | Evidence/status | Permitted interpretation |
|---|---|---|
| Synthetic software quality/time | 408 raw attempts, code/fixture hashes | Authored task coverage, mechanical grounding, local computation |
| Synthetic historical queue composition | Current 1,000-lead diagnostic | Pipeline/evaluation mechanics, not prediction or business effect |
| Real retrospective analysis | Not available | No client labels or as-of history; no performance claim |
| Actual pilot | Not run; zero participants | No client time, adoption, quality ratings, qualification or revenue outcomes |
| Actual invoices/hosting/labor | Not collected | Unknown costs, not zero |
| Business scenarios | Explicit assumptions, separately labeled calculator | Sensitivity and feasibility hypotheses only |

The technical and business go/no-go is **continue synthetic development; do not promote recommendations or claim ROI**. First improve relevance/answerability on dev cases, commission new hidden independently labeled cases, configure/verify Google access and runtime/restore/retention controls, then recruit an authorized review-only pilot. Pilot design and value accounting are in docs/24-business-case.md and docs/08-pilot-roi.md.
