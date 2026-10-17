CREATE TABLE knowledge_memberships (
    organization_id uuid NOT NULL REFERENCES organizations(id),
    actor_id uuid NOT NULL,
    role varchar(20) NOT NULL CHECK (role IN ('reader','steward')),
    scopes text[] NOT NULL,
    active boolean NOT NULL DEFAULT true,
    PRIMARY KEY(organization_id,actor_id)
);
CREATE TABLE documents (
    organization_id uuid NOT NULL REFERENCES organizations(id),
    id uuid NOT NULL,
    slug varchar(100) NOT NULL,
    PRIMARY KEY(organization_id,id),
    UNIQUE(organization_id,slug)
);
CREATE TABLE document_versions (
    organization_id uuid NOT NULL,
    id uuid NOT NULL,
    document_id uuid NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    title varchar(200) NOT NULL,
    content text NOT NULL CHECK (octet_length(content) <= 262144),
    content_hash char(64) NOT NULL,
    access_scope varchar(64) NOT NULL,
    data_mode varchar(12) NOT NULL CHECK(data_mode IN ('synthetic','real')),
    claim_key varchar(100) NOT NULL,
    claim_value varchar(500) NOT NULL,
    outreach_allowed boolean NOT NULL,
    status varchar(12) NOT NULL CHECK(status IN ('draft','approved','revoked')),
    approved_by uuid,
    approved_at timestamptz,
    valid_from timestamptz NOT NULL,
    valid_until timestamptz,
    revoked_at timestamptz,
    chunker_version varchar(30) NOT NULL,
    PRIMARY KEY(organization_id,id),
    UNIQUE(organization_id,document_id,version),
    FOREIGN KEY(organization_id,document_id) REFERENCES documents(organization_id,id),
    FOREIGN KEY(organization_id,data_mode) REFERENCES organizations(id,data_mode),
    CHECK(valid_until IS NULL OR valid_until > valid_from),
    CHECK((status='draft' AND approved_by IS NULL AND approved_at IS NULL AND revoked_at IS NULL)
       OR (status='approved' AND approved_by IS NOT NULL AND approved_at IS NOT NULL AND revoked_at IS NULL)
       OR (status='revoked' AND approved_by IS NOT NULL AND approved_at IS NOT NULL AND revoked_at IS NOT NULL))
);
CREATE TABLE document_chunks (
    organization_id uuid NOT NULL,
    id uuid NOT NULL,
    document_version_id uuid NOT NULL,
    ordinal integer NOT NULL CHECK(ordinal >= 0),
    heading varchar(500) NOT NULL,
    start_offset integer NOT NULL CHECK(start_offset >= 0),
    end_offset integer NOT NULL CHECK(end_offset > start_offset),
    text text NOT NULL,
    text_hash char(64) NOT NULL,
    search_vector tsvector NOT NULL,
    PRIMARY KEY(organization_id,id),
    UNIQUE(organization_id,document_version_id,ordinal),
    FOREIGN KEY(organization_id,document_version_id) REFERENCES document_versions(organization_id,id)
);
CREATE INDEX ix_document_search ON document_chunks USING gin(search_vector);
CREATE INDEX ix_document_current ON document_versions(organization_id,document_id,version DESC);
CREATE TABLE score_runs (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    as_of timestamptz NOT NULL,
    ruleset_version varchar(40) NOT NULL,
    config_hash char(64) NOT NULL,
    eligible boolean NOT NULL,
    points integer NOT NULL CHECK(points BETWEEN 0 AND 100),
    explanation jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY(organization_id,dataset_id,lead_id) REFERENCES leads(organization_id,dataset_id,id)
);
CREATE TABLE ai_budgets (
    organization_id uuid NOT NULL REFERENCES organizations(id),
    period char(7) NOT NULL CHECK(period ~ '^[0-9]{4}-[0-9]{2}$'),
    limit_usd numeric(18,8) NOT NULL CHECK(limit_usd >= 0),
    spent_usd numeric(18,8) NOT NULL DEFAULT 0 CHECK(spent_usd >= 0),
    reserved_usd numeric(18,8) NOT NULL DEFAULT 0 CHECK(reserved_usd >= 0),
    PRIMARY KEY(organization_id,period)
);
CREATE TABLE ai_runs (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    provider_kind varchar(40) NOT NULL,
    prompt_version varchar(40) NOT NULL,
    schema_version varchar(40) NOT NULL,
    rules_config_hash char(64) NOT NULL,
    request_hash char(64) NOT NULL,
    query_hash char(64) NOT NULL,
    state varchar(20) NOT NULL CHECK(state IN ('running','review_pending','abstained','failed')),
    failure_code varchar(100),
    output jsonb,
    human_review_required boolean NOT NULL DEFAULT true CHECK(human_review_required),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE(organization_id,id),
    FOREIGN KEY(organization_id,dataset_id,lead_id) REFERENCES leads(organization_id,dataset_id,id),
    FOREIGN KEY(organization_id,actor_id) REFERENCES knowledge_memberships(organization_id,actor_id)
);
CREATE TABLE ai_attempts (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    run_id uuid NOT NULL,
    attempt integer NOT NULL CHECK(attempt BETWEEN 1 AND 2),
    period char(7) NOT NULL,
    provider_kind varchar(40) NOT NULL,
    model varchar(200) NOT NULL,
    price_version varchar(100) NOT NULL,
    input_rate numeric(18,8) NOT NULL CHECK(input_rate >= 0),
    output_rate numeric(18,8) NOT NULL CHECK(output_rate >= 0),
    state varchar(30) NOT NULL CHECK(state IN ('reserved','accounted','usage_unknown')),
    input_tokens integer CHECK(input_tokens >= 0),
    output_tokens integer CHECK(output_tokens >= 0),
    reserved_usd numeric(18,8) NOT NULL CHECK(reserved_usd >= 0),
    estimated_cost_usd numeric(18,8) CHECK(estimated_cost_usd >= 0),
    cost_basis varchar(40) NOT NULL,
    outcome varchar(100),
    latency_ms numeric(14,3) CHECK(latency_ms >= 0),
    provider_response_id varchar(200),
    UNIQUE(run_id,attempt),
    FOREIGN KEY(organization_id,run_id) REFERENCES ai_runs(organization_id,id),
    FOREIGN KEY(organization_id,period) REFERENCES ai_budgets(organization_id,period)
);
