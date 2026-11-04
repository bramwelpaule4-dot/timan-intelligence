
"""TOTP enrolment and replay-protection database migration."""

from __future__ import annotations


VERSION = 2
NAME = "totp_enrolment"


def upgrade(connection) -> None:
    """Add persistent TOTP enrolment and replay-protection fields."""

    statements = [
        """
        ALTER TABLE users
        ADD COLUMN totp_enabled BOOLEAN NOT NULL DEFAULT FALSE
        """,
        """
        ALTER TABLE users
        ADD COLUMN totp_secret_encrypted TEXT
        """,
        """
        ALTER TABLE users
        ADD COLUMN totp_pending_secret_encrypted TEXT
        """,
        """
        ALTER TABLE users
        ADD COLUMN totp_last_accepted_counter BIGINT
            CHECK (
                totp_last_accepted_counter IS NULL
                OR totp_last_accepted_counter >= 0
            )
        """,
        """
        ALTER TABLE users
        ADD COLUMN totp_enrolled_at TIMESTAMP
        """,
        """
        ALTER TABLE users
        ADD COLUMN totp_pending_created_at TIMESTAMP
        """,
    ]

    for statement in statements:
        connection.execute(statement)
