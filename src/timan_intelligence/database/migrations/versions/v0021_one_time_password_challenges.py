"""Short-lived, single-use OTP challenge storage."""

VERSION = 21
NAME = "one_time_password_challenges"


def upgrade(connection) -> None:
    """Create database storage for hashed one-time verification challenges."""

    connection.execute(
        """
        CREATE TABLE one_time_password_challenges (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL
                REFERENCES users(id) ON DELETE CASCADE,
            purpose TEXT NOT NULL,
            channel TEXT NOT NULL
                CHECK (channel IN ('sms', 'email')),
            code_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            failed_attempts INTEGER NOT NULL DEFAULT 0
                CHECK (failed_attempts >= 0),
            max_attempts INTEGER NOT NULL DEFAULT 5
                CHECK (max_attempts > 0),
            consumed_at TIMESTAMP,
            invalidated_at TIMESTAMP
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX idx_otp_challenges_user_purpose
        ON one_time_password_challenges(user_id, purpose, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_otp_challenges_expires
        ON one_time_password_challenges(expires_at)
        """
    )
