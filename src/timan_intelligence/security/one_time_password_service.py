"""Database-backed one-time-password challenge service for TimanStat."""

from __future__ import annotations

import os
import re
import uuid

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.security.one_time_password import (
    generate_one_time_password,
    hash_one_time_password,
    verify_one_time_password,
)


OTP_CHALLENGE_TTL_SECONDS = 300
OTP_CHALLENGE_MAX_ATTEMPTS = 5
PURPOSE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
VALID_CHANNELS = {"sms", "email"}


class OTPChallengeServiceError(RuntimeError):
    """Raised when an OTP challenge cannot safely be created or processed."""


def _placeholder() -> str:
    return "%s" if get_database_type() == "postgresql" else "?"


def _validate_identity(user_id: str, purpose: str, channel: str) -> tuple[str, str, str]:
    if not isinstance(user_id, str) or not user_id.strip():
        raise OTPChallengeServiceError("A valid user ID is required.")
    if not isinstance(purpose, str) or not PURPOSE_PATTERN.fullmatch(purpose):
        raise OTPChallengeServiceError("A valid OTP purpose is required.")
    if not isinstance(channel, str) or channel not in VALID_CHANNELS:
        raise OTPChallengeServiceError("The OTP channel must be sms or email.")
    return user_id.strip(), purpose, channel


def _get_pepper() -> str:
    """Read the OTP pepper from server-side configuration, never from the database."""
    pepper = os.getenv("TIMANSTAT_OTP_PEPPER", "").strip()
    if not pepper:
        try:
            import streamlit as st

            pepper = str(st.secrets.get("TIMANSTAT_OTP_PEPPER", "")).strip()
        except Exception:
            pepper = ""
    if len(pepper.encode("utf-8")) < 32:
        raise OTPChallengeServiceError(
            "OTP verification is not configured. Set TIMANSTAT_OTP_PEPPER "
            "to a random secret containing at least 32 bytes."
        )
    return pepper


def _expiry_expression() -> str:
    if get_database_type() == "postgresql":
        return "CURRENT_TIMESTAMP + INTERVAL '300 seconds'"
    return "datetime('now', '+300 seconds')"


def create_otp_challenge(
    user_id: str,
    purpose: str,
    channel: str,
) -> dict[str, str]:
    """Create a five-minute OTP challenge for a verified contact method.

    The returned code is intended for the caller's delivery adapter. This
    service never sends or logs it. A new challenge invalidates prior active
    challenges for the same user and purpose.
    """
    user_id, purpose, channel = _validate_identity(user_id, purpose, channel)
    pepper = _get_pepper()
    code = generate_one_time_password()
    challenge_id = str(uuid.uuid4())
    digest = hash_one_time_password(
        code,
        user_id=user_id,
        purpose=purpose,
        pepper=pepper,
    )
    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT is_active, phone_verified, recovery_email_verified
            FROM users
            WHERE id = {p}
            """,
            (user_id,),
        ).fetchone()

        if user is None or not bool(user["is_active"]):
            raise OTPChallengeServiceError("The active user account was not found.")

        verified_column = (
            "phone_verified" if channel == "sms" else "recovery_email_verified"
        )
        if not bool(user[verified_column]):
            raise OTPChallengeServiceError(
                "The selected contact method must be verified before OTP delivery."
            )

        connection.execute(
            f"""
            UPDATE one_time_password_challenges
            SET invalidated_at = CURRENT_TIMESTAMP
            WHERE user_id = {p}
              AND purpose = {p}
              AND consumed_at IS NULL
              AND invalidated_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            """,
            (user_id, purpose),
        )

        connection.execute(
            f"""
            INSERT INTO one_time_password_challenges (
                id, user_id, purpose, channel, code_hash,
                expires_at, failed_attempts, max_attempts
            )
            VALUES (
                {p}, {p}, {p}, {p}, {p},
                {_expiry_expression()}, 0, {OTP_CHALLENGE_MAX_ATTEMPTS}
            )
            """,
            (challenge_id, user_id, purpose, channel, digest),
        )

    return {"challenge_id": challenge_id, "code": code, "channel": channel}


def verify_otp_challenge(
    challenge_id: str,
    user_id: str,
    purpose: str,
    code: str,
) -> bool:
    """Verify and atomically consume a challenge, or count a failed attempt.

    A challenge is accepted only once, before expiry, for its original user
    and purpose, and before its attempt limit is reached.
    """
    if not isinstance(challenge_id, str) or not challenge_id.strip():
        return False

    try:
        user_id, purpose, _ = _validate_identity(user_id, purpose, "email")
    except OTPChallengeServiceError:
        return False

    pepper = _get_pepper()
    p = _placeholder()

    with database_connection() as connection:
        challenge = connection.execute(
            f"""
            SELECT id, code_hash, failed_attempts, max_attempts
            FROM one_time_password_challenges
            WHERE id = {p}
              AND user_id = {p}
              AND purpose = {p}
              AND consumed_at IS NULL
              AND invalidated_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
              AND failed_attempts < max_attempts
            """,
            (challenge_id.strip(), user_id, purpose),
        ).fetchone()

        if challenge is None:
            return False

        is_valid = verify_one_time_password(
            code,
            challenge["code_hash"],
            user_id=user_id,
            purpose=purpose,
            pepper=pepper,
        )

        if not is_valid:
            connection.execute(
                f"""
                UPDATE one_time_password_challenges
                SET failed_attempts = failed_attempts + 1
                WHERE id = {p}
                  AND user_id = {p}
                  AND purpose = {p}
                  AND consumed_at IS NULL
                  AND invalidated_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                  AND failed_attempts < max_attempts
                """,
                (challenge_id.strip(), user_id, purpose),
            )
            return False

        result = connection.execute(
            f"""
            UPDATE one_time_password_challenges
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND user_id = {p}
              AND purpose = {p}
              AND consumed_at IS NULL
              AND invalidated_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
              AND failed_attempts < max_attempts
            """,
            (challenge_id.strip(), user_id, purpose),
        )
        return result.rowcount == 1
