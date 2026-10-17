"""Explicit SQL migrations. DATABASE_URL is never persisted in config or logs."""

import os

from alembic import context
from sqlalchemy import create_engine, pool


def run() -> None:
    url = os.environ["DATABASE_URL"]
    if not url.startswith("postgresql+psycopg://"):
        raise ValueError("RevenueOS requires PostgreSQL through psycopg")
    if context.is_offline_mode():
        context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        with engine.connect() as connection:
            context.configure(connection=connection)
            with context.begin_transaction():
                context.run_migrations()
        engine.dispose()


run()
