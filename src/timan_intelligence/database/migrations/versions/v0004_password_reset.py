
"""Password-reset token storage migration for TimanStat."""

from __future__ import annotations


VERSION = 4
NAME = "password_reset"


def upgrade(connection) -> None:
    """Create secure, single-use password-reset token storage."""

    connection.execute(
        """
        CREATE TABLE password_reset_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE
                REFERENCES users(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            consumed_at TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX idx_password_reset_expires
        ON password_reset_tokens(expires_at)
        """
    )
