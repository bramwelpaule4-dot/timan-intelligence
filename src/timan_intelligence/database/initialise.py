
"""Database initialisation for TimanStat."""

from __future__ import annotations

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.database.models import SCHEMA_STATEMENTS


def initialise_database() -> None:
    """Create all registered database tables and indexes."""

    database_type = get_database_type()

    with database_connection() as connection:
        for statement in SCHEMA_STATEMENTS:
            sql = statement

            # PostgreSQL uses BOOLEAN natively, as does SQLite.
            # The current schema is compatible with both engines.
            if database_type not in {"sqlite", "postgresql"}:
                raise RuntimeError("Unsupported database backend.")

            connection.execute(sql)


def check_database_connection() -> bool:
    """Check whether the configured database is reachable."""

    try:
        with database_connection() as connection:
            if get_database_type() == "sqlite":
                connection.execute("SELECT 1")
            else:
                connection.execute("SELECT 1")

        return True

    except Exception:
        return False
