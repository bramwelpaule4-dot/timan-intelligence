"""Increase shared rate-limit timestamp precision for PostgreSQL."""

from __future__ import annotations

from timan_intelligence.database.connection import get_database_type


VERSION = 8
NAME = "rate_limit_timestamp_precision"


def upgrade(connection) -> None:
    """Convert existing PostgreSQL rate-limit timestamps to double precision.

    SQLite stores these numeric values as 64-bit floating point already.
    """
    if get_database_type() != "postgresql":
        return

    # Rate-limit records are short-lived. Clear any values created by an
    # earlier REAL (float4) schema so no rounded epoch timestamps survive.
    connection.execute("DELETE FROM rate_limit_states")

    connection.execute(
        """
        ALTER TABLE rate_limit_states
        ALTER COLUMN window_started_at
        TYPE DOUBLE PRECISION
        USING window_started_at::DOUBLE PRECISION
        """
    )
    connection.execute(
        """
        ALTER TABLE rate_limit_states
        ALTER COLUMN locked_until
        TYPE DOUBLE PRECISION
        USING locked_until::DOUBLE PRECISION
        """
    )
