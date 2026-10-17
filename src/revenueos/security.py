"""Opt-in runtime-role grants; execute with a migration administrator, never HTTP."""

from sqlalchemy import Connection, text


def install_runtime_role(connection: Connection, role: str = "revenueos_runtime") -> None:
    if role not in ("revenueos_runtime", "revenueos_runtime_test"):
        raise ValueError("fixed_runtime_role_required")
    exists = connection.scalar(text("SELECT 1 FROM pg_roles WHERE rolname=:role"), {"role": role})
    if not exists:
        connection.execute(
            text(
                f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOCREATEDB "
                "NOCREATEROLE NOINHERIT NOBYPASSRLS"
            )
        )
    flags = connection.execute(
        text("""SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls
        FROM pg_roles WHERE rolname=:role"""),
        {"role": role},
    ).one()
    if any(flags):
        raise ValueError("refusing_privileged_existing_role")
    # --no-acl restores omit revokes as well as grants; reapply the public boundary.
    connection.execute(text("REVOKE CREATE ON SCHEMA public FROM PUBLIC"))
    connection.execute(text("REVOKE ALL ON FUNCTION public.lookup_web_session(text) FROM PUBLIC"))
    connection.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
    tables = (
        "organizations",
        "datasets",
        "import_batches",
        "accounts",
        "leads",
        "lead_private",
        "interactions",
        "suppression_tombstones",
        "lead_outcomes",
        "opportunities",
        "opportunity_leads",
        "opportunity_stage_events",
        "documents",
        "document_versions",
        "document_chunks",
        "knowledge_memberships",
        "workflow_reviewers",
        "score_runs",
        "ai_runs",
        "ai_attempts",
        "ai_budgets",
        "bounded_workflows",
        "workflow_audit",
        "outreach_actions",
        "outreach_versions",
        "action_approvals",
        "action_receipts",
        "web_sessions",
        "web_login_attempts",
        "web_workflow_requests",
        "alembic_version",
    )
    for table in tables:
        connection.execute(text(f'GRANT SELECT ON public."{table}" TO {role}'))
    connection.execute(text(f"GRANT SELECT ON current_datasets,lead_response_facts_v1 TO {role}"))
    for table in (
        "ai_runs",
        "ai_attempts",
        "bounded_workflows",
        "workflow_audit",
        "outreach_actions",
        "outreach_versions",
        "action_approvals",
        "web_sessions",
        "web_login_attempts",
        "web_workflow_requests",
    ):
        connection.execute(text(f"GRANT INSERT ON public.{table} TO {role}"))
    for table in (
        "ai_runs",
        "ai_attempts",
        "ai_budgets",
        "bounded_workflows",
        "outreach_actions",
        "web_workflow_requests",
    ):
        connection.execute(text(f"GRANT UPDATE ON public.{table} TO {role}"))
    connection.execute(text(f"GRANT UPDATE(id) ON public.organizations TO {role}"))
    connection.execute(
        text(f"GRANT DELETE ON public.web_sessions,public.web_login_attempts TO {role}")
    )
    connection.execute(text(f"GRANT USAGE ON SEQUENCE public.web_login_attempts_id_seq TO {role}"))
    connection.execute(text(f"GRANT EXECUTE ON FUNCTION public.lookup_web_session(text) TO {role}"))


def runtime_posture(connection: Connection) -> dict[str, object]:
    row = (
        connection.execute(
            text("""SELECT current_user AS role,rolsuper,rolbypassrls,rolcreatedb,
        rolcreaterole FROM pg_roles WHERE rolname=current_user""")
        )
        .mappings()
        .one()
    )
    owns_tables = bool(
        connection.scalar(
            text("""SELECT 1 FROM pg_class c JOIN pg_namespace n
        ON n.oid=c.relnamespace WHERE n.nspname='public'
        AND pg_has_role(current_user,c.relowner,'USAGE') LIMIT 1""")
        )
    )
    return {
        **dict(row),
        "owns_application_relations": owns_tables,
        "restricted": not owns_tables
        and not any(row[k] for k in ("rolsuper", "rolbypassrls", "rolcreatedb", "rolcreaterole")),
    }
