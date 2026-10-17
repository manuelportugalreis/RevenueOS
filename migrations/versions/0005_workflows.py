"""Bounded workflow state, append-only audit, and exact-version human approvals."""

from pathlib import Path

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for statement in Path(__file__).with_suffix(".sql").read_text().split(";\n"):
        if statement.strip():
            op.execute(statement)
    for table in ("workflow_audit", "outreach_versions", "action_approvals"):
        op.execute(f"""CREATE TRIGGER immutable_snapshot BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION reject_snapshot_mutation()""")


def downgrade() -> None:
    for table in (
        "action_receipts",
        "action_approvals",
        "outreach_versions",
        "outreach_actions",
        "workflow_audit",
        "workflow_reviewers",
        "bounded_workflows",
    ):
        op.execute(f"DROP TABLE {table}")
