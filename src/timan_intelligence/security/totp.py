
"""Time-based one-time password support for TimanStat.

Implements RFC 6238 using HMAC-SHA1 and RFC 4226 HOTP truncation.
Compatible with standard authenticator applications.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

from urllib.parse import quote, urlencode


DEFAULT_DIGITS = 6
DEFAULT_PERIOD_SECONDS = 30
DEFAULT_WINDOW = 1
DEFAULT_SECRET_BYTES = 20
DEFAULT_ISSUER = "TimanStat"


class TOTPError(ValueError):
    """Raised when TOTP configuration or input is invalid."""


def generate_totp_secret(
    secret_bytes: int = DEFAULT_SECRET_BYTES,
) -> str:
    """Generate a cryptographically secure Base32 TOTP secret."""

    if (
        isinstance(secret_bytes, bool)
        or not isinstance(secret_bytes, int)
        or not 16 <= secret_bytes <= 64
    ):
        raise TOTPError(
            "secret_bytes must be an integer between 16 and 64."
        )

    secret = secrets.token_bytes(secret_bytes)

    return base64.b32encode(secret).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    """Decode and validate a Base32 TOTP secret."""

    if not isinstance(secret, str) or not secret:
        raise TOTPError("A valid TOTP secret is required.")

    normalised = secret.strip().upper()

    if not normalised:
        raise TOTPError("A valid TOTP secret is required.")

    try:
        encoded = normalised + "=" * (-len(normalised) % 8)
        decoded = base64.b32decode(encoded, casefold=False)
    except (ValueError, base64.binascii.Error) as exc:
        raise TOTPError("The TOTP secret is not valid Base32.") from exc

    if len(decoded) < 16:
        raise TOTPError("The TOTP secret is too short.")

    return decoded


def _validate_configuration(
    digits: int,
    period_seconds: int,
    window: int,
) -> None:
    """Validate TOTP configuration values."""

    if (
        isinstance(digits, bool)
        or not isinstance(digits, int)
        or digits != 6
    ):
        raise TOTPError("Only six-digit TOTP codes are supported.")

    if (
        isinstance(period_seconds, bool)
        or not isinstance(period_seconds, int)
        or period_seconds <= 0
    ):
        raise TOTPError("period_seconds must be a positive integer.")

    if (
        isinstance(window, bool)
        or not isinstance(window, int)
        or not 0 <= window <= 10
    ):
        raise TOTPError("window must be an integer between 0 and 10.")


def _generate_code(
    secret_bytes: bytes,
    counter: int,
    digits: int = DEFAULT_DIGITS,
) -> str:
    """Generate an HOTP code for a given counter."""

    if (
        isinstance(counter, bool)
        or not isinstance(counter, int)
        or counter < 0
    ):
        raise TOTPError("The TOTP counter must be a non-negative integer.")

    message = struct.pack(">Q", counter)

    digest = hmac.new(
        secret_bytes,
        message,
        hashlib.sha1,
    ).digest()

    offset = digest[-1] & 0x0F

    binary_code = struct.unpack(
        ">I",
        digest[offset:offset + 4],
    )[0] & 0x7FFFFFFF

    otp = binary_code % (10 ** digits)

    return str(otp).zfill(digits)


def _get_timestamp(value: float | None) -> float:
    """Return a valid Unix timestamp."""

    timestamp = time.time() if value is None else value

    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, (int, float))
    ):
        raise TOTPError("The timestamp must be a valid number.")

    if not float("-inf") < timestamp < float("inf"):
        raise TOTPError("The timestamp must be finite.")

    if timestamp < 0:
        raise TOTPError("The timestamp cannot be negative.")

    return float(timestamp)


def generate_totp_code(
    secret: str,
    at_time: float | None = None,
    digits: int = DEFAULT_DIGITS,
    period_seconds: int = DEFAULT_PERIOD_SECONDS,
) -> str:
    """Generate a TOTP code for a secret and timestamp.

    This function is primarily useful for testing and controlled
    integrations. Production login should verify user-supplied codes.
    """

    _validate_configuration(
        digits,
        period_seconds,
        window=0,
    )

    timestamp = _get_timestamp(at_time)
    secret_bytes = _decode_secret(secret)
    counter = int(timestamp // period_seconds)

    return _generate_code(
        secret_bytes,
        counter,
        digits,
    )


def verify_totp_code(
    secret: str,
    code: str,
    at_time: float | None = None,
    digits: int = DEFAULT_DIGITS,
    period_seconds: int = DEFAULT_PERIOD_SECONDS,
    window: int = DEFAULT_WINDOW,
    last_accepted_counter: int | None = None,
) -> int | None:
    """Verify a TOTP code and return its matched counter.

    Returns:
        The matched time counter when verification succeeds.
        None when the code is invalid, expired or already used.

    The caller must persist the returned counter against the user
    account to enforce replay protection across login attempts.
    """

    _validate_configuration(
        digits,
        period_seconds,
        window,
    )

    secret_bytes = _decode_secret(secret)

    if not isinstance(code, str):
        return None

    submitted_code = code.strip()

    if (
        len(submitted_code) != digits
        or not submitted_code.isascii()
        or not submitted_code.isdigit()
    ):
        return None

    if last_accepted_counter is not None:
        if (
            isinstance(last_accepted_counter, bool)
            or not isinstance(last_accepted_counter, int)
            or last_accepted_counter < 0
        ):
            raise TOTPError(
                "last_accepted_counter must be a non-negative integer."
            )

    timestamp = _get_timestamp(at_time)
    current_counter = int(timestamp // period_seconds)

    for counter in range(
        max(0, current_counter - window),
        current_counter + window + 1,
    ):
        if (
            last_accepted_counter is not None
            and counter <= last_accepted_counter
        ):
            continue

        expected_code = _generate_code(
            secret_bytes,
            counter,
            digits,
        )

        if hmac.compare_digest(submitted_code, expected_code):
            return counter

    return None


def build_totp_provisioning_uri(
    secret: str,
    account_name: str,
    issuer: str = DEFAULT_ISSUER,
    digits: int = DEFAULT_DIGITS,
    period_seconds: int = DEFAULT_PERIOD_SECONDS,
) -> str:
    """Build an otpauth URI for authenticator-app enrolment."""

    _validate_configuration(
        digits,
        period_seconds,
        window=0,
    )

    _decode_secret(secret)

    if not isinstance(account_name, str) or not account_name.strip():
        raise TOTPError("A valid account name is required.")

    if not isinstance(issuer, str) or not issuer.strip():
        raise TOTPError("A valid issuer name is required.")

    account = account_name.strip()
    issuer_name = issuer.strip()

    label = quote(
        f"{issuer_name}:{account}",
        safe="",
    )

    parameters = urlencode(
        {
            "secret": secret.strip().upper(),
            "issuer": issuer_name,
            "algorithm": "SHA1",
            "digits": digits,
            "period": period_seconds,
        }
    )

    return f"otpauth://totp/{label}?{parameters}"
