# Database and ingestion proposal

This is a logical schema, not executable DDL or migrations. Start with one business per deployment. Include `organization_id` on owned records to make scope explicit, but do not claim multi-tenant readiness.

## Conventions and relationships

UUID primary keys; `timestamptz` for UTC instants; money as fixed precision numeric plus ISO currency; controlled enums for stages/statuses; JSONB only for versioned payloads, feature explanations, and provider metadata. Required business fields remain typed columns. All domain references must match organization via composite foreign keys `(organization_id, id)`. Audit the same invariant for optional polymorphic evidence references in service validation and database constraints where representable.

An organization has memberships, imports, accounts, leads, and documents. An account has many leads/opportunities. A lead has many interactions and can link to multiple opportunities through an explicit bridge. Score runs reference immutable feature snapshots; recommendations reference runs, citations, and draft versions. Draft reviews bind exact versions. Evaluation cases and pilot assignments reference pinned datasets and policies.

## Proposed tables

| Table | Principal fields and constraints | Purpose |
|---|---|---|
| organizations | id, name, reporting_timezone, default_currency, data_mode | Business scope; mode is synthetic or real; never silently mix |
| users / memberships | user: id, oidc_subject unique; membership: organization_id, user_id, role, active | Identity and roles; role changes audited |
| import_batches | id, organization_id, source_system, file_hash, mapping_version, schema_version, mode, status, counts, received_at, committed_at | Unique organization/source/hash/map tuple prevents replay; explicit force-reimport creates lineage |
| import_errors | batch_id, row_number, field, error_code, redacted_excerpt | Quarantine report; full raw PII excluded from error messages |
| datasets | id, organization_id, import_batch_id, version, observed_at, published_at, coverage_start/end, mode | Published snapshot/version for analytics and replay |
| accounts | id, organization_id, source_system, external_id, name, domain, industry, employee_band, source_updated_at | Unique organization/source/external_id; do not auto-merge on name |
| leads | id, organization_id, source_system, external_id, account_id nullable, owner_user_id nullable, source, status, created_at, source_updated_at, do_not_contact, deleted_at | Mutable current projection; unique source ID; unknown owner preserved |
| lead_private | organization_id, lead_id unique, name, email, lawful_use_status, retention_until | Restricted contact fields; only fetched when required |
| lead_versions | id, organization_id, lead_id, dataset_id, observed_at, source_effective_at, attributes, import_batch_id | Immutable state history; source-effective time can be unknown |
| interactions | id, organization_id, source_system, external_id, lead_id, occurred_at, ingested_at, direction, channel, actor_type, summary, import_batch_id | Unique source ID; distinguish human from automation; missing timestamp quarantined |
| opportunities | id, organization_id, source_system, external_id, account_id, owner_user_id, current_stage, amount, currency, created_at, closed_at, outcome | Check nonnegative amounts; terminal outcome/date consistency |
| opportunity_leads | organization_id, opportunity_id, lead_id, attribution_role | Unique pair; use distinct leads in conversion metrics |
| opportunity_stage_events | id, organization_id, opportunity_id, from_stage, to_stage, effective_at, observed_at, source_event_id | Immutable stage transitions; replay/dedup by source event |
| opportunity_versions | id, organization_id, opportunity_id, dataset_id, observed_at, source_effective_at, amount, currency, stage, outcome | Historical amount/stage snapshots for as-of analytics |
| lead_outcomes | id, organization_id, lead_id, label_definition_version, window_start/end, qualified_at nullable, observation_complete, label, provenance | Unique lead/definition/window; distinguish censored, positive, negative, unknown |
| documents | id, organization_id, title, access_scope, steward_user_id, status | Logical document; team or restricted scope |
| document_versions | id, organization_id, document_id, version, content_hash, storage_ref, approved_by/at, valid_from/until, revoked_at, extraction_version | Immutable approved content; new version requires approval |
| document_chunks | id, organization_id, document_version_id, ordinal, text, page/heading, start/end_offset, text_hash, search_vector | Unique version/ordinal; passage locator survives retrieval |
| chunk_embeddings (conditional) | organization_id, chunk_id, embedding_model_version, dimensions, vector | Added only after retrieval gate; never mix incompatible vectors |
| feature_snapshots | id, organization_id, lead_id, as_of, dataset_id, feature_schema_version, values, missingness, source_refs | Historical reproducibility, no future outcomes |
| score_runs | id, organization_id, feature_snapshot_id, scorer_type/version, eligible, points, components, run_at | Points are not probability; stable ordering by lead ID |
| workflow_runs | id, organization_id, requester_id, lead_id, state, idempotency_key, config_versions, input_hash, source_snapshot_id, started/ended_at, failure_code | Workflow ownership, policy state, replay lineage |
| model_calls | id, organization_id, workflow_run_id, attempt, provider/model_version, prompt_version, schema_version, input/output_tokens, latency_ms, cost_amount/currency, cost_status, status | Failed attempts included; unknown usage flagged and reconciled |
| usage_budgets / usage_reservations | budget: organization_id, period, approved_limit, spent, reserved; reservation: workflow_run_id, amount, state, expires_at | Atomically reserve worst-case bounded spend before calls; reconcile usage; expired uncertain calls require reconciliation before release of funds |
| recommendations | id, organization_id, workflow_run_id, score_run_id, action, rationale, missing_information, validation_status | Typed recommendation; no arbitrary execution payload |
| evidence_refs | id, organization_id, recommendation_id, claim_key, chunk_id nullable, feature_snapshot_id nullable, metric_ref nullable, excerpt_hash | Exactly one source kind; claim-to-source linkage |
| drafts / draft_versions | draft: id, organization_id, recommendation_id, current_version; version: id, draft_id, version, body, subject, content_hash, created_by, created_at, expires_at | Immutable versions with revision lineage; private content access |
| reviews | id, organization_id, draft_version_id, reviewer_id, decision, reason, reviewed_at, reviewed_hash | Unique terminal decision per version; stale versions cannot approve |
| audit_events | id, organization_id, actor_id/type, action, entity_type/id, correlation_id, timestamp, redacted_change, previous_hash | Append-only runtime permissions; hash chain is detection, not tamper-proof storage |
| jobs (conditional) | id, organization_id, type, input_ref, idempotency_key, state, lease_owner/until, attempts, heartbeat, next_attempt_at | Durable imports/indexing from same application |
| evaluation_cases / evaluation_runs / evaluation_results | case: dataset/version, task, expected sources/labels, slice; run: config/commit/environment; result: case_id, output_ref, metrics, reviewer | Reproducible comparison with case-level evidence |
| pilot_assignments / pilot_events | assignment: account_id, arm, stratum, assignment_time, experiment_version; event: task_id, actor, type, timestamp, duration, outcome/source | Frozen treatment and denominators; review time separated from sending |

## Ingestion and historical correctness

1. Accept an explicit data mode, schema, and mapping; reject mixed synthetic/real imports. Record source timezone and stage mapping. Source credentials are not accepted inside CSV files.
2. Stream parse with file/row limits; validate required IDs, enum mappings, timestamps, amounts/currencies, field lengths, and referential links. Unknown optional values stay null. A missing required schema or unsafe file fails the batch; isolated bad rows enter quarantine.
3. Display accepted/rejected counts and duplicate decisions. Commit accepted rows only after explicit import confirmation; never silently drop rejected rows. Publish a dataset atomically after integrity checks.
4. Upsert by stable source ID, not email. Replaying an identical batch returns the original result. A conflicting record with the same source version but different content becomes a conflict for review. Out-of-order updates cannot overwrite a newer current projection.
5. Preserve source-effective and ingestion times separately. Record coverage limits: a current CRM export cannot reconstruct the past. Historical scoring features require actual past events or verified snapshots; otherwise retrospective ML evaluation is unavailable.
6. Keep deletion/suppression tombstones for later imports; removed leads cannot be inadvertently reactivated. API ingestion later uses incremental cursors, reconciliation, rate-limit handling, and the same validation boundary.

## Indexes, metrics, and lifecycle

Index source identity uniqueness, `(organization_id, lead_id, occurred_at)` for interactions, lead status/owner/created time, opportunity stage/closed time, review status, and run correlation IDs. Use GIN for document lexical search. Add vector indexes only if exact search fails measured latency at expected scale. Use SQL views for metric definitions before materialized views; refresh and freshness must be visible if caching is introduced.

Reject cross-currency totals. Soft deletes remove records from active workflows immediately; later hard deletion cascades or anonymizes dependent records according to retention policy. Historical evidence containing personal content is access-restricted and deleted with its subject where required. Retain minimal non-content audit tombstones only under the approved policy. Backups expire on schedule, and restores replay deletions before access is reopened.

The simpler schema alternative is a few flat CRM tables plus files for runs; it suffices for an initial analytics prototype. The proposed history/evidence/review tables are justified by reproducibility, leakage prevention, and approval enforcement. Phase their creation with the roadmap rather than build all tables before the first useful slice.
