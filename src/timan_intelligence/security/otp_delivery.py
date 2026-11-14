"""Provider-neutral delivery for TimanStat one-time passwords.

Email reuses the existing configured TimanStat email transport. SMS is
represented by a provider contract; no SMS provider is assumed or silently
simulated in production.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from timanstat.identity.email_delivery import (
    EmailDeliveryError,
    EmailDeliverySettings,
    EmailSender,
    OutboundEmail,
    build_email_sender,
)


class OTPDeliveryError(RuntimeError):
    """Raised when a one-time-password message cannot be delivered."""


@dataclass(frozen=True)
class OutboundSMS:
    """An SMS message prepared for delivery."""

    recipient: str
    body: str


class SMSSender(Protocol):
    """Contract implemented by an SMS gateway adapter."""

    def send(self, message: OutboundSMS) -> None:
        """Submit an SMS message to the configured provider."""


_EMAIL_SUBJECTS = {
    "verify_recovery_email": "Verify your TimanStat recovery email",
    "login_mfa": "Your TimanStat sign-in code",
    "password_recovery": "Your TimanStat password recovery code",
}


def _purpose_label(purpose: str) -> str:
    labels = {
        "verify_recovery_email": "verify your recovery email address",
        "login_mfa": "complete your sign-in",
        "password_recovery": "continue password recovery",
    }
    return labels.get(purpose, "complete your requested security action")


def send_email_otp(
    recipient: str,
    code: str,
    purpose: str,
    *,
    sender: EmailSender | None = None,
) -> None:
    """Deliver an OTP by email using TimanStat's configured email provider."""
    if not isinstance(recipient, str) or not recipient.strip():
        raise OTPDeliveryError("A valid email destination is required.")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise OTPDeliveryError("A valid one-time password is required.")
    if not isinstance(purpose, str) or not purpose.strip():
        raise OTPDeliveryError("An OTP purpose is required.")

    if sender is None:
        try:
            settings = EmailDeliverySettings.from_environment()
            sender = build_email_sender(settings)
        except Exception as exc:
            raise OTPDeliveryError(
                "The email delivery service is not configured."
            ) from exc

    subject = _EMAIL_SUBJECTS.get(
        purpose,
        "Your TimanStat security code",
    )
    body = (
        f"Your TimanStat code to {_purpose_label(purpose)} is: {code}\n\n"
        "This code expires in 5 minutes and can be used only once. "
        "If you did not request it, you can ignore this message. "
        "Never share this code with anyone."
    )

    try:
        sender.send(
            OutboundEmail(
                recipient=recipient.strip(),
                subject=subject,
                body=body,
            )
        )
    except (EmailDeliveryError, ValueError) as exc:
        raise OTPDeliveryError(
            "The one-time password could not be delivered by email."
        ) from exc
    except Exception as exc:
        raise OTPDeliveryError(
            "The one-time password could not be delivered by email."
        ) from exc


def send_sms_otp(
    recipient: str,
    code: str,
    purpose: str,
    *,
    sender: SMSSender | None = None,
) -> None:
    """Deliver an OTP by SMS through an explicitly supplied gateway adapter."""
    if not isinstance(recipient, str) or not recipient.startswith("+"):
        raise OTPDeliveryError(
            "The SMS destination must be an international E.164 number."
        )
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        raise OTPDeliveryError("A valid one-time password is required.")
    if not isinstance(purpose, str) or not purpose.strip():
        raise OTPDeliveryError("An OTP purpose is required.")
    if sender is None:
        raise OTPDeliveryError(
            "SMS delivery is not configured. Connect an SMS gateway before "
            "enabling phone verification or SMS-based sign-in."
        )

    body = (
        f"Your TimanStat code to {_purpose_label(purpose)} is {code}. "
        "It expires in 5 minutes. Do not share it."
    )
    try:
        sender.send(OutboundSMS(recipient=recipient, body=body))
    except Exception as exc:
        raise OTPDeliveryError(
            "The one-time password could not be delivered by SMS."
        ) from exc
