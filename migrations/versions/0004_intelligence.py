"""Versioned scores/knowledge and durable recommendation usage accounting."""

from pathlib import Path

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    for statement in sql.split(";\n"):
        if statement.strip():
            op.execute(statement)
    for table in ("score_runs", "document_chunks"):
        op.execute(f"""
            CREATE TRIGGER immutable_snapshot BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_snapshot_mutation()
        """)
    op.execute("""
        CREATE FUNCTION guard_document_content() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'Document history is append-only';
            END IF;
            IF (to_jsonb(NEW) - 'status' - 'revoked_at') IS DISTINCT FROM
               (to_jsonb(OLD) - 'status' - 'revoked_at') THEN
                RAISE EXCEPTION 'Document content is immutable';
            END IF;
            IF NOT (OLD.status='approved' AND NEW.status='revoked' AND NEW.revoked_at IS NOT NULL)
            THEN RAISE EXCEPTION 'Only revocation is permitted'; END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER immutable_document BEFORE UPDATE OR DELETE ON document_versions
        FOR EACH ROW EXECUTE FUNCTION guard_document_content()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER immutable_document ON document_versions")
    op.execute("DROP FUNCTION guard_document_content()")
    for table in (
        "ai_attempts",
        "ai_runs",
        "ai_budgets",
        "score_runs",
        "document_chunks",
        "document_versions",
        "documents",
        "knowledge_memberships",
    ):
        op.execute(f"DROP TABLE {table}")
