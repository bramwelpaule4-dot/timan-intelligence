
"""Email notification services for TimanStat identity workflows."""

from __future__ import annotations

from urllib.parse import urlencode, urlsplit, urlunsplit

from timan_intelligence.identity.email_delivery import (
    EmailSender,
    OutboundEmail,
    build_email_sender,
)
from timan_intelligence.identity.email_verification import (
    DEFAULT_TOKEN_EXPIRY_MINUTES,
    create_email_verification_token,
)
from timan_intelligence.identity.service import get_user_by_id


EMAIL_VERIFICATION_SUBJECT = "Verify your TimanStat account"


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


def send_email_verification(
    user_id: str,
    base_url: str,
    sender: EmailSender | None = None,
    expiry_minutes: int = DEFAULT_TOKEN_EXPIRY_MINUTES,
) -> None:
    """
    Generate and send an email-verification message.

    The verification token is stored as a hash by the token service.
    Its plaintext value is included only in the outgoing verification
    link.

    Args:
        user_id: ID of the registered user.
        base_url: Public application URL, or a localhost URL for
            development.
        sender: Optional email sender. When omitted, the configured
            provider is constructed automatically.
        expiry_minutes: Token validity period.

    Raises:
        ValueError: If the user or application URL is invalid.
        EmailDeliveryError: If email delivery fails.
    """

    application_url = _validate_base_url(base_url)

    user = get_user_by_id(user_id)

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
