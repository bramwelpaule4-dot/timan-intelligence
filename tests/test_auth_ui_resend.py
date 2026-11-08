
"""Tests for the TimanStat email-verification resend interface."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from timan_intelligence.security import auth_ui


class FakeStreamlit:
    """Minimal Streamlit test double for resend-interface tests."""

    def __init__(self, email="", submitted=True, secrets=None):
        self.email = email
        self.submitted = submitted
        self.secrets = secrets or {
            "TIMAN_APP_BASE_URL": (
                "https://timanstat.example.com"
            )
        }
        self.session_state = {}
        self.errors = []
        self.warnings = []
        self.successes = []
        self.writes = []
        self.markdown_messages = []
        self.captions = []

    def subheader(self, value):
        self.writes.append(value)

    def write(self, value):
        self.writes.append(value)

    def form(self, *args, **kwargs):
        return nullcontext()

    def text_input(self, *args, **kwargs):
        return self.email

    def form_submit_button(self, *args, **kwargs):
        return self.submitted

    def error(self, value):
        self.errors.append(value)

    def warning(self, value):
        self.warnings.append(value)

    def success(self, value):
        self.successes.append(value)

    def markdown(self, value):
        self.markdown_messages.append(value)

    def caption(self, value):
        self.captions.append(value)


@pytest.fixture
def fake_streamlit(monkeypatch):
    fake = FakeStreamlit(email="test@example.com")
    monkeypatch.setattr(auth_ui, "st", fake)
    return fake


def test_resend_form_does_not_submit_when_not_submitted(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.submitted = False

    resend = Mock()
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    resend.assert_not_called()
    assert fake_streamlit.successes == []
    assert fake_streamlit.errors == []


def test_resend_form_rejects_empty_email(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.email = "   "

    resend = Mock()
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    assert fake_streamlit.errors == [
        "Enter your registered email address."
    ]
    resend.assert_not_called()


def test_resend_requires_application_base_url(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.secrets = {}

    monkeypatch.delenv(
        "TIMAN_APP_BASE_URL",
        raising=False,
    )

    resend = Mock()
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    assert len(fake_streamlit.warnings) == 1
    assert "temporarily unavailable" in (
        fake_streamlit.warnings[0]
    )
    resend.assert_not_called()


def test_resend_refuses_unconfigured_mock_provider(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "production")
    monkeypatch.setattr(
        auth_ui,
        "_configured_email_sender",
        Mock(
            side_effect=auth_ui.EmailDeliveryError(
                "Real email delivery is not configured.",
                stage="configuration",
            )
        ),
    )

    resend = Mock()
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    resend.assert_not_called()
    assert fake_streamlit.successes == []
    assert len(fake_streamlit.warnings) == 1
    assert "could not be completed" in fake_streamlit.warnings[0]


def test_production_resend_calls_service_without_mock_sender(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "TIMAN_DEV_EMAIL_SIMULATOR",
        "true",
    )

    resend = Mock(return_value=True)
    email_sender = object()
    monkeypatch.setattr(
        auth_ui,
        "_configured_email_sender",
        lambda base_url: email_sender,
    )
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    resend.assert_called_once_with(
        email="test@example.com",
        base_url="https://timanstat.example.com",
        sender=email_sender,
    )

    assert fake_streamlit.successes == [
        auth_ui.RESEND_GENERIC_MESSAGE
    ]
    assert fake_streamlit.markdown_messages == []


@pytest.mark.parametrize(
    "service_result",
    [True, False],
)
def test_production_response_does_not_reveal_account_existence(
    fake_streamlit,
    monkeypatch,
    service_result,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "production")
    monkeypatch.setenv(
        "TIMAN_DEV_EMAIL_SIMULATOR",
        "false",
    )

    monkeypatch.setattr(
        auth_ui,
        "_configured_email_sender",
        lambda base_url: object(),
    )
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        Mock(return_value=service_result),
    )

    auth_ui.render_resend_verification()

    assert fake_streamlit.successes == [
        auth_ui.RESEND_GENERIC_MESSAGE
    ]

    assert fake_streamlit.errors == []
    assert fake_streamlit.markdown_messages == []


def test_development_resend_displays_mock_verification_link(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv(
        "TIMAN_DEV_EMAIL_SIMULATOR",
        "true",
    )

    sender = auth_ui.MockEmailSender()

    monkeypatch.setattr(
        auth_ui,
        "_development_email_sender",
        Mock(return_value=sender),
    )

    def fake_resend(*, email, base_url, sender=None):
        sender.sent_messages.append(
            SimpleNamespace(
                recipient=email,
                subject="Verify your TimanStat account",
                body=(
                    "Please verify your email address:\n"
                    f"{base_url}/?verify_email=development-token"
                ),
            )
        )
        return True

    resend = Mock(side_effect=fake_resend)

    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    resend.assert_called_once_with(
        email="test@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert fake_streamlit.successes == [
        auth_ui.RESEND_GENERIC_MESSAGE
    ]

    assert any(
        "development-token" in message
        for message in fake_streamlit.markdown_messages
    )

    assert any(
        "Development mode" in message
        for message in fake_streamlit.warnings
    )

    assert fake_streamlit.errors == []


def test_development_resend_does_not_display_link_without_message(
    fake_streamlit,
    monkeypatch,
):
    sender = auth_ui.MockEmailSender()

    monkeypatch.setattr(
        auth_ui,
        "_development_email_sender",
        Mock(return_value=sender),
    )

    resend = Mock(return_value=False)

    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    assert fake_streamlit.successes == [
        auth_ui.RESEND_GENERIC_MESSAGE
    ]

    assert fake_streamlit.markdown_messages == []
    assert fake_streamlit.errors == []


def test_resend_handles_email_delivery_failure(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "production")

    resend = Mock(
        side_effect=auth_ui.EmailDeliveryError(
            "SMTP unavailable"
        )
    )

    monkeypatch.setattr(
        auth_ui,
        "_configured_email_sender",
        lambda base_url: object(),
    )
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    assert len(fake_streamlit.warnings) == 1
    assert "could not be completed" in (
        fake_streamlit.warnings[0]
    )
    assert fake_streamlit.successes == []


def test_resend_handles_unexpected_service_error(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "production")

    resend = Mock(
        side_effect=RuntimeError(
            "Internal database failure"
        )
    )

    monkeypatch.setattr(
        auth_ui,
        "_configured_email_sender",
        lambda base_url: object(),
    )
    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        resend,
    )

    auth_ui.render_resend_verification()

    assert len(fake_streamlit.warnings) == 1
    assert "could not be completed" in (
        fake_streamlit.warnings[0]
    )

    assert "Internal database failure" not in (
        fake_streamlit.warnings[0]
    )

    assert fake_streamlit.successes == []


def test_development_resend_does_not_show_invalid_verification_link(
    fake_streamlit,
    monkeypatch,
):
    sender = auth_ui.MockEmailSender()

    monkeypatch.setattr(
        auth_ui,
        "_development_email_sender",
        Mock(return_value=sender),
    )

    def fake_resend(*, email, base_url, sender=None):
        sender.sent_messages.append(
            SimpleNamespace(
                recipient=email,
                subject="Verify your TimanStat account",
                body="The verification URL is missing.",
            )
        )
        return True

    monkeypatch.setattr(
        auth_ui,
        "resend_email_verification",
        fake_resend,
    )

    auth_ui.render_resend_verification()

    assert fake_streamlit.successes == [
        auth_ui.RESEND_GENERIC_MESSAGE
    ]

    assert fake_streamlit.markdown_messages == []
    assert fake_streamlit.errors == []
