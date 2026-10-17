# Business case: test value before selling lift

RevenueOS targets B2B SaaS inbound sales teams whose CRM exports, knowledge and manual review are fragmented. The commercial hypothesis is that a shared evidence-backed queue and reviewable draft reduce preparation/rework while preserving task completion, factual quality and permission boundaries. No client has confirmed this hypothesis in a measured pilot. The product's current evidence is engineering and synthetic diagnostics.

## What the evidence supports

The paired software diagnostic completed 85/100 authored tasks correctly versus 66/100 for a title-search/template reference. It also produced nine false abstentions and six inappropriate completions and failed its quality gates. No real manual task times, adoption, invoices or conversion outcomes exist. The system cannot be marketed as saving a measured number of hours, improving real qualification rates, or generating incremental revenue. A grounded citation is useful review evidence, not proof the recommendation answers the business question.

Value may come from faster evidence discovery, consistent exclusions, clearer metric definitions, fewer unsupported claims and auditable decisions. These remain measurable hypotheses for users, not realized benefits. The current rules queue has no demonstrated predictive advantage over FIFO.

## Explicit monthly sensitivity scenario

All inputs below are **illustrative analyst assumptions**, not sponsor-supplied or observed business facts. The scenario is USD/month, 1,000 eligible tasks, five baseline minutes/task, $60 loaded hourly capacity value, $100 operating cost and $300 amortized setup/support. Assisted minutes include review, editing, rework and allocated queue work; no API latency is substituted for those minutes. Decimal arithmetic is used for monetary calculations.

| Assumed assisted total minutes/task | Capacity hours released | Potential capacity value | Scenario cost | Net potential capacity value |
|---|---:|---:|---:|---:|
| 3 (optimistic hypothesis) | 33.3333 | $2,000 | $400 | $1,600 |
| 5 (no time improvement) | 0 | $0 | $400 | −$400 |
| 7 (rework/overhead dominates) | −33.3333 | −$2,000 | $400 | −$2,400 |

At the assumed two-minute saving/$60 rate, capacity value equals $2/task, giving a **hypothetical capacity break-even of 200 monthly tasks** at $400 assumed cost. At zero or negative time savings there is no finite positive capacity break-even. These are not ROI results, cash savings or price recommendations. Released capacity only becomes cash savings if actual spending falls; otherwise improved utilization requires separately measured useful output. Do not add both capacity labor value and the same labor cost reduction, or add open pipeline as incremental revenue.

Realized ROI remains null. Future calculation: `(documented realized benefits − all incremental costs) / all incremental costs`, with a common currency/horizon, maturity, attribution, uncertainty and a positive cost denominator. Include implementation, security/hosting, support, change management, review/rework and model invoices. Unknown usage retains reservations until reconciled; a zero-model demo is not a zero-cost service.

## Review-only pilot protocol: designed, not executed

1. Recruit one sponsor, RevOps owner and representative users; obtain written data/knowledge permissions, privacy/provider terms, deletion/retention, budget, outcomes, incident owner and stop rules. Current recruitment, clients, participants and pilot observations: **none**.
2. Complete hosted Google sign-in and enrollment, restricted runtime-role/access tests, privacy/retention, isolated restore and recovery checks. Keep external delivery disabled. Fix answerability/relevance on dev data and obtain fresh independently labeled hidden cases before a product-quality claim.
3. Spend two weeks observing the actual baseline: same eligible inbound population, documented CRM/manual search/templates, active prep/review/edit/rework, queue time and task completion. Collect source/rep/account/week, censoring and missingness. Do not silently fill missing timers with zero or infer sales contact from draft approval.
4. Lock a 4–6 week account-randomized review-only trial if volume supports it. Keep accounts in one arm, stratify source/week/rep where practical, prevent cross-arm template contamination, and analyze original assignment. An analyst estimates power from baseline variance, clustering and the minimum useful effect before enrollment; 3–5 reps alone do not establish adequate power. If infeasible, use an explicitly labeled feasibility/usability study or observational matched comparison with confounding limitations.
5. Primary endpoint: active preparation/review/rework plus allocated queue effort per **eligible assigned lead** within seven days. Report completion alongside effort so skipped work cannot masquerade as efficiency. Proposed target: point estimate ≥20% time reduction with a 95% interval excluding zero, and completion/independent acceptable-quality lower differences both above −5 percentage points. Sponsor must approve those margins before assignment.
6. Independently blind and double-rate a prespecified random sample of both arms for factual support, relevance/action appropriateness, tone and completeness. Report agreement/adjudication and edit/reject reasons. Unsafe external action or unauthorized disclosure stops the trial irrespective of averages.
7. Use account-cluster bootstrap or the locked clustered model for time/quality intervals, report missingness by arm and sensitivity bounds, and avoid repeated success peeking. Qualification follows a mature 30-day window; realized revenue/contribution follows at least 90 days or the actual sales cycle. Underpowered results are inconclusive, not fabricated success.
8. Reconcile costs against usage ledgers/invoices and actual engineering/support time. Report capacity, cash and attributable contribution separately. Sponsor chooses stop, simplify, extend for an answerable uncertainty, or proceed only when safety/quality/value gates pass.

The empty CSV template in `data/pilot/task-observations-template.csv` is a proposed collection contract, not a dataset or executed pilot analysis. The real-data admission guard remains enabled; no pilot data processor or production experiment platform is claimed. The simpler alternative is a small paired synthetic usability study with balanced task order, no sales lift claim and honest learning/spillover caveats.
