"""Database-backed one-time-password challenge service for TimanStat."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import uuid

import phonenumbers

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.identity.service import (
    _normalise_email,
    _verify_password as _verify_current_password,
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
CONTACT_VERIFICATION_PURPOSES = {
    "verify_phone": ("sms", "phone_number_e164", "phone_verified"),
    "verify_recovery_email": (
        "email",
        "recovery_email",
        "recovery_email_verified",
    ),
}


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


def _contact_binding_hash(channel: str, destination: str, pepper: str) -> str:
    """Create a keyed, channel-specific fingerprint of an OTP destination."""
    message = f"timanstat-contact:v1:{channel}:{destination}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), message, hashlib.sha256).hexdigest()


def _reauthenticate_user(connection, user_id: str, current_password: str):
    p = _placeholder()
    user = connection.execute(
        f"SELECT password_hash FROM users WHERE id = {p} AND is_active = TRUE",
        (user_id,),
    ).fetchone()
    if user is None or not isinstance(current_password, str):
        return False
    return _verify_current_password(current_password, user["password_hash"])


def set_phone_number_for_verification(
    user_id: str, phone_number: str, current_password: str
) -> str:
    """Replace a user's phone number after password reauthentication.

    The supplied number must be in international format (for example +254...).
    A changed number is always marked unverified until its OTP is confirmed.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise OTPChallengeServiceError("A valid user ID is required.")
    if not isinstance(phone_number, str) or not phone_number.strip().startswith("+"):
        raise OTPChallengeServiceError(
            "Enter the phone number in international format, including its +country code."
        )
    try:
        parsed = phonenumbers.parse(phone_number.strip(), None)
    except phonenumbers.NumberParseException as exc:
        raise OTPChallengeServiceError("Enter a valid international phone number.") from exc
    if not phonenumbers.is_valid_number(parsed):
        raise OTPChallengeServiceError("Enter a valid international phone number.")
    e164 = phonenumbers.format_number(
        parsed, phonenumbers.PhoneNumberFormat.E164
    )
    user_id = user_id.strip()
    p = _placeholder()

    with database_connection() as connection:
        if not _reauthenticate_user(connection, user_id, current_password):
            raise OTPChallengeServiceError("Current password confirmation failed.")
        duplicate = connection.execute(
            f"""
            SELECT id FROM users
            WHERE phone_number_e164 = {p}
              AND phone_verified = TRUE
              AND id <> {p}
            """,
            (e164, user_id),
        ).fetchone()
        if duplicate is not None:
            raise OTPChallengeServiceError(
                "That verified phone number is already associated with another account."
            )
        connection.execute(
            f"""
            UPDATE users
            SET phone_number_e164 = {p},
                phone_verified = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p} AND is_active = TRUE
            """,
            (e164, user_id),
        )
        connection.execute(
            f"""
            UPDATE one_time_password_challenges
            SET invalidated_at = CURRENT_TIMESTAMP
            WHERE user_id = {p} AND channel = 'sms'
              AND consumed_at IS NULL AND invalidated_at IS NULL
            """,
            (user_id,),
        )
    return e164


def set_recovery_email_for_verification(
    user_id: str, recovery_email: str, current_password: str
) -> str:
    """Replace a recovery email after password reauthentication."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise OTPChallengeServiceError("A valid user ID is required.")
    try:
        email = _normalise_email(recovery_email)
    except ValueError as exc:
        raise OTPChallengeServiceError("Enter a valid recovery email address.") from exc

    user_id = user_id.strip()
    p = _placeholder()
    with database_connection() as connection:
        if not _reauthenticate_user(connection, user_id, current_password):
            raise OTPChallengeServiceError("Current password confirmation failed.")
        primary = connection.execute(
            f"SELECT email FROM users WHERE id = {p} AND is_active = TRUE",
            (user_id,),
        ).fetchone()
        if primary is None:
            raise OTPChallengeServiceError("The active user account was not found.")
        if email == str(primary["email"]).strip().lower():
            raise OTPChallengeServiceError(
                "Use an email address different from your primary sign-in email."
            )
        duplicate = connection.execute(
            f"""
            SELECT id FROM users
            WHERE recovery_email = {p}
              AND recovery_email_verified = TRUE
              AND id <> {p}
            """,
            (email, user_id),
        ).fetchone()
        if duplicate is not None:
            raise OTPChallengeServiceError(
                "That verified recovery email is already associated with another account."
            )
        connection.execute(
            f"""
            UPDATE users
            SET recovery_email = {p},
                recovery_email_verified = FALSE,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p} AND is_active = TRUE
            """,
            (email, user_id),
        )
        connection.execute(
            f"""
            UPDATE one_time_password_challenges
            SET invalidated_at = CURRENT_TIMESTAMP
            WHERE user_id = {p} AND channel = 'email'
              AND consumed_at IS NULL AND invalidated_at IS NULL
            """,
            (user_id,),
        )
        # A reset link may have been delivered to the previous recovery
        # address. Revoke all outstanding links whenever that address is
        # changed, including while the replacement address is unverified.
        connection.execute(
            f"""
            DELETE FROM password_reset_tokens
            WHERE user_id = {p}
            """,
            (user_id,),
        )
    return email


def create_otp_challenge(
    user_id: str,
    purpose: str,
    channel: str,
) -> dict[str, str]:
    """Create a short-lived challenge for MFA or contact ownership verification.

    Contact-verification purposes may target a pending, unverified contact.
    Every other purpose requires an already verified contact. The exact
    destination is fingerprinted so a code cannot verify a subsequently
    changed phone number or recovery email.
    """
    user_id, purpose, channel = _validate_identity(user_id, purpose, channel)
    pepper = _get_pepper()
    code = generate_one_time_password()
    challenge_id = str(uuid.uuid4())
    digest = hash_one_time_password(
        code, user_id=user_id, purpose=purpose, pepper=pepper
    )
    p = _placeholder()

    verification = CONTACT_VERIFICATION_PURPOSES.get(purpose)
    if verification is not None and (
        verification[0] != channel
    ):
        raise OTPChallengeServiceError(
            "The OTP purpose does not match the selected delivery channel."
        )

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT is_active, phone_number_e164, phone_verified,
                   recovery_email, recovery_email_verified
            FROM users WHERE id = {p}
            """,
            (user_id,),
        ).fetchone()
        if user is None or not bool(user["is_active"]):
            raise OTPChallengeServiceError("The active user account was not found.")

        if verification is not None:
            _, contact_column, verified_column = verification
            destination = user[contact_column]
            if not isinstance(destination, str) or not destination.strip():
                raise OTPChallengeServiceError(
                    "Add the contact method before requesting its verification code."
                )
            if bool(user[verified_column]):
                raise OTPChallengeServiceError(
                    "This contact method is already verified."
                )
            binding_hash = _contact_binding_hash(channel, destination, pepper)
        else:
            verified_column = (
                "phone_verified" if channel == "sms"
                else "recovery_email_verified"
            )
            destination_column = (
                "phone_number_e164" if channel == "sms"
                else "recovery_email"
            )
            if not bool(user[verified_column]):
                raise OTPChallengeServiceError(
                    "The selected contact method must be verified before OTP delivery."
                )
            destination = user[destination_column]
            if not isinstance(destination, str) or not destination.strip():
                raise OTPChallengeServiceError(
                    "The selected verified contact method is unavailable."
                )
            binding_hash = _contact_binding_hash(channel, destination, pepper)

        connection.execute(
            f"""
            UPDATE one_time_password_challenges
            SET invalidated_at = CURRENT_TIMESTAMP
            WHERE user_id = {p} AND purpose = {p}
              AND consumed_at IS NULL AND invalidated_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
            """,
            (user_id, purpose),
        )
        connection.execute(
            f"""
            INSERT INTO one_time_password_challenges (
                id, user_id, purpose, channel, code_hash,
                expires_at, failed_attempts, max_attempts,
                contact_binding_hash
            )
            VALUES (
                {p}, {p}, {p}, {p}, {p},
                {_expiry_expression()}, 0, {OTP_CHALLENGE_MAX_ATTEMPTS}, {p}
            )
            """,
            (challenge_id, user_id, purpose, channel, digest, binding_hash),
        )

    return {"challenge_id": challenge_id, "code": code, "channel": channel}


def verify_otp_challenge(
    challenge_id: str,
    user_id: str,
    purpose: str,
    code: str,
) -> bool:
    """Verify and atomically consume a challenge, including contact verification."""
    if not isinstance(challenge_id, str) or not challenge_id.strip():
        return False
    try:
        user_id, purpose, _ = _validate_identity(user_id, purpose, "email")
    except OTPChallengeServiceError:
        return False

    pepper = _get_pepper()
    p = _placeholder()
    verification = CONTACT_VERIFICATION_PURPOSES.get(purpose)

    with database_connection() as connection:
        challenge = connection.execute(
            f"""
            SELECT id, channel, code_hash, contact_binding_hash,
                   failed_attempts, max_attempts
            FROM one_time_password_challenges
            WHERE id = {p} AND user_id = {p} AND purpose = {p}
              AND consumed_at IS NULL AND invalidated_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
              AND failed_attempts < max_attempts
            """,
            (challenge_id.strip(), user_id, purpose),
        ).fetchone()
        if challenge is None:
            return False

        if verification is not None:
            expected_channel, contact_column, verified_column = verification
            if challenge["channel"] != expected_channel:
                return False
            user = connection.execute(
                f"""
                SELECT {contact_column}, {verified_column}
                FROM users WHERE id = {p} AND is_active = TRUE
                """,
                (user_id,),
            ).fetchone()
            if user is None or bool(user[verified_column]):
                return False
            destination = user[contact_column]
            if not isinstance(destination, str) or not destination.strip():
                return False
            expected_binding = _contact_binding_hash(
                expected_channel, destination, pepper
            )
            stored_binding = challenge["contact_binding_hash"]
            if not isinstance(stored_binding, str) or not hmac.compare_digest(
                expected_binding, stored_binding
            ):
                return False

        is_valid = verify_one_time_password(
            code, challenge["code_hash"],
            user_id=user_id, purpose=purpose, pepper=pepper,
        )
        if not is_valid:
            connection.execute(
                f"""
                UPDATE one_time_password_challenges
                SET failed_attempts = failed_attempts + 1
                WHERE id = {p} AND user_id = {p} AND purpose = {p}
                  AND consumed_at IS NULL AND invalidated_at IS NULL
                  AND expires_at > CURRENT_TIMESTAMP
                  AND failed_attempts < max_attempts
                """,
                (challenge_id.strip(), user_id, purpose),
            )
            return False

        consumed = connection.execute(
            f"""
            UPDATE one_time_password_challenges
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE id = {p} AND user_id = {p} AND purpose = {p}
              AND consumed_at IS NULL AND invalidated_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
              AND failed_attempts < max_attempts
            """,
            (challenge_id.strip(), user_id, purpose),
        )
        if consumed.rowcount != 1:
            return False

        if verification is not None:
            _, contact_column, verified_column = verification
            # Compare the exact destination again in the UPDATE. If it was
            # changed concurrently, the code is consumed but cannot verify it.
            verified = connection.execute(
                f"""
                UPDATE users
                SET {verified_column} = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = {p} AND is_active = TRUE
                  AND {contact_column} = {p}
                  AND {verified_column} = FALSE
                """,
                (user_id, destination),
            )
            if verified.rowcount != 1:
                return False

        return True



def get_contact_method_status(user_id: str) -> dict[str, object]:
    """Return the authenticated user's configured contact methods."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise OTPChallengeServiceError("A valid user ID is required.")
    p = _placeholder()
    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT recovery_email, recovery_email_verified,
                   phone_number_e164, phone_verified
            FROM users
            WHERE id = {p} AND is_active = TRUE
            """,
            (user_id.strip(),),
        ).fetchone()
    if user is None:
        raise OTPChallengeServiceError("The active user account was not found.")
    return {
        "recovery_email": user["recovery_email"],
        "recovery_email_verified": bool(user["recovery_email_verified"]),
        "phone_number_e164": user["phone_number_e164"],
        "phone_verified": bool(user["phone_verified"]),
    }


def invalidate_otp_challenge(
    challenge_id: str, user_id: str, purpose: str
) -> bool:
    """Invalidate an unconsumed challenge after delivery failure or cancellation."""
    if not isinstance(challenge_id, str) or not challenge_id.strip():
        return False
    if not isinstance(user_id, str) or not user_id.strip():
        return False
    if not isinstance(purpose, str) or not PURPOSE_PATTERN.fullmatch(purpose):
        return False
    p = _placeholder()
    with database_connection() as connection:
        result = connection.execute(
            f"""
            UPDATE one_time_password_challenges
            SET invalidated_at = CURRENT_TIMESTAMP
            WHERE id = {p} AND user_id = {p} AND purpose = {p}
              AND consumed_at IS NULL AND invalidated_at IS NULL
            """,
            (challenge_id.strip(), user_id.strip(), purpose),
        )
    return result.rowcount == 1
