"""Tenant policies, opaque session bootstrap, and idempotent web workflow requests."""

from alembic import op
from sqlalchemy import inspect, text

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE web_workflow_requests (
        organization_id uuid NOT NULL,actor_id uuid NOT NULL,request_key uuid NOT NULL,
        payload_hash char(64) NOT NULL,state varchar(20) NOT NULL DEFAULT 'pending'
            CHECK(state IN ('pending','completed','failed')),
        workflow_id uuid,response jsonb,failure_code varchar(80),
        created_at timestamptz NOT NULL DEFAULT now(),completed_at timestamptz,
        PRIMARY KEY(organization_id,actor_id,request_key),
        FOREIGN KEY(organization_id,actor_id)
            REFERENCES knowledge_memberships(organization_id,actor_id),
        FOREIGN KEY(organization_id,workflow_id)
            REFERENCES bounded_workflows(organization_id,id))""")
    connection = op.get_bind()
    for table in inspect(connection).get_table_names():
        columns = {c["name"] for c in inspect(connection).get_columns(table)}
        column = "id" if table == "organizations" else "organization_id"
        if column not in columns or table == "alembic_version":
            continue
        # Names are fixed migration-owned catalog identifiers, never browser input.
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        expression = f"{column}=nullif(current_setting('revenueos.organization_id',true),'')::uuid"
        if table == "document_versions":
            expression += """ AND access_scope=ANY(SELECT unnest(m.scopes)
                FROM public.knowledge_memberships m
                WHERE m.organization_id=document_versions.organization_id
                AND m.actor_id=nullif(current_setting('revenueos.actor_id',true),'')::uuid
                AND m.active)"""
        elif table == "document_chunks":
            expression += """ AND EXISTS(SELECT 1 FROM public.document_versions v
                WHERE v.organization_id=document_chunks.organization_id
                AND v.id=document_version_id)"""
        elif table == "documents":
            expression += """ AND EXISTS(SELECT 1 FROM public.document_versions v
                WHERE v.organization_id=documents.organization_id AND v.document_id=documents.id)"""
        op.execute(
            f'CREATE POLICY tenant_scope ON "{table}" USING ({expression}) '
            f"WITH CHECK ({expression})"
        )
    for view in ("current_datasets", "lead_response_facts_v1"):
        op.execute(f"ALTER VIEW {view} SET (security_invoker=true)")
    op.execute("""CREATE FUNCTION public.lookup_web_session(p_hash text)
        RETURNS SETOF public.web_sessions LANGUAGE sql STABLE SECURITY DEFINER
        SET search_path = pg_catalog
        AS $$ SELECT s.* FROM public.web_sessions s
          JOIN public.knowledge_memberships m ON
            (m.organization_id,m.actor_id)=(s.organization_id,s.actor_id)
          JOIN public.organizations o ON o.id=s.organization_id
          WHERE s.token_hash=p_hash AND s.expires_at>now()
            AND m.active AND o.data_mode='synthetic' $$""")
    op.execute("REVOKE ALL ON FUNCTION public.lookup_web_session(text) FROM PUBLIC")
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP FUNCTION public.lookup_web_session(text)")
    connection = op.get_bind()
    for table in inspect(connection).get_table_names():
        if connection.scalar(
            text("""SELECT 1 FROM pg_policies
            WHERE schemaname='public' AND tablename=:name AND policyname='tenant_scope'"""),
            {"name": table},
        ):
            op.execute(f'DROP POLICY tenant_scope ON "{table}"')
            op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
    for view in ("current_datasets", "lead_response_facts_v1"):
        op.execute(f"ALTER VIEW {view} RESET (security_invoker)")
    op.execute("DROP TABLE web_workflow_requests")
