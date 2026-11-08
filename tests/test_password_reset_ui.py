
"""Tests for the TimanStat Streamlit password-recovery interface."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from timan_intelligence.security import password_reset_ui


class FakeStreamlit:
    """Minimal Streamlit test double for password-recovery tests."""

    def __init__(
        self,
        inputs=None,
        submitted=True,
        query_params=None,
    ):
        self.inputs = list(inputs or [])
        self.submitted = submitted
        self.query_params = query_params if query_params is not None else {}
        self.session_state = {}
        self.errors = []
        self.warnings = []
        self.successes = []
        self.subheaders = []
        self.writes = []
        self.markdown_messages = []
        self.captions = []
        self.checkbox_value = False
        self.checkboxes = []
        self.text_input_options = []

    def subheader(self, value):
        self.subheaders.append(value)

    def write(self, value):
        self.writes.append(value)

    def form(self, *args, **kwargs):
        return nullcontext()

    def text_input(self, *args, **kwargs):
        self.text_input_options.append(kwargs.copy())
        if self.inputs:
            return self.inputs.pop(0)
        return ""

    def checkbox(self, label, *args, **kwargs):
        self.checkboxes.append((label, kwargs.copy()))
        return self.checkbox_value

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
    fake = FakeStreamlit()

    monkeypatch.setattr(
        password_reset_ui,
        "st",
        fake,
    )

    monkeypatch.setattr(
        password_reset_ui,
        "_application_base_url",
        lambda: "https://timanstat.example.com",
    )

    monkeypatch.setattr(
        password_reset_ui,
        "_development_email_sender",
        lambda base_url: None,
    )

    return fake


def test_password_reset_request_does_not_submit_when_form_is_not_submitted(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.submitted = False

    request = Mock()

    monkeypatch.setattr(
        password_reset_ui,
        "request_password_reset",
        request,
    )

    password_reset_ui.render_password_reset_request()

    request.assert_not_called()
    assert fake_streamlit.errors == []
    assert fake_streamlit.successes == []


def test_password_reset_request_rejects_empty_email(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = ["   "]

    request = Mock()

    monkeypatch.setattr(
        password_reset_ui,
        "request_password_reset",
        request,
    )

    password_reset_ui.render_password_reset_request()

    assert fake_streamlit.errors == [
        "Enter your registered email address."
    ]

    request.assert_not_called()


def test_password_reset_request_uses_generic_response(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = ["unknown@example.com"]

    request = Mock(return_value=False)

    monkeypatch.setattr(
        password_reset_ui,
        "request_password_reset",
        request,
    )

    password_reset_ui.render_password_reset_request()

    request.assert_called_once_with(
        email="unknown@example.com",
        base_url="https://timanstat.example.com",
        sender=None,
    )

    assert fake_streamlit.successes == [
        password_reset_ui.PASSWORD_RESET_GENERIC_MESSAGE
    ]

    assert "unknown@example.com" not in (
        fake_streamlit.successes[0]
    )


def test_password_reset_request_handles_missing_application_url(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = ["test@example.com"]

    monkeypatch.setattr(
        password_reset_ui,
        "_application_base_url",
        lambda: "",
    )

    request = Mock()

    monkeypatch.setattr(
        password_reset_ui,
        "request_password_reset",
        request,
    )

    password_reset_ui.render_password_reset_request()

    request.assert_not_called()

    assert len(fake_streamlit.warnings) == 1
    assert fake_streamlit.successes == []


def test_password_reset_request_handles_email_delivery_failure(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = ["test@example.com"]

    request = Mock(
        side_effect=password_reset_ui.EmailDeliveryError(
            "SMTP credentials unavailable"
        )
    )

    monkeypatch.setattr(
        password_reset_ui,
        "request_password_reset",
        request,
    )

    password_reset_ui.render_password_reset_request()

    assert len(fake_streamlit.warnings) == 1
    assert fake_streamlit.successes == []


def test_production_password_reset_does_not_display_reset_link(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = ["test@example.com"]

    request = Mock(return_value=True)

    monkeypatch.setattr(
        password_reset_ui,
        "request_password_reset",
        request,
    )

    monkeypatch.setattr(
        password_reset_ui,
        "_development_email_sender",
        lambda base_url: None,
    )

    password_reset_ui.render_password_reset_request()

    request.assert_called_once()

    assert fake_streamlit.successes == [
        password_reset_ui.PASSWORD_RESET_GENERIC_MESSAGE
    ]

    assert fake_streamlit.markdown_messages == []
    assert fake_streamlit.warnings == []


def test_development_password_reset_displays_mock_link(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = ["test@example.com"]

    sender = password_reset_ui.MockEmailSender()

    reset_url = (
        "https://timanstat-dev.streamlit.app/"
        "?reset_password=development-test-token"
    )

    sender.sent_messages.append(
        SimpleNamespace(
            recipient="test@example.com",
            subject="Reset your TimanStat password",
            body=f"Reset your password here:\n{reset_url}",
        )
    )

    request = Mock(return_value=True)

    monkeypatch.setattr(
        password_reset_ui,
        "request_password_reset",
        request,
    )

    monkeypatch.setattr(
        password_reset_ui,
        "_development_email_sender",
        lambda base_url: sender,
    )

    password_reset_ui.render_password_reset_request()

    request.assert_called_once_with(
        email="test@example.com",
        base_url="https://timanstat.example.com",
        sender=sender,
    )

    assert any(
        "development-test-token" in message
        for message in fake_streamlit.markdown_messages
    )

    assert any(
        "Development mode" in message
        for message in fake_streamlit.warnings
    )


def test_extract_password_reset_url_from_email():
    """Extract a reset URL from an email containing real line breaks."""

    reset_url = (
        "https://timanstat.example.com/"
        "?reset_password=test-token-123"
    )

    body = (
        "Hello,\n\n"
        "Reset your password using this link:\n"
        f"{reset_url}\n"
    )

    assert password_reset_ui._extract_password_reset_url(
        body
    ) == reset_url


def test_extract_password_reset_url_returns_none_when_missing():
    body = "This email contains no reset link."

    assert password_reset_ui._extract_password_reset_url(
        body
    ) is None


def test_password_reset_password_fields_are_masked_by_default(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.submitted = False
    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        Mock(),
    )

    password_reset_ui.render_password_reset_form("test-token")

    password_options = [
        options
        for options in fake_streamlit.text_input_options
        if options.get("autocomplete") == "new-password"
    ]

    assert len(password_options) == 2
    assert all(options["type"] == "password" for options in password_options)
    assert fake_streamlit.checkboxes[0][0] == "Show passwords"


def test_password_reset_password_fields_can_be_shown(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.submitted = False
    fake_streamlit.checkbox_value = True
    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        Mock(),
    )

    password_reset_ui.render_password_reset_form("test-token")

    password_options = [
        options
        for options in fake_streamlit.text_input_options
        if options.get("autocomplete") == "new-password"
    ]

    assert len(password_options) == 2
    assert all(options["type"] == "default" for options in password_options)


def test_password_reset_rejects_empty_password_fields(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = ["", ""]

    reset = Mock()

    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        reset,
    )

    password_reset_ui.render_password_reset_form(
        "test-token"
    )

    assert fake_streamlit.errors == [
        "Complete both password fields."
    ]

    reset.assert_not_called()


def test_password_reset_rejects_password_mismatch(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "SecurePassword123!",
        "DifferentPassword123!",
    ]

    reset = Mock()

    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        reset,
    )

    password_reset_ui.render_password_reset_form(
        "test-token"
    )

    assert fake_streamlit.errors == [
        "The passwords do not match."
    ]

    reset.assert_not_called()


def test_password_reset_rejects_password_shorter_than_12_characters(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "Short123!",
        "Short123!",
    ]

    reset = Mock()

    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        reset,
    )

    password_reset_ui.render_password_reset_form(
        "test-token"
    )

    assert fake_streamlit.errors == [
        "Your password must contain at least 12 characters."
    ]

    reset.assert_not_called()


def test_password_reset_rejects_invalid_or_expired_token(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "SecurePassword123!",
        "SecurePassword123!",
    ]

    reset = Mock(return_value=False)

    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        reset,
    )

    password_reset_ui.render_password_reset_form(
        "invalid-token"
    )

    reset.assert_called_once_with(
        token="invalid-token",
        new_password="SecurePassword123!",
    )

    assert len(fake_streamlit.errors) == 1

    assert "invalid, expired, or" in (
        fake_streamlit.errors[0]
    )

    assert fake_streamlit.successes == []


def test_password_reset_handles_successful_password_change(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "SecurePassword123!",
        "SecurePassword123!",
    ]

    reset = Mock(return_value=True)

    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        reset,
    )

    password_reset_ui.render_password_reset_form(
        "valid-token"
    )

    reset.assert_called_once_with(
        token="valid-token",
        new_password="SecurePassword123!",
    )

    assert fake_streamlit.successes == [
        "Your password has been changed successfully. "
        "You can now return to the sign-in page."
    ]

    assert fake_streamlit.errors == []


def test_password_recovery_renders_request_form_without_token(
    fake_streamlit,
):
    fake_streamlit.query_params = {}

    password_reset_ui.render_password_recovery()

    assert "Forgot your password?" in (
        fake_streamlit.subheaders
    )


def test_password_recovery_renders_reset_form_with_token(
    fake_streamlit,
):
    fake_streamlit.query_params = {
        "reset_password": "valid-token"
    }

    password_reset_ui.render_password_recovery()

    assert "Choose a new password" in (
        fake_streamlit.subheaders
    )


def test_password_recovery_supports_list_query_parameter(
    fake_streamlit,
):
    fake_streamlit.query_params = {
        "reset_password": ["valid-token"]
    }

    password_reset_ui.render_password_recovery()

    assert "Choose a new password" in (
        fake_streamlit.subheaders
    )


def test_password_recovery_rejects_invalid_application_url(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.query_params = {
        "reset_password": "valid-token"
    }

    monkeypatch.setattr(
        password_reset_ui,
        "_application_base_url",
        lambda: "javascript:invalid-url",
    )

    password_reset_ui.render_password_recovery()

    assert len(fake_streamlit.warnings) == 1
    assert "Choose a new password" not in (
        fake_streamlit.subheaders
    )


def test_password_recovery_handles_missing_query_params(
    fake_streamlit,
):
    fake_streamlit.query_params = None

    password_reset_ui.render_password_recovery()

    assert "Forgot your password?" in (
        fake_streamlit.subheaders
    )


def test_successful_password_reset_clears_token_from_url(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "SecurePassword123!",
        "SecurePassword123!",
    ]

    fake_streamlit.query_params = {
        "reset_password": "valid-token"
    }

    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        Mock(return_value=True),
    )

    password_reset_ui.render_password_reset_form(
        "valid-token"
    )

    assert "reset_password" not in fake_streamlit.query_params

    assert len(fake_streamlit.successes) == 1
    assert fake_streamlit.errors == []


def test_failed_password_reset_preserves_token_in_url(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "SecurePassword123!",
        "SecurePassword123!",
    ]

    fake_streamlit.query_params = {
        "reset_password": "invalid-token"
    }

    monkeypatch.setattr(
        password_reset_ui,
        "reset_password_with_token",
        Mock(return_value=False),
    )

    password_reset_ui.render_password_reset_form(
        "invalid-token"
    )

    assert (
        fake_streamlit.query_params["reset_password"]
        == "invalid-token"
    )

    assert fake_streamlit.successes == []
    assert len(fake_streamlit.errors) == 1

def test_password_reset_request_email_supports_browser_autofill(
    fake_streamlit,
):
    """The password-reset request exposes the email autofill hint."""

    fake_streamlit.submitted = False

    password_reset_ui.render_password_reset_request()

    email_options = [
        options
        for options in fake_streamlit.text_input_options
        if options.get("autocomplete") == "email"
    ]
    assert len(email_options) == 1



def test_password_reset_request_prefills_email_from_sign_in():
    """The recovery form displays the email carried from sign-in."""

    from timan_intelligence.security.auth_ui import (
        PASSWORD_RESET_EMAIL_PREFILL_KEY,
    )

    fake = FakeStreamlit(submitted=False)
    fake.session_state[PASSWORD_RESET_EMAIL_PREFILL_KEY] = (
        "person@example.com"
    )
    password_reset_ui.st = fake

    password_reset_ui.render_password_reset_request()

    email_options = next(
        options
        for options in fake.text_input_options
        if options.get("autocomplete") == "email"
    )
    assert email_options["value"] == "person@example.com"
