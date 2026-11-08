
"""End-to-end registration flow tests for the TimanStat development email simulator."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from timan_intelligence.security import auth_ui


class FakeStreamlit:
    """Minimal Streamlit test double for registration flow tests."""

    def __init__(self):
        self.secrets = {
            "TIMAN_APP_BASE_URL": (
                "https://timanstat-dev.streamlit.app"
            )
        }
        self.inputs = [
            "Test User",
            "testuser",
            "testuser@example.com",
            "SecureTestPassword123!",
            "SecureTestPassword123!",
        ]
        self.session_state = {}
        self.errors = []
        self.warnings = []
        self.successes = []
        self.markdown_messages = []
        self.captions = []
        self.subheaders = []
        self.writes = []
        self.checkbox_value = False
        self.checkboxes = []

    def checkbox(self, label, *args, **kwargs):
        self.checkboxes.append((label, kwargs.copy()))
        return self.checkbox_value

    def subheader(self, value):
        self.subheaders.append(value)

    def write(self, value):
        self.writes.append(value)

    def form(self, *args, **kwargs):
        return nullcontext()

    def text_input(self, *args, **kwargs):
        return self.inputs.pop(0)

    def form_submit_button(self, *args, **kwargs):
        return True

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
    monkeypatch.setattr(auth_ui, "st", fake)
    return fake


def test_development_registration_displays_generated_verification_link(
    fake_streamlit,
    monkeypatch,
):
    """Development registration should display the mock email link."""

    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")
    monkeypatch.setenv(
        "TIMAN_DEV_ALLOWED_HOSTS",
        "timanstat-dev.streamlit.app",
    )

    register = Mock(return_value="test-user-123")
    monkeypatch.setattr(auth_ui, "register_user", register)

    captured = {}

    def fake_send_verification(
        *,
        user_id,
        base_url,
        sender=None,
    ):
        captured["user_id"] = user_id
        captured["base_url"] = base_url
        captured["sender"] = sender

        sender.sent_messages.append(
            SimpleNamespace(
                recipient="testuser@example.com",
                subject="Verify your TimanStat email",
                body=(
                    "Please verify your email address:\n"
                    f"{base_url}/?verify_email=development-test-token"
                ),
            )
        )

    monkeypatch.setattr(
        auth_ui,
        "send_email_verification",
        fake_send_verification,
    )

    auth_ui.render_registration()

    assert captured["user_id"] == "test-user-123"
    assert captured["base_url"] == (
        "https://timanstat-dev.streamlit.app"
    )

    assert isinstance(
        captured["sender"],
        auth_ui.MockEmailSender,
    )

    assert fake_streamlit.successes == [
        "Your test account has been created successfully."
    ]

    assert any(
        "development-test-token" in message
        for message in fake_streamlit.markdown_messages
    )

    assert any(
        "Development mode" in message
        for message in fake_streamlit.warnings
    )

    assert fake_streamlit.errors == []


def test_production_registration_does_not_display_simulator_link(
    fake_streamlit,
    monkeypatch,
):
    """Production registration must use normal email delivery."""

    monkeypatch.setenv("TIMAN_ENVIRONMENT", "production")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")
    monkeypatch.setenv(
        "TIMAN_DEV_ALLOWED_HOSTS",
        "timanstat-dev.streamlit.app",
    )

    register = Mock(return_value="production-user-123")
    monkeypatch.setattr(auth_ui, "register_user", register)

    send_verification = Mock()
    monkeypatch.setattr(
        auth_ui,
        "send_email_verification",
        send_verification,
    )

    auth_ui.render_registration()

    send_verification.assert_called_once_with(
        user_id="production-user-123",
        base_url="https://timanstat-dev.streamlit.app",
    )

    assert fake_streamlit.markdown_messages == []

    assert fake_streamlit.successes == [
        "Your account has been created. Check your email for the "
        "verification link before signing in."
    ]

    assert fake_streamlit.errors == []
