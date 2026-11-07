"""Single-use recovery-code services for TOTP-protected TimanStat accounts."""

from __future__ import annotations

import hashlib
import re
import secrets
import uuid

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.security.totp_rate_limit import totp_attempt_limiter


RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_BYTES = 16
_RECOVERY_CODE_PATTERN = re.compile(r"^[A-F0-9]{32}$")


class RecoveryCodeError(Exception):
    """Raised when recovery-code management cannot be completed."""


def _placeholder() -> str:
    """Return the configured database parameter placeholder."""

    return "%s" if get_database_type() == "postgresql" else "?"


def _validate_user_id(user_id: str) -> str:
    if not isinstance(user_id, str) or not user_id.strip():
        raise RecoveryCodeError("A valid user ID is required.")
    return user_id.strip()


def _normalise_code(code: str) -> str | None:
    if not isinstance(code, str):
        return None
    normalised = code.strip().replace("-", "").replace(" ", "").upper()
    if not _RECOVERY_CODE_PATTERN.fullmatch(normalised):
        return None
    return normalised


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def generate_recovery_codes(user_id: str) -> list[str]:
    """Replace the user's recovery-code set and return plaintext codes once.

    Only active accounts with TOTP enabled may generate recovery codes.
    Existing codes are invalidated in the same transaction as insertion.
    """

    user_id = _validate_user_id(user_id)
    codes = [
        secrets.token_hex(RECOVERY_CODE_BYTES).upper()
        for _ in range(RECOVERY_CODE_COUNT)
    ]
    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT id
            FROM users
            WHERE id = {p}
              AND is_active = TRUE
              AND totp_enabled = TRUE
            """,
            (user_id,),
        ).fetchone()

        if user is None:
            raise RecoveryCodeError(
                "Recovery codes require an active TOTP-protected account."
            )

        connection.execute(
            f"DELETE FROM totp_recovery_codes WHERE user_id = {p}",
            (user_id,),
        )

        for code in codes:
            connection.execute(
                f"""
                INSERT INTO totp_recovery_codes (id, user_id, code_hash)
                VALUES ({p}, {p}, {p})
                """,
                (str(uuid.uuid4()), user_id, _hash_code(code)),
            )

        connection.execute(
            f"""
            UPDATE users
            SET session_version = session_version + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND is_active = TRUE
              AND totp_enabled = TRUE
            """,
            (user_id,),
        )

    return [f"{code[:8]}-{code[8:16]}-{code[16:24]}-{code[24:]}" for code in codes]


def consume_recovery_code(user_id: str, code: str) -> bool:
    """Atomically consume one valid, unused recovery code."""

    user_id = _validate_user_id(user_id)

    if totp_attempt_limiter.is_locked(user_id, "recovery"):
        return False

    normalised = _normalise_code(code)
    if normalised is None:
        totp_attempt_limiter.record_failure(user_id, "recovery")
        return False

    p = _placeholder()
    with database_connection() as connection:
        result = connection.execute(
            f"""
            UPDATE totp_recovery_codes
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE user_id = {p}
              AND code_hash = {p}
              AND consumed_at IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM users
                  WHERE users.id = {p}
                    AND users.is_active = TRUE
                    AND users.totp_enabled = TRUE
              )
            """,
            (user_id, _hash_code(normalised), user_id),
        )

        accepted = result.rowcount == 1

    if accepted:
        totp_attempt_limiter.record_success(user_id, "recovery")
        return True

    totp_attempt_limiter.record_failure(user_id, "recovery")
    return False


def get_recovery_code_count(user_id: str) -> int:
    """Return the number of unused recovery codes for an active account."""

    user_id = _validate_user_id(user_id)
    p = _placeholder()

    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS remaining
            FROM totp_recovery_codes
            WHERE user_id = {p}
              AND consumed_at IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM users
                  WHERE users.id = {p}
                    AND users.is_active = TRUE
                    AND users.totp_enabled = TRUE
              )
            """,
            (user_id, user_id),
        ).fetchone()

    return int(row["remaining"]) if row is not None else 0


def regenerate_recovery_codes(
    user_id: str,
    current_password: str,
    authenticator_code: str,
) -> list[str] | None:
    """Regenerate codes after verifying the password and a fresh TOTP code."""

    from timan_intelligence.identity.service import _verify_password
    from timan_intelligence.security.totp_service import verify_totp_for_user

    user_id = _validate_user_id(user_id)

    if (
        not isinstance(current_password, str)
        or not current_password
        or not isinstance(authenticator_code, str)
        or not authenticator_code.strip()
    ):
        return None

    p = _placeholder()
    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT password_hash
            FROM users
            WHERE id = {p}
              AND is_active = TRUE
              AND totp_enabled = TRUE
            """,
            (user_id,),
        ).fetchone()

    if user is None or not _verify_password(current_password, user["password_hash"]):
        return None

    compact_code = _normalise_code(authenticator_code)
    if compact_code is not None:
        verified = consume_recovery_code(user_id, authenticator_code)
    else:
        verified = verify_totp_for_user(user_id, authenticator_code.strip())

    if not verified:
        return None

    return generate_recovery_codes(user_id)
