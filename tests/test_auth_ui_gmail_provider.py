"""Tests for selecting real email providers in authentication workflows."""

from unittest.mock import Mock

import pytest

from timan_intelligence.identity.email_delivery import (
    EmailDeliveryError,
    EmailDeliverySettings,
)
from timan_intelligence.security import auth_ui


@pytest.mark.parametrize("provider", ["smtp", "gmail_api"])
def test_configured_email_sender_accepts_real_delivery_providers(
    monkeypatch,
    provider,
):
    """Public authentication flows accept SMTP and Gmail API senders."""

    settings = EmailDeliverySettings(provider=provider)
    expected_sender = object()
    build_sender = Mock(return_value=expected_sender)

    monkeypatch.setattr(
        auth_ui,
        "_development_email_sender",
        lambda base_url: None,
    )
    monkeypatch.setattr(
        auth_ui.EmailDeliverySettings,
        "from_environment",
        Mock(return_value=settings),
    )
    monkeypatch.setattr(auth_ui, "build_email_sender", build_sender)

    sender = auth_ui._configured_email_sender(
        "https://timanstat-dev.streamlit.app"
    )

    assert sender is expected_sender
    build_sender.assert_called_once_with(settings)


def test_configured_email_sender_rejects_mock_provider(
    monkeypatch,
):
    """Public registration must not silently accept undelivered mock mail."""

    monkeypatch.setattr(
        auth_ui,
        "_development_email_sender",
        lambda base_url: None,
    )
    monkeypatch.setattr(
        auth_ui.EmailDeliverySettings,
        "from_environment",
        Mock(return_value=EmailDeliverySettings(provider="mock")),
    )
    build_sender = Mock()
    monkeypatch.setattr(auth_ui, "build_email_sender", build_sender)

    with pytest.raises(EmailDeliveryError) as error:
        auth_ui._configured_email_sender(
            "https://timanstat-dev.streamlit.app"
        )

    assert error.value.stage == "configuration"
    build_sender.assert_not_called()
