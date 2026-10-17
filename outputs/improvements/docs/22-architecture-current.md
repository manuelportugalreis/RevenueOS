# Implemented architecture and evidence boundaries

Current hardening adds a non-owner runtime role, organization/document RLS, transaction-local identity scope, focused evidence selection, request idempotency and steward-only interruption reconciliation. See [design details](28-improvements-guide.md) and [current verification](29-improvements-verification.md). The SVG below predates these additions; the flow remains a single modular application.

![Implemented RevenueOS architecture](architecture.svg)

```mermaid
flowchart TD
  U[Executive / sales user / assigned reviewer] --> B[React + TypeScript dashboard]
  G[Google Workspace OIDC: configured adapter, live tenant unverified] -.-> A[FastAPI identity boundary]
  B --> A
  A --> S[Opaque DB session + membership + Origin/CSRF]
  S --> M[SQL analytics / explained rules]
  S --> I[Actor-bound idempotency key + payload hash + quota]
  I --> W[Bounded read workflow: max 4 tool calls]
  W --> K[Approved scoped lexical knowledge + exact citations]
  W --> T[Validated recommendation: offline template]
  T --> V[Immutable recipient/message/evidence/hash version]
  V --> H[Explicit authenticated reviewer decision]
  H --> X[Decision persisted; no web send endpoint]
  M --> R[Non-owner runtime + organization/document RLS]
  R --> DB[(PostgreSQL: snapshots, documents, runs, sessions, audit)]
  K --> DB
  V --> DB
  H --> DB
  W --> L[Transactional redacted audit / attempt reservations]
  L --> DB
  C[CSV preview / validation / explicit commit] --> DB
  E[Paired synthetic evaluation CLI] --> M
  E --> W
  E --> F[Baseline title search + same validated template]
  F --> DB
  E --> R[Raw JSONL / hashes / clustered descriptive intervals]
  A --> O[Readiness + redacted logs + steward process counters]
  P[Optional live model adapter: not exercised] -.-> T
```

The four read tools cannot select organization/actor/lead, execute SQL, call URLs, assign reviewers or perform writes. The model/provider path has no email/CRM mutation adapter. Existing operator-only approval rehearsal records `delivered=false`; the dashboard exposes decisions only. Google integration is offline-tested with signed mock tokens and policy cases; no live tenant/client credentials were configured.

Deployment is one application/static frontend container, one PostgreSQL instance and a TLS reverse proxy, with no premature microservices. The compiled SPA contains no provider/client secret or identity mapping. SQL/knowledge scope is server-owned. A restricted runtime role/RLS, restore/retention, hosted OAuth and load verification remain prerequisite pilot hardening, not completed controls.

The evaluation lane records synthetic computation, not client behavior. It never converts API milliseconds into human task-time savings or synthetic outcomes into predictive accuracy. See the protocol in docs/21-comparison-acceptance.md and results in docs/23-comparison-report.md.
