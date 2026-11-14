"""Configuration and construction tests for Gmail API email delivery."""

import pytest

from timan_intelligence.identity.email_delivery import (
    EmailDeliverySettings,
    GmailAPIEmailSender,
    MockEmailSender,
    build_email_sender,
)


def test_gmail_api_settings_are_loaded_from_environment():
    settings = EmailDeliverySettings.from_environment({
        "TIMAN_EMAIL_PROVIDER": "gmail_api",
        "TIMAN_EMAIL_SENDER": "timananalytics@gmail.com",
        "TIMAN_GMAIL_CLIENT_ID": "client-id",
        "TIMAN_GMAIL_CLIENT_SECRET": "client-secret",
        "TIMAN_GMAIL_REFRESH_TOKEN": "refresh-token",
    })
    assert settings.provider == "gmail_api"
    assert settings.gmail_client_id == "client-id"
    assert settings.gmail_client_secret == "client-secret"
    assert settings.gmail_refresh_token == "refresh-token"


def test_mock_provider_remains_available():
    sender = build_email_sender(EmailDeliverySettings(provider="mock"))
    assert isinstance(sender, MockEmailSender)


def test_gmail_sender_requires_all_oauth_values():
    settings = EmailDeliverySettings(
        provider="gmail_api",
        sender_email="timananalytics@gmail.com",
        gmail_client_id="client-id",
        gmail_client_secret="",
        gmail_refresh_token="refresh-token",
    )
    with pytest.raises(ValueError, match="Gmail API configuration"):
        GmailAPIEmailSender(settings)


def test_gmail_provider_is_selected_by_factory():
    settings = EmailDeliverySettings(
        provider="gmail_api",
        sender_email="timananalytics@gmail.com",
        gmail_client_id="client-id",
        gmail_client_secret="client-secret",
        gmail_refresh_token="refresh-token",
    )
    assert isinstance(build_email_sender(settings), GmailAPIEmailSender)
