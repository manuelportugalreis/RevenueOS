"""Opaque web sessions and bounded login-attempt history."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE web_sessions (
        token_hash char(64) PRIMARY KEY, organization_id uuid NOT NULL, actor_id uuid NOT NULL,
        csrf_token varchar(100) NOT NULL, expires_at timestamptz NOT NULL,
        FOREIGN KEY(organization_id,actor_id)
            REFERENCES knowledge_memberships(organization_id,actor_id))""")
    op.execute("CREATE INDEX ix_web_sessions_expiry ON web_sessions(expires_at)")
    op.execute("""CREATE TABLE web_login_attempts (
        id bigserial PRIMARY KEY, key_hash char(64) NOT NULL,
        occurred_at timestamptz NOT NULL DEFAULT now())""")
    op.execute("CREATE INDEX ix_web_login_key ON web_login_attempts(key_hash,occurred_at)")


def downgrade() -> None:
    op.execute("DROP TABLE web_login_attempts")
    op.execute("DROP TABLE web_sessions")
