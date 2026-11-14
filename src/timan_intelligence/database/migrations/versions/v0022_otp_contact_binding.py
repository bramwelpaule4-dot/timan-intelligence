"""Bind each OTP challenge to the contact destination it was issued for."""

VERSION = 22
NAME = "otp_contact_binding"


def upgrade(connection) -> None:
    """Store a keyed contact binding to prevent stale-code contact swaps."""

    connection.execute(
        "ALTER TABLE one_time_password_challenges "
        "ADD COLUMN contact_binding_hash TEXT"
    )
