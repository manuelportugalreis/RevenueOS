# RevenueOS planning pack

Current implementation: [dashboard operations](19-dashboard-guide.md), [executed verification](20-dashboard-verification.md), [current architecture](22-architecture-current.md), [paired diagnostic](23-comparison-report.md), [business case](24-business-case.md), [case study](25-case-study.md) and [interview demo](26-interview-demo.md). The combined suite passed 174 tests. Recommendation quality remains blocked; live Google/cloud/model/pilot results are unverified or unavailable. These current documents supplement the historical proposal below.

Status: architecture approved by the owner. Data foundation, intelligence, and bounded workflow increments authorized on 2026-10-16; live model evaluation deferred by explicit owner choice. Original planning date: 2026-10-16.

RevenueOS helps B2B SaaS teams decide which inbound leads to work, understand the evidence, and prepare outreach for human review. The first product slice is **validated CSV → trusted metrics → explained priority → cited recommendation → reviewed draft**.

This pack records the original proposal. Data-foundation implementation now follows [the acceptance criteria](09-data-foundation-acceptance.md) and [the implementation guide](10-data-foundation-guide.md). The original planning exports in `outputs/` remain historical review copies.

See [executed verification and remaining limits](11-data-foundation-verification.md) for this increment's measured test results.

The next increment is documented in [intelligence acceptance criteria](12-intelligence-acceptance.md) and [the implementation guide](13-intelligence-guide.md). It retains a rules baseline, gates predictive modeling off for insufficient real labels/as-of history, and evaluates retrieval and structured recommendations offline.

[Intelligence verification](14-intelligence-verification.md) records 109 passing tests, fixed synthetic baseline comparisons, failed recommendation quality gates, and all unverified production/live-model claims.

The current bounded workflow increment follows [workflow acceptance criteria](15-workflow-acceptance.md), [design and operator guide](16-workflow-guide.md), and [executed verification](17-workflow-verification.md). It adds typed scoped read tools, transactional audit, immutable draft versions, explicit reviewer decisions and one-use offline rehearsal. The combined regression suite has 145 passing tests; historical recommendation-quality failures remain open.

## Reading order and deliverables

| Document | Contents | Requested deliverables |
|---|---|---|
| [Product requirements](01-product-requirements.md) | Problem, personas, scope, stories, metric definitions | A, B, C |
| [Architecture and decisions](02-architecture.md) | Components, flows, interfaces, alternatives, deployment | D; technical decisions |
| [Data model](03-data-model.md) | Tables, relationships, constraints, history, ingestion | E |
| [AI design](04-ai-design.md) | Rules, ML, retrieval, structured generation, bounded tools | F |
| [Security and governance](05-security-governance.md) | Access, privacy, approvals, threats, operational controls | G |
| [Evaluation](06-evaluation.md) | Baselines, datasets, gates, measurement protocols | H |
| [Roadmap and risks](07-roadmap-risks.md) | Phases, acceptance, dependencies, risk register | I, J |
| [Pilot and business impact](08-pilot-roi.md) | Recruitment, experiments, costs, ROI evidence | K |

## Repository inspection

The supplied working directory was inspected, including hidden-file discovery and applicable ancestor `AGENTS.md` checks. Initially only empty `work/` and `outputs/` directories existed. No source, documentation, configuration, datasets, or applicable `AGENTS.md` files were found. `git rev-parse` and `git status` reported that this directory is not a Git repository. There is no existing application to preserve or Git diff to report. Inspection scope is this workspace and its instruction ancestors, not unrelated user directories.

## Decision status and assumptions

| Item | Status | Design implication |
|---|---|---|
| B2B SaaS inbound sales | Confirmed by owner | Prioritize first-response and qualification workflows |
| Small team, 5–20 commercial users | Assumption | Single-business pilot; modest concurrency |
| CSV first, pilot data access unknown | Assumption pending answer | Synthetic-only demonstration until data approval |
| Approximately 10,000 leads, 100,000 interactions, 200 approved documents | Planning workload assumption | Load-test envelope; not customer evidence |
| English, one reporting timezone, one currency per pilot | Assumption | Preserve UTC source times; no currency aggregation without conversion policy |
| Provider-neutral, hosted model allowed for synthetic data | Proposal | Real data requires separate provider/privacy review |
| $100/month demo operations ceiling | Provisional budget target | Includes hosting/model usage; excludes engineering labor; no price estimate asserted |
| 30-day qualification outcome, 90-day revenue follow-up | Proposed business definitions | Owner must align with actual sales cycle before pilot |
| Team-wide access to approved internal sales documents | Assumption | Add finer document scopes before restricted material is admitted |

All numerical quality, latency, cost, and impact targets in this pack are **proposed acceptance criteria**, not measured results. No ROI, model accuracy, runtime benchmark, or user adoption has been measured. Synthetic outcomes demonstrate plumbing and evaluation mechanics only.

## Approval and remaining decisions

The owner approved proceeding according to this architecture and roadmap and subsequently authorized data, offline intelligence, and bounded AI workflows. Those increments are implemented under the guides above. Pilot data availability and mandatory hosting/provider/residency/budget constraints remain unresolved; real-data admission, live evaluation and external delivery remain deferred.

## Evidence and references

Official technical references were checked on 2026-10-16 and are linked beside relevant decisions. They substantiate component capabilities and design considerations; they do not substantiate RevenueOS performance. Exact supported dependency versions and provider pricing must be selected and locked during implementation.
