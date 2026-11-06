
"""Tests for TimanStat provider-independent email delivery."""

from email.message import EmailMessage
from unittest.mock import MagicMock

import pytest

from timan_intelligence.identity import email_delivery
from timan_intelligence.identity.email_delivery import (
    EmailDeliveryError,
    EmailDeliverySettings,
    MockEmailSender,
    OutboundEmail,
    SMTPEmailSender,
    build_email_sender,
)


@pytest.fixture
def valid_message():
    """Provide a valid outbound email."""

    return OutboundEmail(
        recipient="recipient@example.com",
        subject="Verify your TimanStat account",
        body="Please verify your email address.",
    )


@pytest.fixture
def smtp_settings():
    """Provide SMTP configuration for isolated tests."""

    return EmailDeliverySettings(
        provider="smtp",
        sender_email="timananalytics@gmail.com",
        sender_name="Timan Analytics",
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_username="timananalytics@gmail.com",
        smtp_password="test-app-password",
        use_starttls=True,
        timeout=20,
    )


def test_default_settings_use_mock_provider():
    settings = EmailDeliverySettings()

    assert settings.provider == "mock"
    assert settings.smtp_host == ""
    assert settings.smtp_password == ""


def test_environment_configuration_loads_mock_provider():
    settings = EmailDeliverySettings.from_environment(
        {
            "TIMAN_EMAIL_PROVIDER": "mock",
            "TIMAN_EMAIL_SENDER": "test@example.com",
            "TIMAN_EMAIL_SENDER_NAME": "Test Sender",
        }
    )

    assert settings.provider == "mock"
    assert settings.sender_email == "test@example.com"
    assert settings.sender_name == "Test Sender"


def test_environment_configuration_loads_smtp_settings():
    settings = EmailDeliverySettings.from_environment(
        {
            "TIMAN_EMAIL_PROVIDER": "smtp",
            "TIMAN_EMAIL_SENDER": "timananalytics@gmail.com",
            "TIMAN_EMAIL_SENDER_NAME": "Timan Analytics",
            "TIMAN_EMAIL_SMTP_HOST": "smtp.gmail.com",
            "TIMAN_EMAIL_SMTP_PORT": "587",
            "TIMAN_EMAIL_SMTP_USERNAME": "timananalytics@gmail.com",
            "TIMAN_EMAIL_SMTP_PASSWORD": "test-app-password",
            "TIMAN_EMAIL_USE_STARTTLS": "true",
            "TIMAN_EMAIL_TIMEOUT": "30",
        }
    )

    assert settings.provider == "smtp"
    assert settings.sender_email == "timananalytics@gmail.com"
    assert settings.smtp_host == "smtp.gmail.com"
    assert settings.smtp_port == 587
    assert settings.smtp_username == "timananalytics@gmail.com"
    assert settings.smtp_password == "test-app-password"
    assert settings.use_starttls is True
    assert settings.timeout == 30


def test_environment_provider_is_case_insensitive():
    settings = EmailDeliverySettings.from_environment(
        {"TIMAN_EMAIL_PROVIDER": "SMTP"}
    )

    assert settings.provider == "smtp"


def test_environment_rejects_unsupported_provider():
    with pytest.raises(ValueError):
        EmailDeliverySettings.from_environment(
            {"TIMAN_EMAIL_PROVIDER": "sendgrid"}
        )


@pytest.mark.parametrize(
    "port",
    ["invalid", "0", "65536", "-1"],
)
def test_environment_rejects_invalid_smtp_port(port):
    with pytest.raises(ValueError):
        EmailDeliverySettings.from_environment(
            {"TIMAN_EMAIL_SMTP_PORT": port}
        )


@pytest.mark.parametrize(
    "timeout",
    ["invalid", "0", "121", "-1"],
)
def test_environment_rejects_invalid_timeout(timeout):
    with pytest.raises(ValueError):
        EmailDeliverySettings.from_environment(
            {"TIMAN_EMAIL_TIMEOUT": timeout}
        )


def test_environment_rejects_invalid_starttls_value():
    with pytest.raises(ValueError):
        EmailDeliverySettings.from_environment(
            {"TIMAN_EMAIL_USE_STARTTLS": "sometimes"}
        )


def test_build_email_sender_defaults_to_mock():
    sender = build_email_sender(
        EmailDeliverySettings()
    )

    assert isinstance(sender, MockEmailSender)


def test_build_email_sender_creates_smtp_sender(smtp_settings):
    sender = build_email_sender(smtp_settings)

    assert isinstance(sender, SMTPEmailSender)


def test_mock_sender_stores_valid_message(valid_message):
    sender = MockEmailSender()

    sender.send(valid_message)

    assert len(sender.sent_messages) == 1
    assert sender.sent_messages[0] == valid_message


def test_mock_sender_can_store_multiple_messages(valid_message):
    sender = MockEmailSender()

    sender.send(valid_message)
    sender.send(valid_message)

    assert len(sender.sent_messages) == 2


@pytest.mark.parametrize(
    "message",
    [
        None,
        "not an email object",
        OutboundEmail(
            recipient="invalid-address",
            subject="Subject",
            body="Body",
        ),
        OutboundEmail(
            recipient="recipient@example.com",
            subject="",
            body="Body",
        ),
        OutboundEmail(
            recipient="recipient@example.com",
            subject="Subject",
            body="",
        ),
        OutboundEmail(
            recipient="recipient@example.com",
            subject="   ",
            body="Body",
        ),
        OutboundEmail(
            recipient="recipient@example.com",
            subject="Subject",
            body="   ",
        ),
    ],
)
def test_mock_sender_rejects_invalid_messages(message):
    sender = MockEmailSender()

    with pytest.raises(ValueError):
        sender.send(message)

    assert sender.sent_messages == []


def test_smtp_sender_requires_host():
    settings = EmailDeliverySettings(
        provider="smtp",
        smtp_username="user@example.com",
        smtp_password="password",
    )

    with pytest.raises(ValueError, match="SMTP host"):
        SMTPEmailSender(settings)


def test_smtp_sender_requires_username():
    settings = EmailDeliverySettings(
        provider="smtp",
        smtp_host="smtp.example.com",
        smtp_password="password",
    )

    with pytest.raises(ValueError, match="SMTP username"):
        SMTPEmailSender(settings)


def test_smtp_sender_requires_password():
    settings = EmailDeliverySettings(
        provider="smtp",
        smtp_host="smtp.example.com",
        smtp_username="user@example.com",
    )

    with pytest.raises(ValueError, match="SMTP password"):
        SMTPEmailSender(settings)


def test_smtp_sender_requires_valid_sender_email():
    settings = EmailDeliverySettings(
        provider="smtp",
        sender_email="invalid-address",
        smtp_host="smtp.example.com",
        smtp_username="user@example.com",
        smtp_password="password",
    )

    with pytest.raises(ValueError, match="Sender email"):
        SMTPEmailSender(settings)


def test_smtp_sender_delivers_message_using_starttls(
    smtp_settings,
    valid_message,
    monkeypatch,
):
    smtp_server = MagicMock()
    smtp_server.__enter__.return_value = smtp_server

    monkeypatch.setattr(
        email_delivery.smtplib,
        "SMTP",
        MagicMock(return_value=smtp_server),
    )

    sender = SMTPEmailSender(smtp_settings)

    sender.send(valid_message)

    email_argument = smtp_server.send_message.call_args.args[0]

    assert isinstance(email_argument, EmailMessage)
    assert email_argument["To"] == "recipient@example.com"
    assert email_argument["Subject"] == (
        "Verify your TimanStat account"
    )
    assert "timananalytics@gmail.com" in email_argument["From"]

    smtp_server.ehlo.assert_called()
    smtp_server.starttls.assert_called_once()
    smtp_server.login.assert_called_once_with(
        "timananalytics@gmail.com",
        "test-app-password",
    )
    smtp_server.send_message.assert_called_once()


def test_smtp_sender_can_disable_starttls(
    smtp_settings,
    valid_message,
    monkeypatch,
):
    settings = EmailDeliverySettings(
        **{
            **smtp_settings.__dict__,
            "use_starttls": False,
        }
    )

    smtp_server = MagicMock()
    smtp_server.__enter__.return_value = smtp_server

    monkeypatch.setattr(
        email_delivery.smtplib,
        "SMTP",
        MagicMock(return_value=smtp_server),
    )

    sender = SMTPEmailSender(settings)

    sender.send(valid_message)

    smtp_server.starttls.assert_not_called()
    smtp_server.login.assert_called_once()
    smtp_server.send_message.assert_called_once()


def test_smtp_sender_raises_delivery_error_on_connection_failure(
    smtp_settings,
    valid_message,
    monkeypatch,
):
    def fail_connection(*args, **kwargs):
        raise OSError("Connection failed")

    monkeypatch.setattr(
        email_delivery.smtplib,
        "SMTP",
        fail_connection,
    )

    sender = SMTPEmailSender(smtp_settings)

    with pytest.raises(EmailDeliveryError):
        sender.send(valid_message)


def test_smtp_sender_raises_delivery_error_on_authentication_failure(
    smtp_settings,
    valid_message,
    monkeypatch,
):
    smtp_server = MagicMock()
    smtp_server.__enter__.return_value = smtp_server
    smtp_server.login.side_effect = (
        email_delivery.smtplib.SMTPAuthenticationError(
            535,
            b"Authentication failed",
        )
    )

    monkeypatch.setattr(
        email_delivery.smtplib,
        "SMTP",
        MagicMock(return_value=smtp_server),
    )

    sender = SMTPEmailSender(smtp_settings)

    with pytest.raises(EmailDeliveryError):
        sender.send(valid_message)


def test_smtp_sender_rejects_recipient_refusal(
    smtp_settings,
    valid_message,
    monkeypatch,
):
    smtp_server = MagicMock()
    smtp_server.__enter__.return_value = smtp_server
    smtp_server.send_message.return_value = {
        "recipient@example.com": (550, b"Mailbox unavailable")
    }

    monkeypatch.setattr(
        email_delivery.smtplib,
        "SMTP",
        MagicMock(return_value=smtp_server),
    )

    sender = SMTPEmailSender(smtp_settings)

    with pytest.raises(EmailDeliveryError):
        sender.send(valid_message)


def test_smtp_sender_rejects_invalid_message(
    smtp_settings,
):
    sender = SMTPEmailSender(smtp_settings)

    invalid_message = OutboundEmail(
        recipient="invalid",
        subject="Subject",
        body="Body",
    )

    with pytest.raises(ValueError):
        sender.send(invalid_message)
