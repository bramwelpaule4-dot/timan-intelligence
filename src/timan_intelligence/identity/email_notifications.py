
"""Email notification services for TimanStat identity workflows."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.identity.email_delivery import (
    EmailSender,
    OutboundEmail,
    build_email_sender,
)
from timan_intelligence.identity.email_verification import (
    DEFAULT_TOKEN_EXPIRY_MINUTES,
    create_email_verification_token,
)
from timan_intelligence.identity.password_reset import (
    DEFAULT_PASSWORD_RESET_EXPIRY_MINUTES,
    create_password_reset_token,
)
from timan_intelligence.security.distributed_rate_limit import DatabaseRateLimiter


EMAIL_VERIFICATION_REQUEST_LIMITER = DatabaseRateLimiter(
    scope="email-verification-request",
    max_failed_attempts=1,
    window_seconds=DEFAULT_RESEND_COOLDOWN_SECONDS,
    lockout_seconds=DEFAULT_RESEND_COOLDOWN_SECONDS,
)
PASSWORD_RESET_REQUEST_LIMITER = DatabaseRateLimiter(
    scope="password-reset-request",
    max_failed_attempts=1,
    window_seconds=DEFAULT_PASSWORD_RESET_COOLDOWN_SECONDS,
    lockout_seconds=DEFAULT_PASSWORD_RESET_COOLDOWN_SECONDS,
)


EMAIL_VERIFICATION_SUBJECT = "Verify your TimanStat account"
PASSWORD_RESET_SUBJECT = "Reset your TimanStat password"

DEFAULT_RESEND_COOLDOWN_SECONDS = 60
MAX_RESEND_COOLDOWN_SECONDS = 3600

DEFAULT_PASSWORD_RESET_COOLDOWN_SECONDS = 60
MAX_PASSWORD_RESET_COOLDOWN_SECONDS = 3600


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""

    return "%s" if get_database_type() == "postgresql" else "?"


def _validate_base_url(base_url: str) -> str:
    """Validate and normalise the application base URL."""

    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("A valid application base URL is required.")

    base_url = base_url.strip()
    parsed = urlsplit(base_url)

    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError(
            "Application base URL must be a valid HTTP or HTTPS URL."
        )

    if parsed.username or parsed.password:
        raise ValueError(
            "Application base URL must not contain credentials."
        )

    if parsed.query or parsed.fragment:
        raise ValueError(
            "Application base URL must not contain a query or fragment."
        )

    if parsed.scheme == "http" and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError(
            "HTTPS is required for non-local application URLs."
        )

    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip("/"),
            "",
            "",
        )
    )


def _build_verification_url(base_url: str, token: str) -> str:
    """Build the application email-verification URL."""

    query = urlencode({"verify_email": token})

    return f"{base_url}/?{query}"


def _build_password_reset_url(base_url: str, token: str) -> str:
    """Build the application password-reset URL."""

    query = urlencode({"reset_password": token})

    return f"{base_url}/?{query}"


def _validate_email(email: str) -> str | None:
    """Return a normalised email address or None when invalid."""

    if not isinstance(email, str):
        return None

    normalised = email.strip().lower()

    if (
        len(normalised) > 254
        or not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            normalised,
        )
    ):
        return None

    return normalised


def _validate_cooldown(
    cooldown_seconds: int,
    maximum_seconds: int,
    workflow_name: str,
) -> None:
    """Validate a notification cooldown setting."""

    if (
        isinstance(cooldown_seconds, bool)
        or not isinstance(cooldown_seconds, int)
        or not 1 <= cooldown_seconds <= maximum_seconds
    ):
        raise ValueError(
            f"{workflow_name} cooldown must be between "
            f"1 and {maximum_seconds} seconds."
        )


def send_email_verification(
    user_id: str,
    base_url: str,
    sender: EmailSender | None = None,
    expiry_minutes: int = DEFAULT_TOKEN_EXPIRY_MINUTES,
) -> None:
    """
    Generate and send an email-verification message.

    Only the token hash is stored in the database. The plaintext
    token is included only in the outgoing verification link.
    """

    application_url = _validate_base_url(base_url)

    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT id, email, full_name, email_verified
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

    if user["email_verified"]:
        raise ValueError(
            "This user's email address is already verified."
        )

    token = create_email_verification_token(
        user_id,
        expiry_minutes=expiry_minutes,
    )

    verification_url = _build_verification_url(
        application_url,
        token,
    )

    message = OutboundEmail(
        recipient=user["email"],
        subject=EMAIL_VERIFICATION_SUBJECT,
        body=(
            f"Hello {user['full_name']},\n\n"
            "Thank you for registering with TimanStat.\n\n"
            "Please verify your email address by opening the link below:\n\n"
            f"{verification_url}\n\n"
            f"This link expires in {expiry_minutes} minutes. "
            "If you did not create a TimanStat account, "
            "you can ignore this message.\n\n"
            "Regards,\n"
            "TimanStat\n"
            "Timan Analytics"
        ),
    )

    email_sender = sender or build_email_sender()
    email_sender.send(message)


def resend_email_verification(
    email: str,
    base_url: str,
    sender: EmailSender | None = None,
    cooldown_seconds: int = DEFAULT_RESEND_COOLDOWN_SECONDS,
) -> bool:
    """
    Request another email-verification message.

    Returns True when a verification message is successfully sent.

    Returns False for unknown, inactive, already verified, or
    recently contacted accounts. This avoids exposing account
    existence through the public resend workflow.
    """

    normalised_email = _validate_email(email)

    if normalised_email is None:
        return False

    _validate_cooldown(
        cooldown_seconds,
        MAX_RESEND_COOLDOWN_SECONDS,
        "Resend",
    )

    application_url = _validate_base_url(base_url)

    # Consume a shared request slot before account lookup. This both
    # closes the multi-worker cooldown race and avoids account enumeration.
    if not EMAIL_VERIFICATION_REQUEST_LIMITER.consume_attempt(normalised_email):
        return False

    p = _placeholder()
    cutoff = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(seconds=cooldown_seconds)
    )

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT id
            FROM users
            WHERE email = {p}
              AND is_active = TRUE
              AND email_verified = FALSE
            """,
            (normalised_email,),
        ).fetchone()

        if user is None:
            return False

        recent_token = connection.execute(
            f"""
            SELECT id
            FROM email_verification_tokens
            WHERE user_id = {p}
              AND created_at >= {p}
            LIMIT 1
            """,
            (user["id"], cutoff),
        ).fetchone()

        if recent_token is not None:
            return False

        user_id = user["id"]

    send_email_verification(
        user_id=user_id,
        base_url=application_url,
        sender=sender,
    )

    return True


def send_password_reset_email(
    user_id: str,
    base_url: str,
    sender: EmailSender | None = None,
    expiry_minutes: int = DEFAULT_PASSWORD_RESET_EXPIRY_MINUTES,
) -> None:
    """
    Generate and send a password-reset email.

    Only the token hash is stored in the database. The plaintext
    token is included only in the outgoing reset link.

    Password recovery does not automatically verify an email address.
    """

    application_url = _validate_base_url(base_url)
    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT id, email, full_name
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

    token = create_password_reset_token(
        user_id,
        expiry_minutes=expiry_minutes,
    )

    reset_url = _build_password_reset_url(
        application_url,
        token,
    )

    message = OutboundEmail(
        recipient=user["email"],
        subject=PASSWORD_RESET_SUBJECT,
        body=(
            f"Hello {user['full_name']},\n\n"
            "We received a request to reset your TimanStat password.\n\n"
            "To choose a new password, open the link below:\n\n"
            f"{reset_url}\n\n"
            f"This link expires in {expiry_minutes} minutes and "
            "can only be used once.\n\n"
            "If you did not request a password reset, ignore this "
            "message. Your existing password will remain unchanged.\n\n"
            "For your security, do not share this link with anyone.\n\n"
            "Regards,\n"
            "TimanStat\n"
            "Timan Analytics"
        ),
    )

    email_sender = sender or build_email_sender()
    email_sender.send(message)


def request_password_reset(
    email: str,
    base_url: str,
    sender: EmailSender | None = None,
    cooldown_seconds: int = DEFAULT_PASSWORD_RESET_COOLDOWN_SECONDS,
) -> bool:
    """
    Request a password-reset email without disclosing account existence.

    Returns True when a reset email is successfully sent.

    Returns False for invalid, unknown, inactive, or recently
    contacted email addresses.

    Active accounts can request password recovery whether or not
    their email address has been verified. Completing a password
    reset does not change the email-verification status.

    A separate cooldown is applied to password-reset requests.
    """

    normalised_email = _validate_email(email)

    if normalised_email is None:
        return False

    _validate_cooldown(
        cooldown_seconds,
        MAX_PASSWORD_RESET_COOLDOWN_SECONDS,
        "Password-reset",
    )

    application_url = _validate_base_url(base_url)

    # The request throttle is shared by every worker using this database.
    # It is checked before account lookup to preserve generic responses.
    if not PASSWORD_RESET_REQUEST_LIMITER.consume_attempt(normalised_email):
        return False

    p = _placeholder()
    cutoff = (
        datetime.now(timezone.utc).replace(tzinfo=None)
        - timedelta(seconds=cooldown_seconds)
    )

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT id
            FROM users
            WHERE email = {p}
              AND is_active = TRUE
            """,
            (normalised_email,),
        ).fetchone()

        if user is None:
            return False

        recent_token = connection.execute(
            f"""
            SELECT id
            FROM password_reset_tokens
            WHERE user_id = {p}
              AND created_at >= {p}
            LIMIT 1
            """,
            (user["id"], cutoff),
        ).fetchone()

        if recent_token is not None:
            return False

        user_id = user["id"]

    send_password_reset_email(
        user_id=user_id,
        base_url=application_url,
        sender=sender,
    )

    return True
