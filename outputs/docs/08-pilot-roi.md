# Real-business pilot and defensible ROI plan

## Pilot contract and readiness

Recruit one B2B SaaS business with inbound lead flow, a sponsor, 3–5 participating representatives as an initial feasibility assumption, and a RevOps contact. Access is not yet confirmed. Ask for a minimum necessary CRM export, source/timestamp definitions, mature historical outcomes if available, approved sales material, and a documented current workflow. No need for email credentials or CRM write access.

Agree in writing on the business problem, eligible lead population, qualification criteria, data processing, retention/deletion, permitted claims, provider use, pilot duration, users, budget, baseline process, evaluation protocol, incident contacts, and stop rules. Explain that AI drafts require review and delivery remains manual. Demonstrate access, deletion, restore, approval, and kill-switch tests before real data enters the system.

Use a two-week baseline/readiness period to observe normal work and validate task instrumentation. A 4–6 week randomized workflow trial follows if volume supports it. Continue qualification follow-up for 30 days after the final included lead and revenue observation for at least 90 days or the relevant sales cycle. Do not force an immature revenue conclusion into the short pilot window.

## Experimental design

Prefer stable account-level randomization to baseline versus RevenueOS assistance; all leads from an account stay in one arm. Stratify by lead source, arrival week, and representative when feasible, locking assignments before suggestions are visible. Baseline users retain the existing CRM process; treatment receives the priority/evidence/draft workflow. This estimates the bundled workflow effect, not each feature's effect. A separate within-task crossover can measure drafting time, but cannot establish queue-prioritization effects.

Keep account assignment stable, record any reassignment, and analyze by original assignment (intention to treat). Record lead volume, rep, source, missingness, task completion, active preparation/review/edit time, rework, contact events if reliably sourced, and mature qualification. Define idle-time handling before collecting timing; log both elapsed and active time where available. For the primary per-lead time measure, include review/edit/rework and allocate daily queue-triage time across processed leads. Treat unprocessed leads explicitly; otherwise prioritization can make the completed-task subset misleading.

Primary operational endpoint: total active preparation/review effort per eligible assigned lead within seven days, with task completion reported alongside it. Proposed value target: ≥20% reduction relative to baseline. Guardrails: task-completion rate and independent blinded factual/action quality, each with a proposed non-inferiority margin of five percentage points. Review a prespecified random sample of completed baseline and treatment work using the same rubric; report selection and missingness. Declare success only if the time-reduction 95% interval excludes zero, the point reduction reaches the target, and the lower intervals for treatment-minus-baseline completion and acceptable quality are each above −5 percentage points. This prevents reduced effort through skipped work from being called a success. Safety failures override these endpoints. Agree margins with the sponsor before assignment.

Secondary outcomes: first response where verified, rep adoption, edit/reject rate, qualified within 30 days, and realized contribution margin after maturity. Leads with incomplete windows are censored or excluded from the mature conversion denominator under the locked rule, never counted as negatives. Randomization does not repair poor data coverage: report missingness by arm and sensitivity bounds. Survey perceived usefulness separately from measured performance.

An analyst estimates required sample size from observed baseline variance/rate, minimum useful effect, account clustering, and expected attrition before the trial. No arbitrary user count guarantees adequate power. Use account-cluster bootstrap or an appropriate prespecified clustered model for intervals. Fix sample/window and analysis date; avoid repeated peeking and unplanned early success claims. Stop early for safety/cost incidents under the protocol. If volume is insufficient, label the exercise a feasibility pilot and report descriptive time/quality evidence without causal revenue conclusions.

With 3–5 users, learning can contaminate the baseline; log training and shared-template exposure. If spillover is unacceptable, randomize at representative/team level only after sample-size reassessment. If randomization is impossible, use matched historical or phased comparison, report seasonality/source/rep confounding, and label results observational. Never attribute all conversion change to AI.

## ROI accounting

Separate capacity, cash, and incremental gross profit. Use the same currency and time horizon for all terms.

- Net time saved per eligible lead = baseline mean total effort − treatment mean total effort, including review/rework and allocated queue work. Compute by assignment, with completion and missingness sensitivity analysis.
- Capacity hours released = eligible lead volume × net minutes saved / 60. This is capacity value, not automatically a payroll saving.
- Potential labor value = capacity hours × sponsor-supplied loaded hourly cost. Realized cash savings require documented reduced expenditure; improved utilization requires separately measured output.
- Incremental contribution = incremental attributable closed revenue × contribution-margin rate, using realized/recognized business records and the experiment's mature outcome estimate. Do not substitute open pipeline, probability-weighted opportunities, or synthetic wins.
- Total cost = engineering/setup amortized over an explicitly chosen period + hosting/storage/model/indexing + monitoring/support + training + data cleanup + any extra review work not already included in measured effort.
- ROI = (realized attributable benefit − total cost) / total cost. State break-even when cost is positive; report undefined when denominator is zero. A separate capacity-value scenario can use potential labor value, but must be labeled modeled rather than realized ROI.

Do not double-count reviewer time in both net task effort and an extra labor-cost line. Do not count the same capacity hours as both labor savings and incremental sales without evidence for distinct benefits. Report implementation cost both as a full pilot cost and, separately, under a declared ongoing amortization assumption. Low/base/high scenarios use explicit uncertain inputs and are never reported as observed returns.

## Empty evidence ledger to complete during pilot

| Measure | Evidence class | Required source | Current result |
|---|---|---|---|
| Baseline task effort and completion | Real observed baseline | Timestamped tasks, idle/rework rules | Not collected |
| Assisted task effort and completion | Real randomized, if protocol followed | Assignment + task events | Not collected |
| Quality and factual error rates | Real observed reviewer assessment | Blinded rubric + adjudication | Not collected |
| Mature qualification difference | Real randomized or observational, labeled | Outcome events + frozen cohort | Not collected |
| Realized attributable margin | Real randomized estimate if supported | Mature closed-revenue records + margin | Not collected |
| Loaded hourly rate and amortization | Business-supplied assumption | Sponsor approval | Not supplied |
| Actual operating/setup/support cost | Real observed cost | Usage ledger, invoices, time records | Not collected |
| Capacity value or revenue scenarios | Simulation | Explicit formula and assumptions | Not calculated |

## Final pilot decision

Proceed only if quality/safety gates pass, the workflow shows useful time or operating improvement, costs fit the approved budget, and the sponsor accepts the evidence and limitations. Extend an underpowered pilot only if volume can resolve the uncertainty; otherwise report inconclusive. Stop or simplify when users avoid the workflow, factual rework consumes the benefit, or data collection is unreliable.

The simpler alternative is a 1–2 week observed usability study with synthetic or de-identified cases, paired manual/assisted tasks, and no revenue claim. Use it when business access or lead volume cannot support the randomized pilot. A well-documented feasibility result is stronger portfolio evidence than invented ROI.
