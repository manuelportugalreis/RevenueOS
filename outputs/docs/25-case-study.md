# Engineering case study: RevenueOS

**Type:** portfolio engineering demonstration for B2B SaaS inbound RevOps. **Client:** none. **Data:** synthetic. **Business outcomes:** not measured. This case study describes implemented work and observed software evidence, not a consulting engagement or testimonial.

## Problem and product judgment

A representative inbound sales team needs to decide which leads deserve attention, reconcile CRM performance definitions, find approved product facts and prepare messages without surrendering judgment or accidentally contacting customers. A useful solution must distinguish missing activity from no activity, keep currencies and outcome maturity explicit, and make every generated recommendation inspectable.

RevenueOS starts with the smallest credible end-to-end slice: validated CSV publication, immutable CRM snapshots, SQL metrics, transparent attention points, stewarded document retrieval, strictly cited templates and version-bound human review. It deliberately retains a rules baseline because available outcomes are synthetic and features cannot be reconstructed at initial scoring time. It has no conversion probability model or measured predictive accuracy.

## Implementation and tradeoffs

The Python/PostgreSQL modular monolith preserves transactions and source lineage without microservices. React/TypeScript provides executive metrics, an explained queue, source inspection and exact-version approval. Google Workspace is the hosted identity target; signed offline OIDC tests cover cryptographic/claim failures, while real tenant enrollment remains untested. Opaque database sessions support revocation; role and source permissions are server-owned.

The tool boundary permits only four scoped reads. Extra authority arguments, SQL/network tools and approval/send requests are denied. The model cannot grant itself rights. Approved drafts have immutable recipient/message/evidence hashes and expire; edits invalidate old decisions. The web product has no delivery action. A separate synthetic operator rehearsal produces only a non-delivery receipt.

The simpler default is a fixed read pipeline plus deterministic template. A scripted provider tests schema/failure/cost handling without claiming LLM reasoning. A real provider adapter exists but remains unexercised with credentials under the owner's offline instruction. This decision makes the demo inexpensive and inspectable while avoiding invented performance claims.

## What was measured

A prespecified paired diagnostic ran 100 authored tasks twice in each arm: 400 measured attempts plus eight warm-ups. A title/template reference achieved 66/100 fixture successes; bounded lexical/template reached 85/100. The paired family-bootstrap descriptive difference was +19 points, with an interval from +3 to +36, conditional on the authored fixture. These previously seen synthetic cases do not establish client quality or a newly hidden test result.

The assisted path's nine false abstentions and six inappropriate completions keep quality promotion blocked. Mean software invocation was 202.0 ms versus 27.6 ms, with shared-machine test load and no human timing. No model attempts occurred; actual hosting/labor/invoices remain unknown. End-to-end Chromium tests separately exercised login, source-backed draft preparation, explicit reviewer approval, mobile/error behavior and logout. Approval is not a sent message.

## Failure analysis and learning

Lexical recall is insufficient as a release criterion. Broad candidates can introduce unrelated conflicts or suspicious text, causing valid questions to abstain. Conversely, an exact supported quote can be irrelevant to an exact-price question. Reporting only citation validity, an aggregate success percentage or favorable test cases would conceal those product failures.

The next investment is development-only relevance/answerability improvement, independent hidden labels, authenticated deployment/restore validation and an authorized human workflow pilot. Adding more agents, vector infrastructure or predictive models before that evidence would increase complexity without an established benefit.

## Interview claim discipline

I can demonstrate typed data contracts, SQL lineage, temporal/missingness safeguards, safe tool dispatch, exact source locators, immutable review, actual PostgreSQL/browser tests and reproducible failure reporting. I cannot claim a client deployment, real hours saved, causal revenue lift, predictive accuracy, live-model quality or realized ROI. The business case is a testable hypothesis with transparent downside scenarios.
