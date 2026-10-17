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


---

# Explainable priority, cited retrieval, and offline recommendations

This increment follows the owner's approved scope and explicit decision to remain offline. It adds rules-based attention priority, a predictive-data readiness audit, approved-document lexical retrieval, an optional structured LLM provider boundary, conservative draft validation, and evaluation/cost ledgers. No predictive model was trained. No real model API was called.

## Decisions and simpler alternatives

| Choice | Why it fits the available evidence | Simpler alternative / tradeoff |
|---|---|---|
| Transparent points baseline | Works without reliable business labels; each contribution is inspectable and versioned | FIFO is simpler and remains a comparator; no measured commercial superiority is asserted |
| Keep ML gated off | Synthetic current-state exports cannot establish historical predictive accuracy | An arbitrary classifier would be easy to fit but would give misleading evidence; retain rules until real data supports a valid test |
| Preserve current CSV contracts | Avoid inventing use-case fit or contact-completeness fields | Extend the CRM contract later if a pilot business can supply audited observations |
| PostgreSQL full-text search | Reuses the existing store; approval/scope/version checks stay next to content | Title-keyword search is the baseline; embeddings add expense and are deferred until semantic failures justify them |
| Exact paragraph citations | Stable IDs, version, character offsets, text hash, title, and heading can be verified mechanically | Document-title links are easier but cannot establish the exact supporting passage |
| Explicit claim metadata for conflict checks | Detects conflicting values for a steward-declared policy key without pretending to solve semantic contradiction | Manually resolving conflicts before publication is simpler and remains necessary for undeclared contradictions |
| Controlled extractive recommendations | Factual text must equal the entire approved passage; negation omission and novel claims can be rejected exactly | Templates are the default; free paraphrasing needs independent semantic evaluation before admission |
| Pydantic output contracts and a small provider protocol | Strict types, enums, evidence constraints, and bounded retry avoid an orchestration framework | Templates alone are cheaper; an SDK would simplify API parsing but adds a dependency and its own retry behavior |
| Optional standard-library OpenAI Responses adapter | Fixed HTTPS endpoint, no redirects, store=false, tools=[], explicit model/key/enablement, no hidden retries | A fixed template has no external cost/privacy boundary; the adapter remains opt-in and was tested through fake transports only |
| Database usage ledger and reservations | Failed/invalid attempts cost money too; concurrent requests must not spend the same forecast allowance | A log-only counter is simpler but races and can omit failures |
| Grouped, frozen synthetic evaluation | Exposes failure patterns before a pilot and separates development from test cases | A small ad hoc demo is faster but cannot support repeatable comparisons |

Official references checked for implementation: [PostgreSQL text search and ranking](https://www.postgresql.org/docs/current/textsearch-controls.html), [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses), and [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html). OpenAI Docs informed the optional adapter; no provider quality, price, or availability was inferred from documentation.

## Scoring contract

`scoring.py` loads only scoped snapshot CRM attributes, coarse firmographics, lawful-use status, and human interaction metadata. Names, emails, freeform notes, opportunity outcomes, and label tables do not enter the scoring or model context. An exact snapshot observation time is required; earlier/future as-of requests are rejected because this export cannot reconstruct them. Stable IDs and source interaction IDs are included in the explanation.

Ruleset `attention_v1` proposes target employee bands 11–50 and 51–200 as an explicit configuration assumption, not a measured ideal customer profile:

| Component | Points | Required evidence |
|---|---|---|
| Explicit demo request | +30 | Controlled CRM acquisition source |
| Human inbound interaction within seven days | +20 | Recorded human inbound interaction; day-seven boundary inclusive |
| Target company size | +15 | Known employee band matching the versioned config |
| Declared use-case match | 0 in this increment | Not present in CRM v1; warning explains missingness |
| Unanswered over 24 hours | +10, disabled by default | Full contact coverage from lead creation plus explicit attestation; strictly over 24 hours |
| No meaningful activity over 30 days | −15, disabled by default | Same attested coverage; strictly over 30 days |

Clamp eligible point sums to 0–100. Exclude test/internal, disqualified, deleted, do-not-contact, and currently tombstoned leads; excluded final points are zero even if components describe source facts. Unknown company size contributes zero. Unknown/blocked lawful use prevents drafting even though its lead can remain in the attention queue for internal review. Current tombstones can exclude a lead from an old snapshot for safety; this is a deliberate current-policy overlay, not an immutable historical eligibility assertion.

Rules queue ties use oldest known unanswered inbound/acquisition timestamp, then stable lead ID. FIFO, newest-first, and seed-42 random queues use the exact same eligible population. The initial comparison reports top-K membership, label availability, and synthetic outcome composition. It does not calculate predictive accuracy or claim that the rules beat FIFO. Config hash, rules version, as-of, source references, components, exclusions, and warnings are persisted when `score --persist` is used.

## Predictive readiness and future promotion protocol

The 1,000-lead export has 941 outcome rows, 703 complete windows, and 127 dated positive outcomes among complete windows. All 1,000 lead records were updated after creation. Both the labels and source entities are synthetic, and only one snapshot is available per demo business. The audit therefore returns model_training_allowed=false and predictive_accuracy=null.

No scikit-learn dependency or dormant untested training pipeline was added. A future predictive increment requires a sponsor-defined scoring instant and 30-day outcome, authorized real data, independently audited labels, complete maturity windows, feature availability at the scoring instant, and enough observations for useful intervals. Split chronologically with a 30-day maturation/embargo gap and account-disjoint train/validation/test groups, purging overlaps. Fit preprocessing only on training data. Select features, model, hyperparameters, calibration, K, and decision thresholds on training/validation; freeze the final holdout before examining it. Compare regularized logistic regression with FIFO, actual routing, and rules using precision/recall@K, PR-AUC and account-cluster intervals; evaluate Brier/reliability if probabilities are shown. Retain rules if a valid test does not demonstrate useful improvement. The 1,000-window/100-positive count screen is a heuristic, never permission to skip these controls.

## Knowledge, permissions, and citations

Migration `0004` adds eight tables: knowledge_memberships, documents, document_versions, document_chunks, score_runs, ai_budgets, ai_runs, and ai_attempts. Total application tables: 21. Existing data migrations are preserved; only the migration round-trip test's expected schema inventory and table-reset fixture changed.

Synthetic fixture seeding creates a local steward (`22222222-2222-4222-8222-222222222222`) and reader (`33333333-3333-4333-8333-333333333333`). Scope membership lives in PostgreSQL. Readers cannot publish; stewards cannot publish outside assigned scopes. The seed command is a trusted local operator action restricted to synthetic organizations. Selecting an actor UUID in a CLI is not identity authentication, and this must not be exposed as a web authorization mechanism without OIDC and server-derived identity.

The corpus has 19 synthetic documents. It deliberately includes approved content, unapproved drafts, expired/revoked documents, a management-only document, two declared conflicting policy pairs, and three injection notes. Approval metadata is a synthetic workflow fixture, not evidence that an independent human reviewed these claims. In real operation a steward must verify both the content and outreach_allowed flag before publication.

Documents are UTF-8 text/Markdown, bounded to 256 KiB, and split into non-overlapping paragraphs up to 1,600 characters. Offsets are Unicode character indices, not byte offsets. Search uses English PostgreSQL lexemes, server-built OR terms, title/body weights, a GIN index, and deterministic ID ties. The title-keyword comparator searches only titles with the same scope filters. Query length and result count are bounded.

Only current approved, unexpired, unrevoked, authorized versions are returned. A newer approved version supersedes older ones even if it later expires or is revoked; there is no silent fallback to an older claim. Re-ingesting an identical version is idempotent; changing the same version's content or policy metadata fails. Draft-to-approval edits are deliberately not implemented: publish a new approved version. Content/chunks have mutation guards; revocation is the allowed metadata transition.

Citations return document/version/chunk IDs, exact text, title/heading, offsets, and hash. Resolving a citation rechecks access and freshness and verifies the excerpt against immutable document content. The model cannot supply a new citation URL or query another organization. Metadata conflicts are checked across authorized current versions for the retrieved policy keys. Unlabeled semantic contradictions still require stewardship/review.

## Recommendation and review boundary

The workflow loads a scoped lead and explained score, retrieves at most five evidence chunks, checks current suppression/lawful use and known source conflicts/instruction patterns, then uses a template or an injected provider. Source-instruction matching is a limited heuristic; it is not a complete prompt-injection defense. The authority boundary is enforced by no provider tools, no arbitrary SQL/URL/recipient fields, exact evidence validation, and no delivery adapter.

Output contains schema_version, lead_id, controlled action, exact cited rationale claims, missing-information enums, risk flags, nullable controlled draft, and an abstention reason. All schema fields are required, with nullable fields explicit. Pydantic validation is stricter than the reduced provider JSON-schema subset. A claim must copy the entire outreach-approved chunk as both text and quote. Quoting only a favorable phrase, omitting negation, invented pricing, wrong lead IDs, extra send commands, unknown evidence, or unsupported demo personalization fail. Greeting/subject/closing phrases are controlled; no personal contact details are sent to the provider.

Valid proposals are review_pending, human_review_required=true, approved=false, delivery_available=false. There is no approve/send command in this increment. A reviewer must inspect the evidence and text before manual use outside the application. Opening a stored proposal rechecks its requesting actor, active membership, current dataset, lead eligibility/lawful use, source citations/conflicts, and 24-hour expiry. New CRM snapshots, source revocation, suppression, or scope loss can make it unavailable. Rechecks also run before a provider call and before returning generated content.

Generation has at most two total attempts and a 30-second workflow deadline, with a maximum 10-second individual transport timeout. There are no SDK/transport retries beneath this budget. Malformed/invalid known-usage results may consume the second attempt. Unknown usage, refusal, model/price mismatch, exhausted budget, or policy change fail safely; uncertain usage is not retried automatically. A future async service must also bound connection/database waiting to meet a hard end-to-end SLO; this local operator implementation is not a real-time deployment guarantee.

## Usage and cost accounting

PriceCard requires a model, explicit rate version, and input/output USD-per-million rates. No default live model or live price is guessed. Each attempt atomically reserves forecast cost under the organization/month budget before invoking the provider. Its estimate uses the UTF-8 request size plus a framing allowance and output cap, not a measured tokenizer count. Store usage, model, rate version/rates, attempt latency, validation outcome, response ID, and cost evidence class; exclude raw prompts from the cost ledger.

Known matching-model usage reconciles the reservation into a configured-rate estimate, including failed/refused/invalid outputs. Fixture counts/rates are marked fixture_simulated. Unknown usage, a transport failure, or a model mismatch retains the reservation and records null cost; it is never recorded as a free call. A process crash after reservation likewise leaves inspectable reserved work. A steward must resolve uncertain billing before funds are released; automatic invoice reconciliation/refunds are not implemented.

Reservations protect concurrent forecast allowances, not arbitrary provider billing behavior. If reported usage exceeds the forecast/output bound the run fails and the observed configured estimate remains recorded; subsequent requests respect the increased spend. Rates can change and cached/tier discounts are not modeled, so configured estimates are not invoice cost. The offline evaluation's 0.5/2 USD-per-million rates and 500/180 token counts are deliberately fictional test inputs. Template execution has no model attempt; local compute/hosting costs were not measured.

## Evaluation evidence and known quality failures

The corpus/cases are agent-authored and agent-labeled, not independently human annotated. There are 100 query variants in 20 families: 60 dev cases/12 families and 40 test cases/eight disjoint families. Categories are answerable, unanswerable, conflict, injection, and restricted/expired/revoked. Five variants from one family are correlated; percentages are descriptive on this fixture. Wilson intervals in JSON are explicitly descriptive and do not establish population confidence under independent sampling. Gold answerable documents each have one relevant paragraph, so document hits equal passage hits for this fixture only.

Fifteen fault scenarios describe fabricated IDs, unsupported/negation-omitting claims, wrong leads, send commands, malformed output/retry, timeouts, missing usage, refusals, model mismatches, denied/concurrent budgets, revocation, and suppression during a call. Automated tests exercise these boundaries. Independent human groundedness, tone/usefulness, and factual-context adjudication remain pending.

The scripted provider deliberately produces the same content as the template. It tests provider/schema/budget plumbing and cannot establish LLM semantic quality, relative capability, real token usage, live latency, or financial cost. Both frozen comparison reports retain failed gates. High retrieval recall does not imply answerability or useful recommendations: broad OR retrieval can pull unrelated conflicts/instruction notes into a candidate set, causing excessive abstention. Conversely, a safe verbatim billing paragraph can be irrelevant/incomplete for an exact-price question. That is an answerability failure, not fabricated pricing or an expired-document access leak.

Do not tune this implementation on the exposed test cases and continue calling them a fresh holdout. Develop a relevance/evidence-selection fix on dev data, then obtain independent labels and a new hidden challenge set before a new release claim.

## Run the offline increment

Install the existing dependency lock and migrate the database with the root README commands. Import the seeded 1,000-lead bundle in a fresh synthetic database (one snapshot per organization/source observation time). Use its returned dataset UUID:

```powershell
python -m revenueos.cli readiness --organization 11111111-1111-4111-8111-111111111111 --dataset DATASET_UUID
python -m revenueos.cli score --organization 11111111-1111-4111-8111-111111111111 --dataset DATASET_UUID --persist
python -m revenueos.cli seed-knowledge --organization 11111111-1111-4111-8111-111111111111
python -m revenueos.cli search --organization 11111111-1111-4111-8111-111111111111 --actor 33333333-3333-4333-8333-333333333333 --query "configuration checklist"
python -m revenueos.cli citation --organization 11111111-1111-4111-8111-111111111111 --actor 33333333-3333-4333-8333-333333333333 --chunk CHUNK_UUID
python -m revenueos.cli recommend --organization 11111111-1111-4111-8111-111111111111 --dataset DATASET_UUID --actor 33333333-3333-4333-8333-333333333333 --lead ELIGIBLE_LEAD_UUID --query "configuration checklist"
python -m revenueos.cli intelligence-eval --organization 11111111-1111-4111-8111-111111111111 --dataset DATASET_UUID --split dev --output outputs/dev-evaluation.json
python -m revenueos.cli intelligence-eval --organization 11111111-1111-4111-8111-111111111111 --dataset DATASET_UUID --split test --output outputs/test-evaluation.json
```

Use `--rules-config CONFIG.json` for an explicitly versioned RulesConfig. The default template requires no model budget. A scripted-fixture recommendation requires a synthetic monthly budget; the offline evaluator initializes a 10 USD **simulated allowance**. The library's configure_budget function requires a local steward. No CLI live-provider option exists in this offline increment.

Rebuild fixture files with `python scripts/build_intelligence_fixtures.py --output DIRECTORY`. Run `pytest --require-db` against the dedicated local revenueos_test database plus Ruff/mypy checks. Ordinary CI never uses model credentials. Before a future live evaluation, obtain explicit provider/model/rate/budget approval, configure environment credentials without sharing them in chat, create a matching PriceCard, and deliberately enable the optional adapter. That execution remains unverified here.

## Remaining release gates

The recommendation false-abstention gate is not met; live-model quality and independent human review are unmeasured. Real-data admission, authenticated server identities, production DB roles/RLS, privacy deletion/retention, backup/restore, hosted CI, container execution, and scale tests remain future work. Scoring currently reads each lead's context separately; bulk-query optimization should precede a production high-volume API. There is no claim of revenue lift, predictive accuracy, customer deployment, or measured ROI.
