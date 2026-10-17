"""Current snapshot projection and SQL metric building blocks."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW current_datasets AS
        SELECT DISTINCT ON (organization_id) * FROM datasets
        ORDER BY organization_id, version DESC
    """)
    op.execute("""
        CREATE VIEW lead_response_facts_v1 AS
        SELECT l.organization_id, l.dataset_id, l.id AS lead_id,
               min(i.occurred_at) FILTER (
                 WHERE i.direction='outbound' AND i.actor_type='human'
                   AND i.occurred_at >= l.created_at) AS first_human_response_at
        FROM leads l LEFT JOIN interactions i
          ON (i.organization_id,i.dataset_id,i.lead_id)=(l.organization_id,l.dataset_id,l.id)
        GROUP BY l.organization_id,l.dataset_id,l.id
    """)


def downgrade() -> None:
    op.execute("DROP VIEW lead_response_facts_v1")
    op.execute("DROP VIEW current_datasets")
