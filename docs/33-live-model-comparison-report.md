# Actual free-tier LLM comparison: no demonstrated uplift

2026-10-17. The owner explicitly confirmed Google AI Studio **Free Tier with no linked billing account**. This is an operator attestation, not a billing API verification. No billing setting, paid service, automatic fallback or external messaging was enabled. The public site remains a recorded interactive replay and never receives the API key.

## Design and evidence

The experiment uses 24 newly authored questions in 12 related families, one eligible synthetic lead, the same scoped approved corpus, fixed evidence time, focused evidence selector and strict local validator in both arms. The extractive prompt/schema and policy were frozen before the prospective execution. One seeded-order repetition compares direct templates with `gemini-3.5-flash-lite`, minimal thinking, a 1,500-output-token bound and one attempt per task. The provider has no tools. Calls are paced at 15 seconds outside individual workflow timers.

These are project-authored synthetic diagnostics, **not independent human labels or held-out predictive accuracy**. Some conservative refusal labels may admit valid grounded negative answers; independent adjudication is required. Original questions, labels and failures were preserved instead of tuned after inspection. The earlier 99/100 result uses a different exposed set and is not a controlled comparison with these 24 tasks.

Raw evidence: `outputs/prospective/free-gemini-run-2/attempts.jsonl` and `report.json`; published UI aggregate: `data/dashboard/prospective-evaluation.json`. A regression test verifies the aggregate against raw task outcomes and report hashes. The model's incremental contribution is measured only within this restrictive extractive contract, not free-form sales writing.

## Results on all assigned tasks

| Metric | Focused template | Gemini-assisted workflow |
|---|---:|---:|
| Assigned tasks | 24 | 24 |
| Fixture task successes, provisional labels | 17 | 14 |
| Relevant accepted completions / answerable tasks | 8/9 | 5/9 |
| Correct refusals / expected-refusal tasks | 9/15 | 9/15 |
| False abstentions | 1 | 1 |
| Completions marked inappropriate by authored labels | 6 | 0 |
| Local validation failures | 0 | 9 |
| Actual model generation calls | 0 | 14 |
| Mean workflow software latency | 22.7 ms | 994.9 ms |

All 14 model requests returned completed generations and accounted usage. Five generations passed the local validator; nine failed its combined schema/evidence/policy checks. Ten of the 24 model-arm tasks abstained before inference, so those ten do not demonstrate model refusal ability. Failures remain in assigned denominators; they are not discarded or credited as successful abstentions. The paired task-success difference is **-12.5 percentage points**, descriptive family-bootstrap interval **-25 to 0**, conditional on this provisional fixture set. This is not population inference or proof that LLMs generally cannot help.

No unsupported completion passed the validator. That does **not** establish a zero hallucination rate: rejected raw model text was not retained, and the combined validation code does not distinguish exact rejection causes. Rejected outputs cannot be retrospectively classified as hallucinations versus formatting/action-contract errors. The next experiment needs a clearly marked synthetic-only rejection quarantine or granular validation categories, frozen before its execution. Do not invent explanations for those nine failures.

The lower count of accepted inappropriate completions comes with nine hard failures and lower task success. It is not a demonstrated business improvement. Both arms fail the configured prospective abstention gates. Neither is cleared for client use. Pipeline latency includes pre-provider refusals; the mean actual API-attempt latency was 1,642.8 ms over 14 requests. Quota pacing is excluded from those per-task/API timings. No human preparation, reading, review or rework time was measured.

## Tokens, availability and zero-budget boundaries

Observed accounted usage: **7,280 input tokens and 3,207 output tokens including reported thought usage**. All 14 attempt records were accounted; no unknown usage was reported in this successful run. The explicitly attested free-tier price card estimates provider charges at USD 0. **Actual invoice remains null**, because no invoice was inspected. The software cannot establish account entitlement from an API key, which is why the owner's no-billing confirmation was required before transport calls. See [official pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite) and [billing status guidance](https://ai.google.dev/gemini-api/docs/billing#verify-billing-status).

Availability failures are preserved separately. The initially documented 2.5 Flash-Lite endpoint returned HTTP 404 for new users and the experiment halted after one request. A separate minimal plumbing probe returned the same diagnostic and recommended 3.5 Flash-Lite. An authenticated catalog read confirmed that model, and its free-tier pricing was checked before an explicit availability correction. There was no automatic fallback. Across both failed requests and the successful run there were **16 generation-endpoint requests**, within the announced ceiling of 24, plus one non-generation catalog read. The failed run's zero task successes describe infrastructure availability, not model accuracy. See `outputs/prospective/availability-check.json` and the preserved `free-gemini-run-1/` folder.

The API key remains in ignored local configuration and is absent from Git, the public browser build and CI. The free-tier experiment is operator-only CLI work; the default web workflow remains deterministic. No ongoing public inference spending is exposed.

## Decision and next milestone

**Keep the template as the default.** Actual LLM transport and token accounting are now demonstrated, but the model did not improve assigned task success in this experiment. The engineering outcome is a measured negative result with fail-closed validation, not a performance claim manufactured by choosing a weak baseline.

The shuffled review packet contains 48 task-arm rows with empty human relevance, grounding, review-time and edit-time fields. Its coordinator key is separate. No independent review, customer company, pilot result or realized ROI has been fabricated. Next: independent label adjudication, a new development set for granular validation/prompt-contract work, then an independently authored frozen evaluation set. Any subsequent prompt changes require a new version and a new report, retaining this result.

## Public-access verification

The demo is available at https://manuelportugalreis.com/RevenueOS/ (the canonical GitHub Pages URL redirects there). Hosted verification for the public increment passed 218 Python/PostgreSQL tests, two authenticated backend browser journeys, two public replay journeys, Ruff, mypy, production/showcase builds and Docker build. Two additional browser journeys exercised the actual deployed HTTPS site. The recorded comparison and aggregate are now also displayed under Evaluation, with provisional-label and no-uplift disclosures. Current CI identifies the exact subsequent publication commit; earlier reports retain their own source hashes and environments.
