# Security, privacy, and AI governance

## Scope and ownership

Treat CRM contact details, interactions, private sales documents, drafts, and model inputs as confidential. Use synthetic data for public portfolio assets, tests, screenshots, logs, and demonstrations. A synthetic marker must survive import, storage, API responses, exports, and UI rendering. A marker alone is insufficient: generators must use fictitious entities and non-deliverable domains, with a review for accidental real identities.

The technical owner owns access controls, incident response, and release gates. The RevOps sponsor owns score rules, qualification definitions, access decisions, and pilot success criteria. A document steward owns approved claims and source validity. Reviewers own outreach approval; independent evaluators assess factual quality. These may be roles held by a small number of people, but responsibilities must be explicit.

Use the [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework) as a governance organizing reference: document use context, measure risks, assign owners, and manage changes. This is a lightweight alignment exercise, not a compliance certification. Threat tests draw on [OWASP's LLM application risks](https://owasp.org/projects/top-10-for-large-language-model-applications), especially injection, information disclosure, excessive agency, and resource abuse.

## Controls by boundary

| Boundary | Required control | Verification evidence |
|---|---|---|
| Browser → API | TLS, OIDC session, secure HttpOnly SameSite cookies, CSRF protection on mutations, explicit CORS, escaped text | Unauthenticated requests fail; CSRF and stored-XSS fixtures |
| Identity → data | Server-derived organization/role; object checks on every read/write/export/citation; single-business deployment | Cross-organization and role-negative tests, including guessed IDs |
| API → database | Parameterized SQL; least-privilege non-owner runtime role; RLS where scope applies; separate migration account | Integration tests using actual runtime role; no owner/BYPASSRLS access |
| Import → storage | File size/row limits, parser timeouts, content-type checks, randomized storage paths, no public uploads | Oversized, malformed, duplicate, path traversal and parser-abuse cases |
| Documents → model | Approved versions, ACL filtering, instruction/data separation, limited context | Injection and revoked-source suites; no tool authority from document text |
| Model → application | Strict schema and evidence allowlist, policy validation, bounded calls, escaped rendering | Malformed outputs, false citation IDs, arbitrary action and quota tests |
| Application → external world | No send adapter or credentials; allowlisted provider egress only | Attempted external-message and arbitrary URL calls denied |
| Human → approval | Reviewer identity, authorization, hash/version check, current evidence, expiry, atomic update | Edit/revoke/race/expired approval tests |
| Operations → logs/backups | Redaction, encrypted transport/storage, restricted access, retention, restore drills | Log scan, access review, documented restore results |

Roles: representative reads permitted CRM context and reviews their drafts; manager reads team analytics and reviews team work; RevOps imports/maps data and manages rules; steward approves documents; administrator manages membership/configuration. Administrative powers do not automatically authorize use of restricted customer content. Initially all admitted approved knowledge is team-accessible; restricted documents require tested scope enforcement before admission. LLM identity never grants user privileges.

## Real-data admission and privacy lifecycle

Before real data: sponsor confirms authorized purpose and permission to process; inventory fields; remove unnecessary identifiers; approve retention, provider/subprocessors, residency, access, and contractual restrictions. Hosted model processing of real data is blocked until this review is recorded. If requirements cannot be met, remain synthetic or use an approved local model only after capability/quality review. No compliance claims are made without applicable review.

Proposed defaults, subject to sponsor approval: raw uploads deleted seven days after successful import; active pilot contact/context/draft data retained through pilot plus 30 days; restricted content-free audit metadata 180 days; operational logs 30 days; rolling backups 30 days. No raw prompts or CRM text in routine logs. Debug payload capture is off by default, minimized/redacted, restricted, and expires after seven days when explicitly enabled. Never commit secrets or real datasets to Git. Secrets are injected via environment variables; local `.env` is ignored and deployment uses secret storage with rotation.

Deletion workflow: authenticate request/authority → locate subject and linked sources → suppress immediately → remove private fields, document excerpts, drafts, embeddings and caches → preserve only approved non-personal audit tombstone → record completion → replay deletion ledger after backup restoration before reopening access. Previously copied outreach cannot be recalled; manual-use responsibility belongs to the reviewer and pilot business. Test deletion with a known synthetic subject across all stores.

## Change governance and release safety

Version datasets, score rules, label definitions, prompts, models, tool schemas, chunkers, retrieval settings, and approved documents. Any change runs the relevant evaluation subset plus fixed safety regression suite. Model/provider changes require quality, privacy, latency, and cost review. Keep a release decision with known failures, signer, date, rollback target, and evidence artifact hashes. Score rules must be inspectable and overrideable with an audit reason.

Provide kill switches for generation, imports, and approvals; immutable run status; rate limiting by actor/business; monthly/daily cost reservations; and separate development/pilot credentials. A model timeout never produces an approved draft. Show error codes and support correlation IDs without exposing private provider responses.

Proposed pilot operations: daily backup; restore target RPO ≤24 hours and RTO ≤4 hours, proven by a drill before real-data use. These are targets, not vendor guarantees. Health checks separate API readiness, database readiness, provider state, and stale indexing. Monitor import failures, quarantine rate, latency, attempts, invalid citations, abstention, spend, and approval conflicts. Alert on unauthorized-access attempts and unexpected outbound traffic.

Incident response: disable the affected capability, restrict access and preserve redacted evidence, identify data/people affected, rotate exposed secrets, notify the sponsor promptly (target within one business day), follow applicable business/legal notification requirements, restore from a verified safe version, rerun regression tests, and document corrective action. Rehearse provider outage, leaked credential, and revoked-document scenarios.

## Simpler alternative

A fully local, synthetic-only demo with no external provider and fixed templates reduces privacy exposure and operational work. It cannot establish readiness for real customer data. The proposed controls are introduced with their relevant phase; no real pilot starts with demo authentication or untested restoration.
