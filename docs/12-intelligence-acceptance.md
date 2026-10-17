# Intelligence increment: inspection and acceptance criteria

Date: 2026-10-16. Owner authorizes explainable lead priority, conditional predictive modeling, cited retrieval, structured LLM recommendations, baseline comparisons, failure cases, and cost tracking.

## Inspection and dependencies before coding

The repository contains the previous deterministic data foundation: Python 3.12, PostgreSQL, SQLAlchemy Core, Alembic, Pydantic, a CLI, synthetic full-export snapshots, and a prior report of 52 passing tests. All repository files are currently uncommitted; preserve them. No applicable AGENTS.md was found. Existing migration and fixture tests must keep passing. No document corpus, score engine, LLM adapter, model credential, or real-business labeled dataset exists.

Use the existing dependencies and Python standard-library HTTPS for an optional provider adapter. PostgreSQL full-text search supplies lexical retrieval; no vector database, embeddings, orchestration framework, or ML dependency is justified for the available data. The provider adapter follows the official OpenAI Responses structured-output contract checked on 2026-10-16. No key-discovery tool is available and no provider key environment variable is configured. Offline tests must never call a real provider.

## Data-readiness decision

Available CRM data is explicitly synthetic; the demo is one observed full-export snapshot, plus a separate small edge fixture. Labels were simulated and current attributes include post-creation updates. There is no independently observed business outcome cohort with reconstructable pre-outcome features. A predictive model is **not supported**. Implement a reproducible readiness audit that records counts, maturity/missingness, provenance, snapshot coverage, and rejection reasons. Do not fit a model or report synthetic ranking agreement as predictive accuracy. Future promotion requires mature real labels, frozen time/account-disjoint holdout, leakage-safe features, calibration if probabilities are shown, and improvement over operational baselines with uncertainty.

## Small verifiable increments

1. **Explainable scoring:** versioned rules and configuration; source references/as-of timestamps; point contributions, exclusions, missing-feature warnings; deterministic ties; comparable FIFO/newest-first/random queues. Contact tracking is incomplete, so the overdue/no-response bonus stays disabled unless explicitly attested. The current CRM contract lacks declared use-case match, so its contribution stays zero with a warning. No invented feature values.
2. **Knowledge:** a clearly synthetic steward-approved corpus; immutable document versions/chunks and exact offsets/hashes; lexical search and simple title/keyword comparator; scope, validity, approval, revocation filters before evidence leaves the service; citations resolve to exact authorized passages. Conflicting topic versions abstain. No external URLs supplied by the model.
3. **Recommendations and cost:** strict structured output, claim-to-evidence allowlists, bounded inputs/outputs, at most two attempts, explicit human-review requirement, no external delivery tools. Add a real opt-in Responses adapter plus deterministic template and scripted-fixture providers with distinct evidence labels. Fail closed on missing evidence, unavailable provider, fabricated citations, unsupported text, invalid schema, suppression/revocation, and budget exhaustion. Persist run/version/usage/cost/failure metadata and conservatively reserve spend before calls. Unknown provider usage never means free.
4. **Evaluation:** deterministic case files and pinned hashes, dev/test split with repeated-template families kept together, hand-computed score fixtures, same-case baseline retrieval/recommendation comparisons, adversarial cases, and separate latency/cost observations. Do not call an agent-authored fixture set independently human-labeled or a valid business predictive holdout. Export counts, failures, and unverified gates. Live-model and independent-review gates remain pending without credentials/reviewers.

## Release acceptance for this increment

- Existing regression suite passes against actual PostgreSQL; new migrations round-trip.
- Scoring contributions and ordering match hand-computed cases, including suppression, stale data, missingness, seven-day/30-day boundaries, and future as-of rejection.
- Every returned citation resolves to the exact approved, current, authorized chunk; invalid IDs/quotes and revoked/restricted/foreign evidence fail tests.
- Every surfaced factual product claim is an exact supported extract in this conservative first release. Freeform paraphrase/draft content fails validation rather than relying on a semantic judge. This restricts expressiveness; human review remains required.
- Retry, provider refusal/timeout/malformed output, current suppression, spend reservation/reconciliation, concurrent budget limits, and unknown usage have meaningful tests.
- Fixed synthetic retrieval Recall@5 target ≥90%; report actual counts and failures, including if the target is missed. Structural validation and safety tests have zero accepted unsafe outputs in the defined suite. These do not establish live LLM groundedness or production security.
- Cost/latency reports distinguish deterministic local execution, scripted fixture simulation, configured-price estimates, and actual billed/live measurements. No predictive accuracy, live-model quality, ROI, or invoice-cost claim without the required evidence.

Deployment remains a local synthetic operator workflow. Authentication, multi-tenant readiness, production RLS, and real-data admission remain separate gates. The previous no-AI instruction is superseded for this authorized increment; external messaging remains prohibited.
