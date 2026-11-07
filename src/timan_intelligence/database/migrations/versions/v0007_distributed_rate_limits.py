"""Shared database-backed rate-limit state migration for TimanStat."""

from __future__ import annotations

VERSION = 7
NAME = "distributed_rate_limits"


def upgrade(connection) -> None:
    """Create shared rate-limit state for all application workers."""
    connection.execute(
        """
        CREATE TABLE rate_limit_states (
            key_hash TEXT PRIMARY KEY,
            window_started_at DOUBLE PRECISION NOT NULL,
            failure_count INTEGER NOT NULL DEFAULT 0
                CHECK (failure_count >= 0),
            locked_until DOUBLE PRECISION
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_rate_limit_locked_until
        ON rate_limit_states(locked_until)
        """
    )
