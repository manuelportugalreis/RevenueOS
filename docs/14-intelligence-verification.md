# Intelligence increment: executed results and remaining gates

Date: 2026-10-16, America/Phoenix. Owner authorized scoring, conditional predictive modeling, retrieval/citations, structured LLM recommendations, comparison datasets, failure handling and cost tracking. The owner explicitly chose **offline execution** for this increment.

## Delivered and preserved

The prior data foundation was inspected and its 52-test suite rerun successfully before changes. Existing CSV contracts, data fixtures, migrations 0001–0003, analytics, and planning artifacts were preserved. Added:

- Versioned explainable points baseline with component evidence, configuration hash, missingness/exclusion reasons, snapshot as-of enforcement, and FIFO/newest/random comparators.
- A persisted score history and a reproducible predictive-data readiness audit. No classifier, probability model, accuracy number, or synthetic-to-real performance claim was added.
- Stewarded, versioned SQL document retrieval with exact citations, membership scopes, validity/current-version filters, revocation, and explicit metadata conflict detection.
- Typed recommendation output, strict complete-passage validation, controlled outreach phrases, pre/post-call checks, pending-review state, and no external-message capability.
- An opt-in OpenAI Responses adapter tested through fake transports, default deterministic templates, and a clearly labeled scripted test provider. The CLI offers templates/scripted fixtures only.
- Atomic monthly forecast reservations and attempt-level usage/cost/failure records. Unknown usage retains funds instead of being counted as zero cost.
- Nineteen synthetic source documents, 100 grouped dev/test knowledge cases, 15 documented fault scenarios, offline comparison tooling, CLI commands, and implementation/operating documentation.

Migration 0004 adds eight tables, taking the schema to 21 application tables and two views. Migration reversal and re-upgrade were exercised in the regression suite. No new third-party package dependency was necessary; existing SQLAlchemy, Alembic and Pydantic plus standard-library HTTPS cover this increment.

## Executed engineering checks

| Check | Observed result |
|---|---|
| Final full regression suite, actual PostgreSQL 18.6 | **109 passed; zero failed, errors or skips; 60.40 seconds** |
| Ruff lint | Passed |
| Ruff format check | Passed, 28 Python files in src/migrations/tests |
| Strict mypy on source | Passed, 12 source files |
| Dependency consistency | pip check passed |
| Migration downgrade/re-upgrade | Passed; 21 application tables/two views restored |
| New operator CLI commands | Manually executed against an isolated synthetic demo; score, readiness, seed-knowledge, search, citation, template/scripted recommendations, dev/test evaluations |
| Scoring output | 1,000 source explanations persisted/exported; 680 queue-eligible leads |
| Offline failure exports | Fabricated citation rejected; timeout retained unknown-usage reservation |

Tests exercise score arithmetic, seven-day/24-hour/30-day boundaries, missing/automated activity, exclusions, unsupported as-of requests, stable queue membership, exact Unicode offsets, document immutability, scope denial, draft/expired/revoked filtering, citation revocation, conflicts, reader publish denial, strict provider contracts, unsupported claims/negation omission, fabricated IDs, wrong leads, extra send commands, personalization errors, bounded retry, refusal/timeout/missing usage/model mismatch, budget denial/concurrency, suppression during a call, stored-draft actor/expiry checks, and invalidation by a newer CRM snapshot. Fixture split/provenance/hash/regeneration and the development harness are also tested.

During an incremental knowledge test run, two assertions incorrectly expected zero lexical results when a restricted/expired document was hidden. OR search legitimately returned other authorized documents sharing words. The tests were corrected to assert that the protected document IDs never appeared; the unrelated matches remain visible as a recommendation-relevance limitation. The final suite contains no skipped or unresolved failing tests. Passing these tests does not imply the quality targets below passed.

## Predictive modeling decision

The available 1,000-lead snapshot contains 941 synthetic outcome records, 703 complete observation windows and 127 dated positives among complete windows. All 1,000 current lead records were updated after their creation time. There is no independently observed real-business label set or reconstructable initial-scoring feature history.

**Decision: retain the transparent baseline; predictive training is unsupported.** The audit returns model_training_allowed=false and predictive_accuracy=null. The future time/account-disjoint holdout and promotion requirements are described in the implementation guide. They have not been satisfied or simulated into a success claim.

## Queue comparison at capacity K=20

These are descriptive compositions of the same synthetic current snapshot, not a predictive test or evidence of business lift. Different queues have different label coverage, and current status affects eligibility.

| Queue | Selected | Complete synthetic outcomes | Positive synthetic outcomes among those | Overlap with rules top 20 |
|---|---:|---:|---:|---:|
| Explained rules | 20 | 20 | 4 | 20 |
| FIFO | 20 | 17 | 5 | 2 |
| Newest first | 20 | 0 | 0 | 0 |
| Seed-42 random | 20 | 12 | 3 | 0 |

There is no demonstrated predictive or commercial advantage for rules over FIFO. Ranking all 1,000 leads took about 2.19 seconds in the test evaluation and 2.95 seconds in the development run on this local environment. Those single-run observations are not load tests or an API SLO.

## Frozen synthetic knowledge comparison

The fixture was authored before the evaluations and assigned by family: 60 dev cases/12 families, 40 test cases/eight disjoint families. Five variants per family are correlated. The same corpus is used across splits. Labels are agent-authored and have not been independently reviewed. The test split was evaluated separately after the development run; retrieval/recommendation behavior was not tuned on its results.

| Method | Dev relevant passage Recall@5 | Test relevant passage Recall@5 |
|---|---:|---:|
| Title-keyword baseline | 3/25 (12%) | 4/15 (26.7%) |
| PostgreSQL full-text | 25/25 (100%) | 15/15 (100%) |

The ≥90% synthetic retrieval target was met on these fixed cases. Each gold answerable document has one passage, so document and passage hits coincide for this fixture only. This establishes fixture retrieval behavior, not real-corpus quality or predictive accuracy. The JSON includes descriptive intervals explicitly caveated for family correlation.

| Recommendation measure | Dev | Test | Proposed gate |
|---|---:|---:|---|
| Correct abstention on cases requiring it | 29/35 (82.9%) | 25/25 (100%) | ≥95% |
| False abstention on answerable cases | 5/25 (20%) | 4/15 (26.7%) | ≤10% |
| Relevant completed answers | 20/25 | 11/15 | Report alongside coverage |

**The recommendation quality gate fails.** The pipeline remains an offline demonstration. All results were retained, including six dev cases that produced a reviewable but incomplete/irrelevant extract where the fixture expected abstention. No exact price was fabricated: the current billing paragraph was insufficient to answer an exact-price query. Expired-source queries sometimes returned a different authorized billing paragraph; this was not an expired-document disclosure.

The four answerable test cases incorrectly abstained were integrations-4 (unsafe_source), export-5, deployment-1 and deployment-5 (conflicting_sources). Broad OR retrieval pulled related words from instruction notes or unrelated policy conflicts into the candidate set. Checking every candidate conservatively stopped otherwise answerable requests. Retrieval recall therefore looks stronger than recommendation usefulness. Improve evidence selection/relevance on dev data and obtain a new hidden, independently labeled challenge set before claiming a new release gate.

The scripted provider intentionally copies the template. Its semantic results match the template by construction. This does not demonstrate an LLM advantage. It verifies the additional provider/schema/validation/accounting path only.

## Latency and cost evidence

On the fixed 40-case test execution, local retrieval p95 was about 16.75 ms for full text and 16 ms for title-only search. Workflow p95 was about 78 ms for the template and 125 ms for scripted fixtures. Cases were run serially on a local synthetic environment while other verification could share the machine. No provider/network latency or production capacity claim follows.

No external model calls occurred. Actual model invoice cost and live token counts are **not measured**. The scripted test uses fictional 500-input/180-output token counts and fictional rates of 0.5/2 USD per million. Its bookkeeping estimate is 0.00061000 USD per scripted attempt. Development used 26 scripted attempts (0.01586000 simulated USD); the frozen test used 11 (0.00671000 simulated USD). Template runs created no model attempts. These figures exclude local compute/hosting and are not provider prices or incurred bills.

Separate exported failures demonstrate two important accounting paths:

- A fabricated citation failed both allowed attempts. Both simulated attempt estimates, 0.00061000 each, were recorded with schema/evidence failure outcomes.
- A scripted timeout returned no usage. The ledger records cost=null, usage_unknown, and retains its 0.00536400 USD forecast reservation. It is not reported as a free call. In attempt exports reserved_usd is the original reservation; state distinguishes reconciled attempts from reservations still held in the monthly budget.

The live adapter's transport contract, refusals, incomplete envelopes and enablement guard were tested with injected fake transports. Actual OpenAI HTTP behavior, credentials, model availability, live pricing, quality, latency, cost and reliability remain unverified by explicit offline scope.

## Remaining risks and next steps

1. **Quality:** reduce irrelevant/conflicting candidate contamination and improve answerability on development cases; independently review the corpus/cases and acquire a new hidden challenge set. Do not deploy recommendation generation as production-ready while the gate fails.
2. **Prediction:** collect authorized real mature outcomes and features known before those outcomes; lock a leakage-safe time/account holdout before fitting or claiming accuracy.
3. **Governance:** add authenticated server identities, production runtime roles/RLS, reviewed knowledge approval, erasure/retention, and backup/restore before real business data. The local synthetic operator tool is not multi-tenant production security.
4. **Cost:** add trusted manual/invoice reconciliation for unknown reservations; validate a real provider/model/rate/budget only under a future live-evaluation instruction.
5. **Operations:** optimize the per-lead context query pattern when adding the API; execute supplied Docker/hosted CI and scale tests. Their execution remains unverified here.

All current source is still uncommitted; no remote push, hosted deployment, external outreach, real-data processing, measured ROI, or predictive accuracy is claimed. The temporary loopback-only PostgreSQL process is stopped after verification; its ignored synthetic test/demo data remains available for restarting locally.
