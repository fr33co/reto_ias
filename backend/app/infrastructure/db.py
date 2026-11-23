"""Engine creation and schema initialisation (tables, indexes, immutability trigger)."""
from sqlalchemy import Engine, create_engine, text

from .orm import Base

# Traceability: dispatches are never modified or deleted (enforced by the database itself).
_TRIGGER = """
CREATE OR REPLACE FUNCTION dispatches_immutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'dispatches are immutable (%)', TG_OP;
END;
$$ LANGUAGE plpgsql;
DROP TRIGGER IF EXISTS dispatches_no_update_delete ON dispatches;
CREATE TRIGGER dispatches_no_update_delete
    BEFORE UPDATE OR DELETE ON dispatches
    FOR EACH ROW EXECUTE FUNCTION dispatches_immutable();
"""


def create_db_engine(url: str) -> Engine:
    """Create the SQLAlchemy engine (psycopg 3 driver, small pool, connection pre-ping).

    Args:
        url: Database URL; `postgresql://` is normalised to `postgresql+psycopg://`.
    """
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(url, pool_size=5, max_overflow=5, pool_pre_ping=True)


def init_schema(engine: Engine) -> None:
    """Create the tables and install the immutability trigger (idempotent).

    An advisory lock serialises concurrent start-ups.

    Args:
        engine: The engine to initialise.
    """
    Base.metadata.create_all(engine)
    with engine.begin() as c:
        c.execute(text("SELECT pg_advisory_xact_lock(42)"))   # concurrent start-ups
        c.execute(text(_TRIGGER))
