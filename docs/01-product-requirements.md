# Product requirements, business problem, and personas

## Problem statement

A B2B SaaS commercial team receives inbound leads while its CRM mixes incomplete profiles, interaction records, opportunities, and inconsistent outcomes. Representatives spend time assembling context and locating approved product information. Managers cannot consistently explain why leads receive attention, whether response delays matter, or whether AI suggestions improve work.

RevenueOS tests the hypothesis that a visible, consistent queue plus evidence-backed preparation can reduce review effort without reducing qualification quality. Slow follow-up, missed opportunities, and inconsistent messaging are plausible problems to validate with a pilot sponsor, not established findings about a particular company. The CRM remains the system of record.

Before development, interview two representatives, one RevOps operator, and the sponsor. Observe five actual lead-review tasks if authorized; record elapsed time, rework, source systems, data availability, and the definition of a qualified lead. Collect baseline volumes and conversion denominators. Reprioritize the scope if context assembly is not a material problem.

## Representative personas

These are design personas, not interviewed users.

| Persona | Job and friction | Core workflow | Success evidence |
|---|---|---|---|
| Maya, inbound sales representative | Must decide whom to contact; context is scattered and suggestions can be hard to trust | Review queue → inspect score reasons and source evidence → edit/reject draft → approve for manual use | Less time per review, acceptable drafts, fewer factual corrections |
| Jordan, RevOps manager | Owns CRM hygiene and routing; inconsistent timestamps and stage definitions weaken reporting | Map CSV fields → resolve quarantine → inspect freshness and funnel → review exceptions | Reconciled metrics, explainable ordering, reproducible imports |
| Alex, head of sales and pilot sponsor | Needs credible operational value and clear risk ownership | Inspect executive metrics, adoption, costs, and controlled pilot results | Faster work with no material quality harm; auditable value claim |

## Product scope

The minimum valuable release includes CSV preview/validation, dataset lineage, a lead queue with transparent score contributions, deterministic dashboard metrics, approved-document search with citations, and a bounded recommendation/draft workflow. Every draft is visibly unapproved until a named person reviews it. Every page identifies synthetic datasets and data freshness.

Next, add evaluations, auditability, operational controls, and a reproducible demo. A real pilot follows readiness review. API-based CRM ingestion, semantic retrieval, and supervised scoring are conditional enhancements. No autonomous sending, CRM writes, arbitrary SQL agent, general-purpose web browsing, autonomous prospecting, fine-tuning, revenue forecasting, or multi-agent framework is in the first release. No dependency on classical ML to deliver the initial value.

## Functional requirements and acceptance

| ID | User need | Acceptance criterion |
|---|---|---|
| P1 | Trust imported data | Preview mapping; report row/field errors; quarantine invalid rows; explicit commit; replay causes no duplicate business records |
| P2 | Understand sales performance | Each metric has SQL definition, period, source version, denominator, missing-data count, and freshness; reconcile fixed fixtures exactly |
| P3 | Work an explained queue | Show score version, as-of time, eligibility, components, missing values, and deterministic tie-break; allow baseline comparison |
| P4 | Find approved knowledge | Search authorized current versions only; open citations to exact passages; abstain when evidence is insufficient |
| P5 | Prepare a next action | Typed output separates recommendation, evidence, missing facts, and draft; only permitted actions accepted |
| P6 | Retain control | Reviewer can edit/reject/approve; edits invalidate prior approval; approval never triggers external delivery |
| P7 | Explain system behavior | Trace import, features, sources, prompts/models, validation, cost, review, and evaluation by run ID |
| P8 | Demonstrate responsibly | Seeded synthetic scenario, reproducible setup, limits and failure demo, and results ledger distinguishing simulated from observed |

## Executive metric contract

- Inbound leads: distinct eligible external lead IDs created in the selected interval, grouped by source; test/internal records excluded by explicit rules.
- First response: earliest human outbound contact after lead creation minus creation time. Report median/p90 and unresolved counts separately; exclude automated acknowledgments and never substitute draft approval for contact. Business-hour timing is deferred.
- Qualification rate: leads qualified within 30 days / eligible leads with a complete 30-day follow-up window. Missing observation is unknown, not failure. Report cohort dates and exclusions.
- Win rate: won opportunities / (won + lost opportunities) closed in the interval; show open count separately. This is different from lead conversion.
- Open pipeline: sum of open opportunity amounts as of the snapshot, in one currency. Label as pipeline, never realized revenue. Do not claim historical pipeline without historical state.
- AI acceptance: approved draft versions / reviewed draft versions, paired with edit rate and independent quality review. Acceptance is not factual correctness or ROI.

Qualification and eligibility definitions are versioned with the sponsor. Use contact/opportunity linkage to avoid counting several opportunities as several converted leads. Historical cohort reporting is unavailable when snapshot/history coverage cannot support it.

## Experience and operational constraints

Support keyboard navigation, readable evidence links, empty/error/loading states, actionable validation messages, and explicit stale-data banners. Target dashboard p95 ≤2 seconds and draft workflow p95 ≤15 seconds at the declared evaluation workload. Provide cancellation and a safe failure state; provider downtime leaves analytics and rules usable. These are release targets requiring measurement.

The interview narrative should show one successful case, one abstention, one rejected malicious document instruction, and one outage fallback. A credible demonstration explains denominators, lineage, tradeoffs, and failed hypotheses, not just an attractive generated answer.
