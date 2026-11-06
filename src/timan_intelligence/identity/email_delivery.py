
"""Provider-independent email delivery services for TimanStat.

Supports:
- Mock delivery for development and automated testing.
- SMTP delivery for Gmail and other SMTP providers.
- Environment-based configuration so credentials are never hardcoded.
"""

from __future__ import annotations

import os
import re
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage as MIMEEmailMessage
from typing import Protocol


DEFAULT_SMTP_TIMEOUT = 20
DEFAULT_SMTP_PORT = 587


class EmailDeliveryError(Exception):
    """Raised when an email cannot be delivered."""


@dataclass(frozen=True)
class OutboundEmail:
    """An email message prepared for delivery."""

    recipient: str
    subject: str
    body: str


@dataclass(frozen=True)
class EmailDeliverySettings:
    """Configuration for an email delivery provider."""

    provider: str = "mock"
    sender_email: str = "no-reply@timanstat.local"
    sender_name: str = "TimanStat"
    smtp_host: str = ""
    smtp_port: int = DEFAULT_SMTP_PORT
    smtp_username: str = ""
    smtp_password: str = ""
    use_starttls: bool = True
    timeout: int = DEFAULT_SMTP_TIMEOUT

    @classmethod
    def from_environment(
        cls,
        environ: dict[str, str] | None = None,
    ) -> "EmailDeliverySettings":
        """Load email settings from environment variables."""

        env = os.environ if environ is None else environ

        provider = env.get(
            "TIMAN_EMAIL_PROVIDER",
            "mock",
        ).strip().lower()

        if provider not in {"mock", "smtp"}:
            raise ValueError(
                "TIMAN_EMAIL_PROVIDER must be 'mock' or 'smtp'."
            )

        try:
            smtp_port = int(
                env.get(
                    "TIMAN_EMAIL_SMTP_PORT",
                    str(DEFAULT_SMTP_PORT),
                )
            )
            timeout = int(
                env.get(
                    "TIMAN_EMAIL_TIMEOUT",
                    str(DEFAULT_SMTP_TIMEOUT),
                )
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "SMTP port and timeout must be valid integers."
            ) from exc

        if not 1 <= smtp_port <= 65535:
            raise ValueError("SMTP port must be between 1 and 65535.")

        if not 1 <= timeout <= 120:
            raise ValueError("Email timeout must be between 1 and 120 seconds.")

        use_starttls_value = env.get(
            "TIMAN_EMAIL_USE_STARTTLS",
            "true",
        ).strip().lower()

        if use_starttls_value not in {"true", "false"}:
            raise ValueError(
                "TIMAN_EMAIL_USE_STARTTLS must be true or false."
            )

        return cls(
            provider=provider,
            sender_email=env.get(
                "TIMAN_EMAIL_SENDER",
                "no-reply@timanstat.local",
            ).strip(),
            sender_name=env.get(
                "TIMAN_EMAIL_SENDER_NAME",
                "TimanStat",
            ).strip(),
            smtp_host=env.get(
                "TIMAN_EMAIL_SMTP_HOST",
                "",
            ).strip(),
            smtp_port=smtp_port,
            smtp_username=env.get(
                "TIMAN_EMAIL_SMTP_USERNAME",
                "",
            ).strip(),
            smtp_password=env.get(
                "TIMAN_EMAIL_SMTP_PASSWORD",
                "",
            ),
            use_starttls=use_starttls_value == "true",
            timeout=timeout,
        )


class EmailSender(Protocol):
    """Interface implemented by all email delivery providers."""

    def send(self, message: OutboundEmail) -> None:
        """Deliver an email message."""


def _validate_message(message: OutboundEmail) -> None:
    """Validate an outbound email before delivery."""

    if not isinstance(message, OutboundEmail):
        raise ValueError("A valid outbound email message is required.")

    if not isinstance(message.recipient, str):
        raise ValueError("Recipient must be an email address.")

    recipient = message.recipient.strip()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient):
        raise ValueError("Recipient must be a valid email address.")

    if not isinstance(message.subject, str) or not message.subject.strip():
        raise ValueError("Email subject is required.")

    if not isinstance(message.body, str) or not message.body.strip():
        raise ValueError("Email body is required.")


class MockEmailSender:
    """In-memory email sender for development and automated tests.

    Messages are retained only in memory and are not actually delivered.
    """

    def __init__(self) -> None:
        self.sent_messages: list[OutboundEmail] = []

    def send(self, message: OutboundEmail) -> None:
        """Validate and retain a message without sending it."""

        _validate_message(message)
        self.sent_messages.append(message)


class SMTPEmailSender:
    """SMTP email sender compatible with Gmail and other SMTP providers."""

    def __init__(self, settings: EmailDeliverySettings) -> None:
        self.settings = settings

        if not settings.smtp_host:
            raise ValueError("SMTP host is required.")

        if not settings.smtp_username:
            raise ValueError("SMTP username is required.")

        if not settings.smtp_password:
            raise ValueError("SMTP password is required.")

        if not settings.sender_email:
            raise ValueError("Sender email address is required.")

        if not re.fullmatch(
            r"[^@\s]+@[^@\s]+\.[^@\s]+",
            settings.sender_email,
        ):
            raise ValueError("Sender email address is invalid.")

    def send(self, message: OutboundEmail) -> None:
        """Send a plain-text email using authenticated SMTP."""

        _validate_message(message)

        email_message = MIMEEmailMessage()
        email_message["Subject"] = message.subject
        email_message["From"] = (
            f"{self.settings.sender_name} "
            f"<{self.settings.sender_email}>"
        )
        email_message["To"] = message.recipient.strip()
        email_message.set_content(message.body)

        try:
            with smtplib.SMTP(
                self.settings.smtp_host,
                self.settings.smtp_port,
                timeout=self.settings.timeout,
            ) as server:

                server.ehlo()

                if self.settings.use_starttls:
                    server.starttls()
                    server.ehlo()

                server.login(
                    self.settings.smtp_username,
                    self.settings.smtp_password,
                )

                refused = server.send_message(email_message)

                if refused:
                    raise EmailDeliveryError(
                        "The email provider refused delivery to the "
                        "recipient."
                    )

        except EmailDeliveryError:
            raise
        except (
            smtplib.SMTPException,
            OSError,
            TimeoutError,
            ValueError,
        ) as exc:
            raise EmailDeliveryError(
                "Email delivery failed. Check the provider configuration "
                "and connection."
            ) from exc


def build_email_sender(
    settings: EmailDeliverySettings | None = None,
) -> EmailSender:
    """Construct the configured email sender.

    Mock delivery is the safe default until real SMTP credentials
    have been configured.
    """

    if settings is None:
        settings = EmailDeliverySettings.from_environment()

    if settings.provider == "mock":
        return MockEmailSender()

    if settings.provider == "smtp":
        return SMTPEmailSender(settings)

    raise ValueError("Unsupported email delivery provider.")
