"""Record policy/method explicitly; historical runs remain marked unrecorded."""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""ALTER TABLE ai_runs
        ADD COLUMN retrieval_method varchar(30) NOT NULL DEFAULT 'unrecorded',
        ADD COLUMN evidence_profile varchar(30) NOT NULL DEFAULT 'unrecorded',
        ADD COLUMN evidence_selection jsonb""")


def downgrade() -> None:
    op.execute("""ALTER TABLE ai_runs DROP COLUMN evidence_selection,
        DROP COLUMN evidence_profile,DROP COLUMN retrieval_method""")
