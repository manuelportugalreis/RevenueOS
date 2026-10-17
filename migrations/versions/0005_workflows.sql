CREATE TABLE bounded_workflows (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    dataset_id uuid NOT NULL,
    lead_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    state varchar(30) NOT NULL CHECK(state IN ('planning','reading','recommending','review_pending','abstained','failed')),
    policy_version varchar(40) NOT NULL,
    request_hash char(64) NOT NULL,
    planner_attempts integer NOT NULL DEFAULT 0 CHECK(planner_attempts BETWEEN 0 AND 2),
    tool_calls integer NOT NULL DEFAULT 0 CHECK(tool_calls BETWEEN 0 AND 4),
    recommendation_id uuid,
    failure_code varchar(100),
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    UNIQUE(organization_id,id),
    FOREIGN KEY(organization_id,dataset_id,lead_id) REFERENCES leads(organization_id,dataset_id,id),
    FOREIGN KEY(organization_id,actor_id) REFERENCES knowledge_memberships(organization_id,actor_id),
    FOREIGN KEY(organization_id,recommendation_id) REFERENCES ai_runs(organization_id,id)
);
CREATE TABLE workflow_reviewers (
    organization_id uuid NOT NULL,
    actor_id uuid NOT NULL,
    active boolean NOT NULL DEFAULT true,
    PRIMARY KEY(organization_id,actor_id),
    FOREIGN KEY(organization_id,actor_id) REFERENCES knowledge_memberships(organization_id,actor_id)
);
CREATE TABLE workflow_audit (
    organization_id uuid NOT NULL REFERENCES organizations(id),
    sequence bigint NOT NULL,
    workflow_id uuid,
    actor_id uuid NOT NULL,
    event varchar(60) NOT NULL,
    outcome varchar(100) NOT NULL,
    subject_hash char(64) NOT NULL,
    previous_hash char(64) NOT NULL,
    event_hash char(64) NOT NULL,
    occurred_at timestamptz NOT NULL,
    PRIMARY KEY(organization_id,sequence),
    FOREIGN KEY(organization_id,workflow_id) REFERENCES bounded_workflows(organization_id,id)
);
CREATE INDEX ix_workflow_audit_run ON workflow_audit(organization_id,workflow_id,sequence);
CREATE TABLE outreach_actions (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    workflow_id uuid NOT NULL,
    current_version integer NOT NULL DEFAULT 1 CHECK(current_version>0),
    state varchar(20) NOT NULL CHECK(state IN ('pending','approved','rejected','rehearsed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(organization_id,id),
    UNIQUE(workflow_id),
    FOREIGN KEY(organization_id,workflow_id) REFERENCES bounded_workflows(organization_id,id)
);
CREATE TABLE outreach_versions (
    organization_id uuid NOT NULL,
    action_id uuid NOT NULL,
    version integer NOT NULL CHECK(version>0),
    kind varchar(30) NOT NULL CHECK(kind='email_draft'),
    recipient varchar(254) NOT NULL,
    message jsonb NOT NULL,
    payload_hash char(64) NOT NULL,
    expires_at timestamptz NOT NULL,
    created_by uuid NOT NULL,
    PRIMARY KEY(organization_id,action_id,version),
    FOREIGN KEY(organization_id,action_id) REFERENCES outreach_actions(organization_id,id),
    FOREIGN KEY(organization_id,created_by) REFERENCES knowledge_memberships(organization_id,actor_id)
);
CREATE TABLE action_approvals (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    action_id uuid NOT NULL,
    version integer NOT NULL,
    payload_hash char(64) NOT NULL,
    reviewer_id uuid NOT NULL,
    decision varchar(10) NOT NULL CHECK(decision IN ('approve','reject')),
    decided_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    UNIQUE(organization_id,action_id,version),
    FOREIGN KEY(organization_id,action_id,version) REFERENCES outreach_versions(organization_id,action_id,version),
    FOREIGN KEY(organization_id,reviewer_id) REFERENCES workflow_reviewers(organization_id,actor_id)
);
CREATE TABLE action_receipts (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL,
    action_id uuid NOT NULL UNIQUE,
    approval_id uuid NOT NULL UNIQUE REFERENCES action_approvals(id),
    payload_hash char(64) NOT NULL,
    mode varchar(20) NOT NULL CHECK(mode='offline_rehearsal'),
    delivered boolean NOT NULL CHECK(NOT delivered),
    created_at timestamptz NOT NULL,
    FOREIGN KEY(organization_id,action_id) REFERENCES outreach_actions(organization_id,id)
);
