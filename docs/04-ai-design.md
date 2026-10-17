# AI, ML, retrieval, and bounded workflow design

## Assign each task to the simplest suitable mechanism

| Task | Proposed mechanism | Why | Simpler alternative |
|---|---|---|---|
| Validation, suppression, access, amounts, dashboard metrics | Deterministic rules and SQL | Exact definitions and enforceable constraints | CSV checks and fixed reports for a smaller prototype |
| Lead prioritization | Versioned points-based rules | Transparent with no trustworthy labels required | FIFO or newest-first queue |
| Conversion prediction, conditional | Logistic regression with regularization and calibrated probabilities if justified | Interpretable challenger on tabular data | Keep points-based scoring; no model is a valid result |
| Knowledge retrieval | Authorized PostgreSQL lexical search; semantic search only after benchmark | Approved corpus with inspectable evidence | Curated document links and keyword filtering |
| Context synthesis and wording | One evaluated LLM through a typed provider adapter | Flexible synthesis and personalized drafts | Deterministic recommendation and email templates |
| Workflow decisions | Explicit state machine; bounded LLM choice among read tools only where useful | Demonstrates tool use with server-owned authority | Fixed retrieval → generation pipeline |

## Transparent baseline

Proposed ruleset v0 is a stakeholder hypothesis, not a validated lead-quality model. First apply eligibility: disqualified, deleted, test, duplicate, and do-not-contact records cannot receive an outreach draft. Missing lawful-use status blocks real-data drafting until reviewed. Those records appear in an exception queue with reasons.

For eligible leads, sum: explicit demo request +30; recent human inbound interaction within seven days +20; confirmed target company-size band +15; confirmed target use-case match +15; no human response after 24 hours +10; no meaningful activity for over 30 days −15. Clamp total to 0–100. Use one explicit as-of instant; time-based rules use UTC elapsed time. Unknown values contribute zero and show a missing-data warning. Store each contribution, observed value, source, and ruleset version. Target company band and use-case mapping are sponsor-configured; do not let an LLM invent them.

This is an attention-priority score, combining fit and urgency. It is neither a conversion probability nor a fairness guarantee. Stable tie-break: oldest unanswered inbound timestamp, then lead ID. Compare with FIFO, newest-first, and actual business routing if available. Missing response tracking disables the overdue rule and flags it; no-data must not masquerade as slow response.

## Conditional supervised ML

Proposed label: qualification within 30 days after first inbound lead creation, with qualification defined by the sponsor's recorded CRM stage/event. Only complete follow-up windows produce negative labels. Store explicit exclusions for censored, missing, duplicate, or ambiguous cases. Lead identity and account relationships must be reconciled before splitting.

Use only facts available at the scoring instant: source, declared intent, known firmographics, and prior interactions. Exclude later stage, close outcome, post-score response, future activity counts, and overwritten current attributes. No names/emails or protected/sensitive attributes in training features; review geographic and firmographic proxies. Fit imputers/encoders inside training folds. [Scikit-learn's leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html) supports keeping test data outside fitting and preprocessing.

Use forward-time train/validation/test windows with a label-maturation gap, and group by account to avoid shared-account leakage; purge overlapping accounts or use a separate account-generalization analysis. Keep preprocessing and calibration selection inside training/validation. Freeze the final test set before tuning. Compare precision@K, recall@K, PR-AUC, and business workload with the rules baseline, reporting bootstrapped account-level intervals. For probabilities, inspect Brier score and reliability curves; calibration requires separate held-out predictions, as described in [the official calibration guide](https://scikit-learn.org/stable/modules/calibration.html).

Data readiness requires reconstructable as-of features, reliable labels, and enough mature positives/negatives for stable evaluation. A planning heuristic is at least 1,000 matured leads and 100 positives; this is not a statistical guarantee. Perform a learning-curve and interval review before proceeding. If readiness fails or the model does not beat the operational baseline, document the result and retain rules. A boosted-tree challenger is optional only after logistic regression; no deep learning or fine-tuning is justified initially.

## Retrieval and citation contract

Only a steward-approved document version is indexed. Begin with UTF-8 text/Markdown product descriptions, objection handling, pricing policies, and permitted claims. Chunk along headings, provisionally 300–600 tokens with modest overlap; store exact offsets/headings and content hashes. Tune on a development set, not the final test set.

Search filters organization, access scope, approval state, validity, and revocation before returning candidates. Begin with lexical search. If semantic retrieval demonstrates benefit, add embeddings in PostgreSQL and fuse ranks; keep embedding version/dimension and rebuild rules explicit. Exact vector search is the initial option for a small corpus. No separate vector database or reranker until measured need.

The server supplies an evidence allowlist containing immutable chunk IDs and authorized CRM snapshot references. The model may reference only those IDs. Validators reject unknown IDs, unauthorized versions, missing claim references, or quotations absent from the specified passage. Show an exact passage plus title/version/heading or page in the UI. Recheck authorization at citation open and approval. A structurally valid citation can still fail to support a claim: human-labeled groundedness evaluation remains mandatory.

Product facts require approved-document evidence. Lead facts require CRM snapshot evidence. Metrics come from registered SQL definitions. Unsupported pricing, promises, customer names, or inferred personal details cause regeneration within the shared attempt budget or abstention. No evidence means a clear request for more information, not a best guess. Conflicting documents cause abstention and a steward task. Revoked/changed sources invalidate affected pending drafts and approvals for further in-app use.

## Structured recommendations and tool permissions

Proposed output fields: `lead_id`, `action` (review/contact/qualify/hold/request_information), `rationale_claims` (text + evidence IDs), `missing_information`, `risk_flags`, `draft` (nullable subject/body), and `abstention_reason`. Do not present a self-reported model confidence number as calibrated confidence. Schema validation checks types, enums, lengths, allowed evidence, eligibility, and required fields. Separate rendering from validation; generated HTML is never trusted.

Allowed read tools are `get_lead_context(lead_id)`, `get_priority_explanation(lead_id)`, `search_approved_knowledge(query)`, and `get_metric(metric_name, fixed_filters)`. Tools use the authenticated scope, parameter allowlists, row caps, and server-side authorization. The model cannot select another organization, arbitrary URL, SQL statement, shell command, secret, or recipient. Limits are four tool calls and two generation attempts total per workflow. Tool outputs are untrusted data, including instructions embedded in CRM notes or documents.

The server stores validated output as a proposal through ordinary application logic, not a model-authorized write tool. Human review binds a reviewer, immutable draft version, content hash, current evidence, eligibility, and expiry (proposed 24 hours). Editing, source revocation, suppression, or lead-context changes invalidate approval. Approval permits manual use only; there is no send tool or delivery state. This demonstrates agentic reasoning with bounded authority rather than autonomous sales execution.

## Cost and graceful degradation

Select a small model that passes evaluations; benchmark alternatives with the same cases and token budgets. Provider pricing and contractual retention remain unresolved until selection. Measure prompt/completion tokens, all attempts, wall time, retrieval/indexing expense, and failure cost. Cache retrieval by organization/access scope/corpus version; cache generated content only by authorized actor/scope, lead snapshot, prompt/model, and evidence versions with a short expiry. Suppression or revocation invalidates caches. Templates and rules stay usable when generation is unavailable.
