
"""TOTP enrolment and verification services for TimanStat."""

from __future__ import annotations

from typing import Any

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.security.totp import (
    DEFAULT_ISSUER,
    TOTPError,
    build_totp_provisioning_uri,
    generate_totp_secret,
    verify_totp_code,
)
from timan_intelligence.security.totp_encryption import (
    SecretEncryptionError,
    decrypt_totp_secret,
    encrypt_totp_secret,
)
from timan_intelligence.security.totp_rate_limit import (
    totp_attempt_limiter,
)
from timan_intelligence.security.distributed_rate_limit import DatabaseRateLimiter


# An unconfirmed authenticator enrolment remains valid for 15 minutes.
PENDING_ENROLMENT_TTL_MINUTES = 15

# Password re-authentication for sensitive security changes is shared by
# authenticator disablement and recovery-code regeneration.
SECURITY_REAUTHENTICATION_LIMITER = DatabaseRateLimiter(
    scope="security-reauthentication",
    max_failed_attempts=5,
    window_seconds=900,
    lockout_seconds=900,
)


class TOTPServiceError(Exception):
    """Raised when a TOTP enrolment or service operation fails."""


def _rate_limit_is_locked(user_id: str, operation: str) -> bool:
    """Check the TOTP limiter and fail closed with a controlled service error."""
    try:
        return totp_attempt_limiter.is_locked(user_id, operation)
    except Exception as exc:
        raise TOTPServiceError(
            "The TOTP rate-limit service is unavailable."
        ) from exc


def _rate_limit_record_failure(user_id: str, operation: str) -> None:
    """Record a failed TOTP attempt or fail closed."""
    try:
        totp_attempt_limiter.record_failure(user_id, operation)
    except Exception as exc:
        raise TOTPServiceError(
            "The TOTP rate-limit service is unavailable."
        ) from exc


def _rate_limit_record_success(user_id: str, operation: str) -> None:
    """Clear successful TOTP attempt history or fail closed."""
    try:
        totp_attempt_limiter.record_success(user_id, operation)
    except Exception as exc:
        raise TOTPServiceError(
            "The TOTP rate-limit service is unavailable."
        ) from exc


def is_security_reauthentication_locked(user_id: str) -> bool:
    """Return whether sensitive account-security re-authentication is locked."""
    try:
        return SECURITY_REAUTHENTICATION_LIMITER.is_locked(user_id)
    except Exception as exc:
        raise TOTPServiceError(
            "The account security rate-limit service is unavailable."
        ) from exc


def _record_security_reauthentication_failure(user_id: str) -> None:
    """Record an incorrect password used for a sensitive security change."""
    try:
        SECURITY_REAUTHENTICATION_LIMITER.record_failure(user_id)
    except Exception as exc:
        raise TOTPServiceError(
            "The account security rate-limit service is unavailable."
        ) from exc


def _clear_security_reauthentication_failures(user_id: str) -> None:
    """Clear password re-authentication failures after a successful change."""
    try:
        SECURITY_REAUTHENTICATION_LIMITER.record_success(user_id)
    except Exception as exc:
        # A committed security change must not be reported as failed solely
        # because stale rate-limit history could not be cleared.
        pass


def _placeholder() -> str:
    """Return the correct database parameter placeholder."""

    return "%s" if get_database_type() == "postgresql" else "?"


def _validate_user_id(user_id: str) -> str:
    """Validate and normalise a user identifier."""

    if not isinstance(user_id, str) or not user_id.strip():
        raise TOTPServiceError("A valid user ID is required.")

    return user_id.strip()


def _get_active_user(connection, user_id: str) -> Any:
    """Retrieve an active user and their TOTP enrolment state."""

    p = _placeholder()

    return connection.execute(
        f"""
        SELECT
            id,
            username,
            email,
            is_active,
            totp_enabled,
            totp_secret_encrypted,
            totp_pending_secret_encrypted,
            totp_last_accepted_counter,
            totp_pending_created_at
        FROM users
        WHERE id = {p}
          AND is_active = TRUE
        """,
        (user_id,),
    ).fetchone()


def _clear_expired_pending_enrolment(
    connection,
    user_id: str,
) -> bool:
    """
    Clear a pending enrolment that has expired or has no timestamp.

    The expiry comparison uses database time to avoid differences
    between application-server clocks and database-server clocks.

    Returns:
        True if an expired or invalid pending enrolment was cleared.
        False if no expired pending enrolment was found.
    """

    p = _placeholder()

    if get_database_type() == "postgresql":
        expiry_condition = f"""
            totp_pending_created_at <
            CURRENT_TIMESTAMP - INTERVAL '{PENDING_ENROLMENT_TTL_MINUTES} minutes'
        """
    else:
        expiry_condition = f"""
            totp_pending_created_at <
            datetime('now', '-{PENDING_ENROLMENT_TTL_MINUTES} minutes')
        """

    result = connection.execute(
        f"""
        UPDATE users
        SET
            totp_pending_secret_encrypted = NULL,
            totp_pending_created_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = {p}
          AND is_active = TRUE
          AND totp_enabled = FALSE
          AND totp_pending_secret_encrypted IS NOT NULL
          AND (
              totp_pending_created_at IS NULL
              OR {expiry_condition}
          )
        """,
        (user_id,),
    )

    return result.rowcount == 1


def begin_totp_enrolment(
    user_id: str,
    issuer: str = DEFAULT_ISSUER,
) -> dict[str, str]:
    """
    Begin TOTP enrolment for an active user.

    Generates a new secret, creates its provisioning URI, encrypts
    the secret, and stores it as a pending enrolment secret.

    The provisioning URI is validated before any database write.
    This prevents invalid issuer or account configuration from
    leaving an unusable pending enrolment in the database.

    The plaintext secret and provisioning URI are returned to the
    caller for display to the user. They must not be stored in logs.

    Returns:
        A dictionary containing:
        - secret: Base32 secret for authenticator enrolment.
        - provisioning_uri: Standard otpauth URI.

    Raises:
        TOTPServiceError: If the user cannot begin enrolment.
    """

    user_id = _validate_user_id(user_id)

    try:
        secret = generate_totp_secret()

    except TOTPError as exc:
        raise TOTPServiceError(
            "Unable to generate the TOTP enrolment secret."
        ) from exc

    p = _placeholder()

    with database_connection() as connection:
        user = _get_active_user(connection, user_id)

        if user is None:
            raise TOTPServiceError(
                "The requested active user account was not found."
            )

        if bool(user["totp_enabled"]):
            raise TOTPServiceError(
                "Two-factor authentication is already enabled."
            )

        try:
            provisioning_uri = build_totp_provisioning_uri(
                secret=secret,
                account_name=user["email"],
                issuer=issuer,
            )

        except TOTPError as exc:
            raise TOTPServiceError(
                "Unable to create the authenticator provisioning URI."
            ) from exc

        try:
            encrypted_secret = encrypt_totp_secret(secret)

        except SecretEncryptionError as exc:
            raise TOTPServiceError(
                "Unable to protect the TOTP enrolment secret."
            ) from exc

        result = connection.execute(
            f"""
            UPDATE users
            SET
                totp_pending_secret_encrypted = {p},
                totp_pending_created_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND is_active = TRUE
              AND totp_enabled = FALSE
            """,
            (
                encrypted_secret,
                user_id,
            ),
        )

        if result.rowcount != 1:
            raise TOTPServiceError(
                "Unable to establish the pending TOTP enrolment."
            )

        stored = connection.execute(
            f"""
            SELECT totp_pending_secret_encrypted
            FROM users
            WHERE id = {p}
            """,
            (user_id,),
        ).fetchone()

        if (
            stored is None
            or stored["totp_pending_secret_encrypted"] != encrypted_secret
        ):
            raise TOTPServiceError(
                "Unable to verify the pending TOTP enrolment."
            )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
    }


def confirm_totp_enrolment(
    user_id: str,
    code: str,
    at_time: float | None = None,
) -> bool:
    """
    Confirm TOTP enrolment using a valid authenticator code.

    Pending enrolments older than the configured TTL are rejected
    and their pending secrets are cleared.

    Failed authenticator codes are rate-limited independently from
    normal TOTP verification attempts.

    Returns:
        True if enrolment succeeds; otherwise False.
    """

    user_id = _validate_user_id(user_id)

    if _rate_limit_is_locked(user_id, "enrolment"):
        return False

    p = _placeholder()

    with database_connection() as connection:
        user = _get_active_user(connection, user_id)

        if user is None:
            return False

        if bool(user["totp_enabled"]):
            return False

        encrypted_secret = user["totp_pending_secret_encrypted"]

        if not encrypted_secret:
            return False

        # Expired enrolments and pending secrets without a creation
        # timestamp must never be accepted.
        if _clear_expired_pending_enrolment(connection, user_id):
            return False

        # Reload the record after the expiry check so confirmation
        # uses the current pending secret and not a stale snapshot.
        user = _get_active_user(connection, user_id)

        if user is None or bool(user["totp_enabled"]):
            return False

        encrypted_secret = user["totp_pending_secret_encrypted"]

        if not encrypted_secret or user["totp_pending_created_at"] is None:
            return False

        try:
            secret = decrypt_totp_secret(encrypted_secret)

            accepted_counter = verify_totp_code(
                secret=secret,
                code=code,
                at_time=at_time,
            )

        except (TOTPError, SecretEncryptionError) as exc:
            raise TOTPServiceError(
                "Unable to verify the pending TOTP enrolment secret."
            ) from exc

        if accepted_counter is None:
            _rate_limit_record_failure(user_id, "enrolment")
            return False

        result = connection.execute(
            f"""
            UPDATE users
            SET
                totp_enabled = TRUE,
                session_version = session_version + 1,
                totp_secret_encrypted = {p},
                totp_pending_secret_encrypted = NULL,
                totp_last_accepted_counter = {p},
                totp_enrolled_at = CURRENT_TIMESTAMP,
                totp_pending_created_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND is_active = TRUE
              AND totp_enabled = FALSE
              AND totp_pending_secret_encrypted = {p}
              AND totp_pending_created_at IS NOT NULL
            """,
            (
                encrypted_secret,
                accepted_counter,
                user_id,
                encrypted_secret,
            ),
        )

        if result.rowcount != 1:
            return False

        _rate_limit_record_success(user_id, "enrolment")

        return True


def verify_totp_for_user(
    user_id: str,
    code: str,
    at_time: float | None = None,
) -> bool:
    """
    Verify an authenticator code for an enrolled active user.

    The accepted counter is updated atomically. This prevents the
    same authenticator code from succeeding in concurrent requests.

    Failed authenticator codes are rate-limited independently from
    enrolment confirmation attempts.

    Returns:
        True if the code is valid and its counter is successfully
        recorded; otherwise False.
    """

    user_id = _validate_user_id(user_id)

    if _rate_limit_is_locked(user_id, "verification"):
        return False

    p = _placeholder()

    with database_connection() as connection:
        user = _get_active_user(connection, user_id)

        if user is None:
            return False

        if not bool(user["totp_enabled"]):
            return False

        encrypted_secret = user["totp_secret_encrypted"]

        if not encrypted_secret:
            raise TOTPServiceError(
                "The enrolled account has no protected TOTP secret."
            )

        try:
            secret = decrypt_totp_secret(encrypted_secret)

            accepted_counter = verify_totp_code(
                secret=secret,
                code=code,
                at_time=at_time,
                last_accepted_counter=user["totp_last_accepted_counter"],
            )

        except (TOTPError, SecretEncryptionError) as exc:
            raise TOTPServiceError(
                "Unable to verify the account's TOTP secret."
            ) from exc

        if accepted_counter is None:
            _rate_limit_record_failure(user_id, "verification")
            return False

        result = connection.execute(
            f"""
            UPDATE users
            SET
                totp_last_accepted_counter = {p},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND is_active = TRUE
              AND totp_enabled = TRUE
              AND totp_secret_encrypted = {p}
              AND (
                  totp_last_accepted_counter IS NULL
                  OR totp_last_accepted_counter < {p}
              )
            """,
            (
                accepted_counter,
                user_id,
                encrypted_secret,
                accepted_counter,
            ),
        )

        if result.rowcount != 1:
            # This also covers a concurrent request that has already
            # accepted the same counter.
            totp_attempt_limiter.record_failure(
                user_id,
                "verification",
            )
            return False

        _rate_limit_record_success(user_id, "verification")

        return True



def get_totp_status(user_id: str) -> bool:
    """Return whether an active account has TOTP enabled."""

    user_id = _validate_user_id(user_id)

    with database_connection() as connection:
        user = _get_active_user(connection, user_id)

        if user is None:
            raise TOTPServiceError(
                "The requested active user account was not found."
            )

        return bool(user["totp_enabled"])


def disable_totp_for_user(
    user_id: str,
    current_password: str,
    code: str,
    at_time: float | None = None,
) -> bool:
    """
    Disable TOTP after re-authenticating with the account password
    and a fresh authenticator code.

    Successful removal clears all enrolled and pending TOTP material
    and increments session_version so every active session is revoked.

    Returns False when credentials are incorrect or the account cannot
    be updated. Invalid user IDs raise TOTPServiceError.
    """

    # Import locally to avoid an identity/security module import cycle.
    from timan_intelligence.identity.service import _verify_password

    user_id = _validate_user_id(user_id)

    if not isinstance(current_password, str) or not current_password:
        return False

    if not isinstance(code, str) or not code.strip():
        return False

    if is_security_reauthentication_locked(user_id):
        return False

    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT password_hash, totp_enabled
            FROM users
            WHERE id = {p}
              AND is_active = TRUE
            """,
            (user_id,),
        ).fetchone()

        if user is None or not bool(user["totp_enabled"]):
            return False

        if not _verify_password(current_password, user["password_hash"]):
            _record_security_reauthentication_failure(user_id)
            return False

    # This validates and consumes a fresh, non-replayed authenticator
    # code before the destructive operation is attempted.
    if not verify_totp_for_user(user_id, code.strip(), at_time=at_time):
        return False

    with database_connection() as connection:
        updated = connection.execute(
            f"""
            UPDATE users
            SET
                totp_enabled = FALSE,
                totp_secret_encrypted = NULL,
                totp_pending_secret_encrypted = NULL,
                totp_last_accepted_counter = NULL,
                totp_enrolled_at = NULL,
                totp_pending_created_at = NULL,
                session_version = session_version + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
              AND is_active = TRUE
              AND totp_enabled = TRUE
            """,
            (user_id,),
        )

        changed = updated.rowcount == 1

    if changed:
        _clear_security_reauthentication_failures(user_id)

    return changed
