CREATE TABLE organizations (
    id uuid PRIMARY KEY,
    name varchar(200) NOT NULL,
    data_mode varchar(12) NOT NULL CHECK (data_mode IN ('synthetic','real')),
    reporting_timezone varchar(64) NOT NULL DEFAULT 'UTC',
    default_currency char(3) NOT NULL CHECK (default_currency IN ('USD','EUR','GBP','CAD','AUD'))
);
CREATE TABLE import_batches (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id),
    source_system varchar(64) NOT NULL,
    bundle_hash char(64) NOT NULL,
    preview_hash char(64) NOT NULL,
    schema_version varchar(20) NOT NULL,
    mapping_version varchar(64) NOT NULL,
    observed_at timestamptz NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    accepted_count integer NOT NULL CHECK (accepted_count >= 0),
    quarantined_count integer NOT NULL CHECK (quarantined_count >= 0),
    duplicate_count integer NOT NULL CHECK (duplicate_count >= 0),
    UNIQUE (organization_id, source_system, bundle_hash),
    UNIQUE (organization_id, id)
);
CREATE TABLE datasets (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations(id),
    import_batch_id uuid NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    data_mode varchar(12) NOT NULL CHECK (data_mode IN ('synthetic','real')),
    source_system varchar(64) NOT NULL,
    observed_at timestamptz NOT NULL,
    published_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    UNIQUE (organization_id, version),
    UNIQUE (import_batch_id),
    FOREIGN KEY (organization_id, import_batch_id) REFERENCES import_batches(organization_id,id)
);
CREATE TABLE import_errors (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id uuid NOT NULL,
    import_batch_id uuid NOT NULL,
    entity varchar(40) NOT NULL,
    row_number integer NOT NULL CHECK (row_number >= 2),
    field varchar(100) NOT NULL,
    code varchar(80) NOT NULL,
    FOREIGN KEY (organization_id, import_batch_id) REFERENCES import_batches(organization_id,id)
);
CREATE TABLE accounts (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    id uuid NOT NULL,
    external_id varchar(100) NOT NULL,
    source_updated_at timestamptz NOT NULL,
    row_hash char(64) NOT NULL,
    name varchar(200) NOT NULL,
    domain varchar(253),
    industry varchar(100),
    employee_band varchar(20) CHECK (employee_band IN ('1-10','11-50','51-200','201-1000','1000+')),
    PRIMARY KEY (organization_id,dataset_id,id),
    UNIQUE (organization_id,dataset_id,external_id),
    FOREIGN KEY (organization_id,dataset_id) REFERENCES datasets(organization_id,id)
);
CREATE TABLE leads (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    id uuid NOT NULL,
    external_id varchar(100) NOT NULL,
    source_updated_at timestamptz NOT NULL,
    row_hash char(64) NOT NULL,
    account_id uuid,
    source varchar(40) NOT NULL CHECK (source IN ('website','demo_request','webinar','referral','test','internal')),
    status varchar(30) NOT NULL CHECK (status IN ('new','working','qualified','disqualified')),
    created_at timestamptz NOT NULL,
    do_not_contact boolean NOT NULL,
    deleted_at timestamptz,
    PRIMARY KEY (organization_id,dataset_id,id),
    UNIQUE (organization_id,dataset_id,external_id),
    CHECK (source_updated_at >= created_at),
    CHECK (deleted_at IS NULL OR (deleted_at >= created_at AND deleted_at <= source_updated_at)),
    FOREIGN KEY (organization_id,dataset_id) REFERENCES datasets(organization_id,id),
    FOREIGN KEY (organization_id,dataset_id,account_id) REFERENCES accounts(organization_id,dataset_id,id)
);
CREATE TABLE lead_private (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    name varchar(200),
    email varchar(254),
    lawful_use_status varchar(20) NOT NULL CHECK (lawful_use_status IN ('approved','unknown','blocked')),
    PRIMARY KEY (organization_id,dataset_id,lead_id),
    FOREIGN KEY (organization_id,dataset_id,lead_id) REFERENCES leads(organization_id,dataset_id,id)
);
CREATE TABLE opportunities (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    id uuid NOT NULL,
    external_id varchar(100) NOT NULL,
    source_updated_at timestamptz NOT NULL,
    row_hash char(64) NOT NULL,
    account_id uuid NOT NULL,
    stage varchar(20) NOT NULL CHECK (stage IN ('discovery','demo','proposal','won','lost')),
    amount numeric(14,2) NOT NULL CHECK (amount >= 0),
    currency char(3) NOT NULL CHECK (currency IN ('USD','EUR','GBP','CAD','AUD')),
    created_at timestamptz NOT NULL,
    closed_at timestamptz,
    PRIMARY KEY (organization_id,dataset_id,id),
    UNIQUE (organization_id,dataset_id,external_id),
    CHECK (source_updated_at >= created_at),
    CHECK ((stage IN ('won','lost')) = (closed_at IS NOT NULL)),
    CHECK (closed_at IS NULL OR (closed_at >= created_at AND closed_at <= source_updated_at)),
    FOREIGN KEY (organization_id,dataset_id) REFERENCES datasets(organization_id,id),
    FOREIGN KEY (organization_id,dataset_id,account_id) REFERENCES accounts(organization_id,dataset_id,id)
);
CREATE TABLE interactions (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    id uuid NOT NULL,
    external_id varchar(100) NOT NULL,
    source_updated_at timestamptz NOT NULL,
    row_hash char(64) NOT NULL,
    lead_id uuid NOT NULL,
    occurred_at timestamptz NOT NULL,
    direction varchar(10) NOT NULL CHECK (direction IN ('inbound','outbound')),
    channel varchar(20) NOT NULL CHECK (channel IN ('email','phone','meeting','web')),
    actor_type varchar(12) NOT NULL CHECK (actor_type IN ('human','automation')),
    summary varchar(2000),
    PRIMARY KEY (organization_id,dataset_id,id),
    UNIQUE (organization_id,dataset_id,external_id),
    CHECK (source_updated_at >= occurred_at),
    FOREIGN KEY (organization_id,dataset_id,lead_id) REFERENCES leads(organization_id,dataset_id,id)
);
CREATE TABLE opportunity_leads (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    opportunity_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    PRIMARY KEY (organization_id,dataset_id,opportunity_id,lead_id),
    FOREIGN KEY (organization_id,dataset_id,opportunity_id) REFERENCES opportunities(organization_id,dataset_id,id),
    FOREIGN KEY (organization_id,dataset_id,lead_id) REFERENCES leads(organization_id,dataset_id,id)
);
CREATE TABLE opportunity_stage_events (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    id uuid NOT NULL,
    external_id varchar(100) NOT NULL,
    source_updated_at timestamptz NOT NULL,
    row_hash char(64) NOT NULL,
    opportunity_id uuid NOT NULL,
    from_stage varchar(20),
    to_stage varchar(20) NOT NULL,
    effective_at timestamptz NOT NULL,
    PRIMARY KEY (organization_id,dataset_id,id),
    UNIQUE (organization_id,dataset_id,external_id),
    CHECK (from_stage IS NULL OR from_stage IN ('discovery','demo','proposal','won','lost')),
    CHECK (to_stage IN ('discovery','demo','proposal','won','lost')),
    CHECK (source_updated_at >= effective_at),
    FOREIGN KEY (organization_id,dataset_id,opportunity_id) REFERENCES opportunities(organization_id,dataset_id,id)
);
CREATE TABLE lead_outcomes (
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    definition_version varchar(30) NOT NULL CHECK (definition_version = 'qualified_30d_v1'),
    qualified_at timestamptz,
    observation_complete boolean NOT NULL,
    observed_through timestamptz NOT NULL,
    PRIMARY KEY (organization_id,dataset_id,lead_id),
    FOREIGN KEY (organization_id,dataset_id,lead_id) REFERENCES leads(organization_id,dataset_id,id),
    CHECK (qualified_at IS NULL OR qualified_at <= observed_through)
);
CREATE TABLE suppression_tombstones (
    organization_id uuid NOT NULL REFERENCES organizations(id),
    source_system varchar(64) NOT NULL,
    lead_id uuid NOT NULL,
    do_not_contact boolean NOT NULL,
    deleted_at timestamptz,
    PRIMARY KEY (organization_id,source_system,lead_id),
    CHECK (do_not_contact OR deleted_at IS NOT NULL)
);
CREATE INDEX ix_interactions_lead_time ON interactions(organization_id,dataset_id,lead_id,occurred_at);
CREATE INDEX ix_leads_created ON leads(organization_id,dataset_id,created_at);
CREATE INDEX ix_opportunities_closed ON opportunities(organization_id,dataset_id,closed_at);
CREATE INDEX ix_datasets_version ON datasets(organization_id,version DESC);
