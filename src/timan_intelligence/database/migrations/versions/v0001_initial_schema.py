
"""Initial TimanStat database schema migration."""

from __future__ import annotations

from timan_intelligence.database.models import SCHEMA_STATEMENTS


VERSION = 1
NAME = "initial_schema"


def upgrade(connection) -> None:
    """Create the initial database schema."""

    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)
