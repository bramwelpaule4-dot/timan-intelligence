"""Cryptographic primitives for short-lived one-time verification codes.

This module deliberately does not send codes or persist them. Delivery and
single-use database consumption belong to the identity verification service.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets


OTP_LENGTH = 6
OTP_PATTERN = re.compile(r"^[0-9]{6}$")
MIN_PEPPER_BYTES = 32


class OneTimePasswordError(ValueError):
    """Raised when OTP input or cryptographic configuration is invalid."""


def generate_one_time_password() -> str:
    """Generate a cryptographically random six-digit decimal OTP."""
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def _validate_context(user_id: str, purpose: str, pepper: str | bytes) -> bytes:
    if not isinstance(user_id, str) or not user_id.strip():
        raise OneTimePasswordError("A valid user ID is required.")

    if (
        not isinstance(purpose, str)
        or not purpose.strip()
        or len(purpose) > 64
        or not re.fullmatch(r"[A-Za-z0-9_.:-]+", purpose)
    ):
        raise OneTimePasswordError("A valid OTP purpose is required.")

    if isinstance(pepper, str):
        pepper_bytes = pepper.encode("utf-8")
    elif isinstance(pepper, bytes):
        pepper_bytes = pepper
    else:
        raise OneTimePasswordError("The OTP pepper must be text or bytes.")

    if len(pepper_bytes) < MIN_PEPPER_BYTES:
        raise OneTimePasswordError(
            "The OTP pepper must contain at least 32 bytes."
        )

    return pepper_bytes


def hash_one_time_password(
    code: str,
    *,
    user_id: str,
    purpose: str,
    pepper: str | bytes,
) -> str:
    """Return a keyed SHA-256 digest bound to one user and OTP purpose.

    The server-side pepper must be stored separately from the database.
    HMAC prevents a database-only disclosure from enabling practical
    offline enumeration of the six-digit OTP space.
    """
    if not isinstance(code, str) or not OTP_PATTERN.fullmatch(code):
        raise OneTimePasswordError("The OTP must contain exactly six digits.")

    pepper_bytes = _validate_context(user_id, purpose, pepper)
    message = f"timanstat-otp:v1:{user_id.strip()}:{purpose}:{code}".encode(
        "utf-8"
    )
    return hmac.new(pepper_bytes, message, hashlib.sha256).hexdigest()


def verify_one_time_password(
    code: str,
    expected_digest: str,
    *,
    user_id: str,
    purpose: str,
    pepper: str | bytes,
) -> bool:
    """Verify a six-digit OTP using constant-time digest comparison."""
    if not isinstance(expected_digest, str):
        return False

    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
        return False

    try:
        actual_digest = hash_one_time_password(
            code,
            user_id=user_id,
            purpose=purpose,
            pepper=pepper,
        )
    except OneTimePasswordError:
        return False

    return hmac.compare_digest(actual_digest, expected_digest)
