import os
from contextvars import ContextVar
from uuid import UUID

from sqlalchemy import Connection, Engine, create_engine, event, text

tenant_context: ContextVar[UUID | None] = ContextVar("revenueos_tenant", default=None)
actor_context: ContextVar[UUID | None] = ContextVar("revenueos_actor", default=None)


def _set_scope(connection: Connection) -> None:
    scope = tenant_context.get()
    connection.execute(
        text(
            "SELECT set_config('revenueos.organization_id',:org,true),"
            "set_config('revenueos.actor_id',:actor,true)"
        ),
        {"org": str(scope) if scope else "", "actor": str(actor_context.get() or "")},
    )


def get_engine(url: str | None = None) -> Engine:
    target = url or os.environ["DATABASE_URL"]
    if not target.startswith("postgresql+psycopg://"):
        raise ValueError("RevenueOS requires PostgreSQL through psycopg")
    engine = create_engine(
        target,
        pool_pre_ping=True,
        pool_timeout=5,
        hide_parameters=True,
        connect_args={"options": "-c timezone=UTC", "connect_timeout": 5},
    )
    # SET LOCAL is reset on transaction completion; the context never survives pool reuse.
    event.listen(engine, "begin", _set_scope)
    return engine
