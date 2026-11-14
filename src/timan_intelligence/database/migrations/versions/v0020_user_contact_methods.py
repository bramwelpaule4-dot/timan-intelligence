"""Verified phone and secondary recovery email fields for user accounts."""

VERSION = 20
NAME = "user_contact_methods"


def upgrade(connection) -> None:
    """Add optional contact destinations without changing existing accounts."""

    connection.execute(
        "ALTER TABLE users ADD COLUMN phone_number_e164 TEXT"
    )
    connection.execute(
        "ALTER TABLE users ADD COLUMN phone_verified "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )
    connection.execute(
        "ALTER TABLE users ADD COLUMN recovery_email TEXT"
    )
    connection.execute(
        "ALTER TABLE users ADD COLUMN recovery_email_verified "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )
    connection.execute(
        """
        CREATE INDEX idx_users_phone_number_e164
        ON users(phone_number_e164)
        """
    )
