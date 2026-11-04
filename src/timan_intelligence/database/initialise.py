
"""Database initialisation for TimanStat."""

from __future__ import annotations

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.database.migrations.runner import run_migrations


def initialise_database() -> None:
    """Initialise or upgrade the database using versioned migrations."""

    database_type = get_database_type()

    if database_type not in {"sqlite", "postgresql"}:
        raise RuntimeError("Unsupported database backend.")

    with database_connection() as connection:
        run_migrations(connection)


def check_database_connection() -> bool:
    """Check whether the configured database is reachable."""

    try:
        with database_connection() as connection:
            connection.execute("SELECT 1")

        return True

    except Exception:
        return False
