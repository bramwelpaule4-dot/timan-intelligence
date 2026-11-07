
"""Secure password-reset token services for TimanStat."""

from __future__ import annotations

import hashlib
import secrets
import uuid

from datetime import datetime, timedelta, timezone

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.identity.service import _hash_password


DEFAULT_PASSWORD_RESET_EXPIRY_MINUTES = 30
MAX_PASSWORD_RESET_EXPIRY_MINUTES = 1440
PASSWORD_RESET_TOKEN_BYTES = 32
MAX_PASSWORD_RESET_TOKEN_LENGTH = 512


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""

    return "%s" if get_database_type() == "postgresql" else "?"


def _hash_token(token: str) -> str:
    """Return the SHA-256 hash of a password-reset token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(
    user_id: str,
    expiry_minutes: int = DEFAULT_PASSWORD_RESET_EXPIRY_MINUTES,
) -> str:
    """
    Create a new password-reset token for an active user.

    Any previously issued password-reset token for the user
    is invalidated. Only the token hash is stored.
    """

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("A valid user ID is required.")

    if (
        isinstance(expiry_minutes, bool)
        or not isinstance(expiry_minutes, int)
        or not 1 <= expiry_minutes <= MAX_PASSWORD_RESET_EXPIRY_MINUTES
    ):
        raise ValueError(
            "Password-reset token expiry must be between "
            "1 and 1440 minutes."
        )

    user_id = user_id.strip()

    token = secrets.token_urlsafe(PASSWORD_RESET_TOKEN_BYTES)
    token_hash = _hash_token(token)
    token_id = str(uuid.uuid4())

    expires_at = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        + timedelta(minutes=expiry_minutes)
    )

    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT id
            FROM users
            WHERE id = {p}
              AND is_active = TRUE
            """,
            (user_id,),
        ).fetchone()

        if user is None:
            raise ValueError(
                "The requested user does not exist or is inactive."
            )

        connection.execute(
            f"""
            DELETE FROM password_reset_tokens
            WHERE user_id = {p}
            """,
            (user_id,),
        )

        connection.execute(
            f"""
            INSERT INTO password_reset_tokens (
                id,
                user_id,
                token_hash,
                expires_at
            )
            VALUES ({p}, {p}, {p}, {p})
            """,
            (
                token_id,
                user_id,
                token_hash,
                expires_at,
            ),
        )

    return token


def reset_password_with_token(
    token: str,
    new_password: str,
) -> bool:
    """
    Replace a user's password using a valid password-reset token.

    Password replacement, token consumption, and account-wide
    session revocation occur in the same database transaction.

    Incrementing users.session_version invalidates every existing
    authenticated session associated with the account.

    Returns:
        True if the password was successfully changed.
        False if the token is invalid, expired, consumed, or
        belongs to an inactive account.

    Raises:
        ValueError: If the new password does not meet requirements.
    """

    if not isinstance(token, str):
        return False

    token = token.strip()

    if (
        not token
        or len(token) > MAX_PASSWORD_RESET_TOKEN_LENGTH
    ):
        return False

    # Validate and hash before changing database state.
    new_password_hash = _hash_password(new_password)

    token_hash = _hash_token(token)
    p = _placeholder()

    with database_connection() as connection:
        reset_record = connection.execute(
            f"""
            SELECT
                tokens.id,
                tokens.user_id
            FROM password_reset_tokens AS tokens
            INNER JOIN users AS users
                ON users.id = tokens.user_id
            WHERE tokens.token_hash = {p}
              AND tokens.consumed_at IS NULL
              AND tokens.expires_at > CURRENT_TIMESTAMP
              AND users.is_active = TRUE
            """,
            (token_hash,),
        ).fetchone()

        if reset_record is None:
            return False

        # Consume the token conditionally to prevent reuse.
        consumed = connection.execute(
            f"""
            UPDATE password_reset_tokens
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND consumed_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            """,
            (reset_record["id"],),
        )

        if consumed.rowcount != 1:
            return False

        # Change the password and increment the account's session
        # version together. All existing sessions will fail their
        # next session-version validation.
        updated = connection.execute(
            f"""
            UPDATE users
            SET password_hash = {p},
                session_version = session_version + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND is_active = TRUE
            """,
            (
                new_password_hash,
                reset_record["user_id"],
            ),
        )

        if updated.rowcount != 1:
            raise RuntimeError(
                "Password reset could not update the user account."
            )

        # Invalidate any other outstanding reset token for this user.
        connection.execute(
            f"""
            DELETE FROM password_reset_tokens
            WHERE user_id = {p}
              AND id != {p}
            """,
            (
                reset_record["user_id"],
                reset_record["id"],
            ),
        )

    return True
