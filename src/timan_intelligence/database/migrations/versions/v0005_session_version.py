
"""User session-version migration for TimanStat."""

from __future__ import annotations


VERSION = 5
NAME = "session_version"


def upgrade(connection) -> None:
    """Add a version counter for account-wide session revocation."""

    connection.execute(
        """
        ALTER TABLE users
        ADD COLUMN session_version INTEGER NOT NULL DEFAULT 0
            CHECK (session_version >= 0)
        """
    )
