"""Immutable CRM export snapshots, validation lineage, and suppression tombstones."""

from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    sql = Path(__file__).with_suffix(".sql").read_text(encoding="utf-8")
    for statement in sql.split(";\n"):
        if statement.strip():
            op.execute(statement)


def downgrade() -> None:
    # Only this application's tables; no CASCADE against unrelated database objects.
    for table in (
        "suppression_tombstones",
        "lead_outcomes",
        "opportunity_stage_events",
        "opportunity_leads",
        "interactions",
        "lead_private",
        "opportunities",
        "leads",
        "accounts",
        "import_errors",
        "datasets",
        "import_batches",
        "organizations",
    ):
        op.execute(f"DROP TABLE {table}")
