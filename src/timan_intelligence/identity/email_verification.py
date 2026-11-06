
"""Email verification token services for TimanStat."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


DEFAULT_TOKEN_EXPIRY_MINUTES = 30
MAX_TOKEN_EXPIRY_MINUTES = 1440
TOKEN_BYTES = 32


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""

    return "%s" if get_database_type() == "postgresql" else "?"


def _hash_token(token: str) -> str:
    """Return the SHA-256 hash of a verification token."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_email_verification_token(
    user_id: str,
    expiry_minutes: int = DEFAULT_TOKEN_EXPIRY_MINUTES,
) -> str:
    """
    Create a new email verification token for an active user.

    Any previous outstanding token for the user is invalidated.

    Only the SHA-256 hash is stored in the database.

    Returns:
        The plaintext token. It should be delivered to the user
        through the configured email delivery service.

    Raises:
        ValueError: If the user ID or expiry period is invalid,
            or if the user does not exist or is inactive.
    """

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("A valid user ID is required.")

    if (
        isinstance(expiry_minutes, bool)
        or not isinstance(expiry_minutes, int)
        or not 1 <= expiry_minutes <= MAX_TOKEN_EXPIRY_MINUTES
    ):
        raise ValueError(
            "Token expiry must be between 1 and 1440 minutes."
        )

    user_id = user_id.strip()

    token = secrets.token_urlsafe(TOKEN_BYTES)
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

        # Invalidate any previously issued token for this user.
        connection.execute(
            f"""
            DELETE FROM email_verification_tokens
            WHERE user_id = {p}
            """,
            (user_id,),
        )

        connection.execute(
            f"""
            INSERT INTO email_verification_tokens (
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


def verify_email_token(token: str) -> bool:
    """
    Verify an email verification token and activate email verification.

    A token is accepted only when:
    - It exists in the database.
    - It has not already been consumed.
    - It has not expired.
    - Its associated user account is active.

    Successful verification consumes the token and marks the
    associated user's email as verified in the same transaction.

    Returns:
        True if verification succeeds; otherwise False.
    """

    if not isinstance(token, str):
        return False

    token = token.strip()

    if not token or len(token) > 512:
        return False

    token_hash = _hash_token(token)
    p = _placeholder()

    with database_connection() as connection:
        verification = connection.execute(
            f"""
            SELECT
                tokens.id,
                tokens.user_id
            FROM email_verification_tokens AS tokens
            INNER JOIN users AS users
                ON users.id = tokens.user_id
            WHERE tokens.token_hash = {p}
              AND tokens.consumed_at IS NULL
              AND tokens.expires_at > CURRENT_TIMESTAMP
              AND users.is_active = TRUE
            """,
            (token_hash,),
        ).fetchone()

        if verification is None:
            return False

        # Consume the token only if it remains valid and unused.
        consumed = connection.execute(
            f"""
            UPDATE email_verification_tokens
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND consumed_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            """,
            (verification["id"],),
        )

        if consumed.rowcount != 1:
            return False

        # Mark the associated user's email as verified.
        updated = connection.execute(
            f"""
            UPDATE users
            SET email_verified = TRUE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND is_active = TRUE
            """,
            (verification["user_id"],),
        )

        if updated.rowcount != 1:
            raise RuntimeError(
                "Email verification could not update the user account."
            )

    return True
