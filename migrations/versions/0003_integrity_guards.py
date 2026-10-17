"""Protect published snapshot rows against accidental in-place edits."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLES = (
    "datasets",
    "import_batches",
    "import_errors",
    "accounts",
    "leads",
    "lead_private",
    "opportunities",
    "interactions",
    "opportunity_leads",
    "opportunity_stage_events",
    "lead_outcomes",
)


def upgrade() -> None:
    op.execute("ALTER TABLE organizations ADD CONSTRAINT uq_org_mode UNIQUE(id,data_mode)")
    op.execute("""
        ALTER TABLE datasets ADD CONSTRAINT fk_dataset_org_mode
        FOREIGN KEY(organization_id,data_mode) REFERENCES organizations(id,data_mode)
    """)
    op.execute("""
        CREATE FUNCTION reject_snapshot_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'Published snapshots are append-only' USING ERRCODE='55000';
        END;
        $$
    """)
    for table in TABLES:
        op.execute(f"""
            CREATE TRIGGER immutable_snapshot BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_snapshot_mutation()
        """)


def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f"DROP TRIGGER immutable_snapshot ON {table}")
    op.execute("DROP FUNCTION reject_snapshot_mutation()")
    op.execute("ALTER TABLE datasets DROP CONSTRAINT fk_dataset_org_mode")
    op.execute("ALTER TABLE organizations DROP CONSTRAINT uq_org_mode")
