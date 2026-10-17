# Implementation roadmap and risk register

No implementation starts until architecture approval. Durations below are rough planning assumptions for one engineer with timely business feedback, not commitments. Each phase ends in a reviewable artifact and a go/no-go gate. Discovery and pilot access can lengthen the schedule independently of coding.

## Phased roadmap

| Phase | Indicative effort | Deliverable and acceptance | Dependencies |
|---|---|---|---|
| 0. Approve scope and definitions | 2–3 working days | Owner signs architecture/scope; confirm pilot segment, target outcome, data access, allowed provider, budget and known limitations | This planning pack and owner decision |
| 1. Reproducible data foundation | 4–6 days | Git setup, lockfiles, Compose, env template, initial migrations, synthetic dataset/data dictionary, CSV mapping/quarantine/idempotency; import gates pass from clean checkout | Phase 0 |
| 2. Trusted dashboard and priority queue | 4–6 days | SQL metric contracts, React UI, score components/missingness/eligibility; exact analytics/scoring fixtures; compare queues; visible synthetic/freshness markers | Phase 1; sponsor rule/metric review |
| 3. Approved knowledge and structured drafts | 5–7 days | Document stewardship/versioning, lexical retrieval, claim-linked citations, provider adapter, template comparator, validated drafts, edit/reject/approve states; unsupported answer abstains | Phase 2; approved corpus and provider for synthetic calls |
| 4. Bounded tools and evaluation gates | 4–6 days | Bounded read-tool workflow, budgets, policy tests, adversarial suite, fixed benchmark report; decision whether tools or hybrid search improve the simpler pipeline | Phase 3; reviewed evaluation cases |
| 5. Pilot hardening and portfolio release | 4–6 days | OIDC, scoped runtime role, access tests, redaction, deletion/restore drill, quota/kill switches, CI and deployment runbook; synthetic demo plus known-failures report | Phases 1–4; all safety gates pass |
| 6. Real-business pilot | 2-week readiness/baseline period + 4–6 weeks workflow experiment; revenue follow-up to ≥90 days as appropriate | Written data/sponsor authorization, locked protocol, assignments, measured time/quality/cost, intervals, sponsor go/no-go; inconclusive result acceptable | Phase 5; sponsor/users/data; power review and approved privacy/provider terms |
| 7. Evidence-led extensions | Scoped only after decision | Add supervised ML only with mature as-of data; hybrid retrieval only if lexical fails; CRM API read sync only with approved mapping/reconciliation tests | Pilot findings and explicit scope approval |

Phases 1–5 total roughly 21–31 engineering days before pilot operations, excluding phase 0 and access delays. Keep one complete slice usable at each gate. The entire proposed schema need not be built at phase 1; add evaluation, document, review, and pilot tables alongside their workflows. Authentication for a local synthetic development slice can be stubbed; phase 5 must replace it before private real data.

## Dependency and stop rules

- Missing real data does not block synthetic demonstration; it blocks real-world performance/ROI claims and may block retrospective ML.
- Missing approved sales corpus means templates and context display only; no invented knowledge base.
- Missing model budget/provider clearance means keep rules/search/templates; do not bypass privacy review.
- Any access-control, fabricated-citation acceptance, or approval-integrity failure blocks release regardless of average quality.
- If the workflow has no observed user value, revisit scope before adding features.

## Risk register

Likelihood and impact are qualitative initial assessments, not estimated probabilities. Residual risk remains after mitigations.

| ID | Risk; likelihood / impact | Owner | Mitigation and detection | Trigger, fallback, residual risk |
|---|---|---|---|---|
| R1 | Missing/dirty CRM data; high / high | RevOps | Quarantine, mapping review, completeness/freshness reports, source reconciliation | Critical field coverage <95%: repair export or exclude affected metric/rule; hidden source errors remain |
| R2 | Temporal leakage or censored labels; high / high | AI engineer | Immutable snapshots, maturity windows, grouped time split, feature audit | As-of reconstruction unavailable: no retrospective model claim; prospective evaluation only |
| R3 | Hallucinated or weakly supported sales claims; medium / high | AI engineer + steward | Source allowlist, claim checks, abstention, human evaluation | Any unsupported pricing/contract claim accepted: block generation release, template fallback; subtle entailment errors remain |
| R4 | Prompt injection or excessive tool agency; medium / high | Security owner | Untrusted-data boundary, read-only allowlist, argument validation, adversarial cases | Unauthorized action/access: kill generation, investigate; test suites cannot exhaust attacks |
| R5 | PII leakage or cross-scope retrieval; medium / high | Security owner | Minimize context, ACL/RLS tests, separate business deployments, provider approval, redaction | Any observed disclosure: isolate pilot and incident response; manual exports remain a boundary |
| R6 | Unexpected model/hosting cost; medium / medium | Technical owner | Token reservations, attempt caps, monthly ledger, user quotas | 80% of approved monthly cap: throttle; 100%: deny generation until budget review; unknown usage reconciled conservatively |
| R7 | Low adoption or excessive editing; high / high | Sales sponsor | Co-design, workflow observation, edit/reject reasons, simple evidence UI | <60% eligible-task usage over two weeks: interview users and simplify; novelty effects remain |
| R8 | Spurious ROI or underpowered experiment; high / high | Pilot analyst + sponsor | Pre-registered assignment/endpoints, intervals, observed vs simulated ledger | Required sample unavailable: feasibility-only pilot; no causal revenue claim |
| R9 | Model/provider outage or version drift; medium / medium | Technical owner | Timeouts, bounded retry, version capture, canary benchmark, templates | Error/latency gate fails: disable generation or roll back; provider version pinning may be limited |
| R10 | Stale approval, edited draft, revoked source; medium / high | Application owner | Immutable draft hash/version, transactional review, expiry and source rechecks | Any stale approval accepted: stop approvals; manual copies cannot be recalled |
| R11 | Biased prioritization or neglected segments; medium / high | RevOps + AI owner | Explain features, review proxies, segment metrics, baseline comparison, override audit | Material segment harm or coverage gap: pause scorer and use FIFO; small segments stay uncertain |
| R12 | Scope creep and fragile demo; high / medium | Product owner | Gate extensions, maintain working slice, rehearse clean setup and fallback | Milestone slips: defer semantic search/ML/API integrations first; core controls remain required |
| R13 | Incomplete deletion or failed restore; medium / high | Operations owner | Subject trace, cache purge, retention jobs, deletion ledger, restore drill | Drill fails: no real-data pilot; backup expiration delays final removal |
| R14 | Missing CRM contact telemetry or attribution; high / medium | RevOps | Distinguish draft review from outbound contact; record unknown status | No trustworthy contact events: omit first-response claims; measure in-app preparation only |

Review risks at each phase gate and weekly during pilot. Record owner, last review, evidence link, current status, and follow-up action in the evolving register.

## Portfolio evidence

Deliver a short recorded or live walkthrough, architecture/data diagrams, data dictionary, reproducible clean-start instructions, a representative import error, explainable queue comparison, cited answer and abstention, approval conflict, budget/outage fallback, evaluation report, and pilot report if available. Include a decision log explaining why a simpler mechanism was retained where experiments did not justify complexity. Never present a synthetic demo as customer deployment.
