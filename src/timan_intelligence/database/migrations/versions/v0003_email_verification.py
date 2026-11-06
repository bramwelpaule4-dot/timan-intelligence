
"""Email verification token storage migration for TimanStat."""

from __future__ import annotations


VERSION = 3
NAME = "email_verification"


def upgrade(connection) -> None:
    """Create secure, single-use email verification token storage."""

    connection.execute(
        """
        CREATE TABLE email_verification_tokens (
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
        CREATE INDEX idx_email_verification_expires
        ON email_verification_tokens(expires_at)
        """
    )
