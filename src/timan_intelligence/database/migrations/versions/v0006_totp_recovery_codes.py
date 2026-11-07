"""One-time TOTP recovery-code storage migration for TimanStat."""

from __future__ import annotations


VERSION = 6
NAME = "totp_recovery_codes"


def upgrade(connection) -> None:
    """Create storage for hashed, single-use TOTP recovery codes."""

    connection.execute(
        """
        CREATE TABLE totp_recovery_codes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            code_hash TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            consumed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_totp_recovery_codes_user
        ON totp_recovery_codes(user_id)
        """
    )
