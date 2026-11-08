
"""Tests for the TimanStat Streamlit authentication interface."""

from contextlib import nullcontext
from unittest.mock import Mock

import pytest

from timan_intelligence.security import auth_ui


class FakeStreamlit:
    """Minimal Streamlit test double for authentication UI tests."""

    def __init__(self, inputs=None, submitted=True, secrets=None):
        self.inputs = list(inputs or [])
        self.submitted = submitted
        self.secrets = secrets or {}
        self.session_state = {}
        self.errors = []
        self.warnings = []
        self.successes = []
        self.titles = []
        self.captions = []
        self.subheaders = []
        self.writes = []
        self.buttons = []
        self.query_params = {}
        self.checkbox_value = False
        self.checkboxes = []
        self.text_input_options = []

    def button(self, label, *args, **kwargs):
        self.buttons.append(label)
        return False

    def subheader(self, value):
        self.subheaders.append(value)

    def write(self, value):
        self.writes.append(value)

    def form(self, *args, **kwargs):
        return nullcontext()

    def text_input(self, *args, **kwargs):
        self.text_input_options.append((args, kwargs.copy()))
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

    def title(self, value):
        self.titles.append(value)

    def caption(self, value):
        self.captions.append(value)

    def tabs(self, labels):
        return (nullcontext(), nullcontext())

    def markdown(self, value):
        self.writes.append(value)


@pytest.fixture
def valid_registration_inputs():
    return [
        "Test User",
        "testuser",
        "testuser@example.com",
        "SecureTestPassword123!",
        "SecureTestPassword123!",
    ]


@pytest.fixture
def fake_streamlit(monkeypatch):
    fake = FakeStreamlit(
        secrets={
            "TIMAN_APP_BASE_URL": "https://timanstat.example.com"
        }
    )
    monkeypatch.setattr(auth_ui, "st", fake)
    return fake


def test_application_base_url_uses_streamlit_secrets(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.delenv("TIMAN_APP_BASE_URL", raising=False)

    assert auth_ui._application_base_url() == (
        "https://timanstat.example.com"
    )


def test_application_base_url_falls_back_to_environment(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.secrets = {}
    monkeypatch.setenv(
        "TIMAN_APP_BASE_URL",
        "https://environment.example.com",
    )

    assert auth_ui._application_base_url() == (
        "https://environment.example.com"
    )


def test_registration_does_not_submit_when_form_is_not_submitted(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.submitted = False
    register = Mock()
    monkeypatch.setattr(auth_ui, "register_user", register)

    auth_ui.render_registration()

    register.assert_not_called()
    assert fake_streamlit.errors == []


def test_registration_rejects_missing_required_fields(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "",
        "testuser",
        "testuser@example.com",
        "SecureTestPassword123!",
        "SecureTestPassword123!",
    ]
    register = Mock()
    monkeypatch.setattr(auth_ui, "register_user", register)

    auth_ui.render_registration()

    assert fake_streamlit.errors == [
        "Complete all required fields."
    ]
    register.assert_not_called()


def test_registration_rejects_password_mismatch(
    fake_streamlit,
    monkeypatch,
    valid_registration_inputs,
):
    fake_streamlit.inputs = valid_registration_inputs.copy()
    fake_streamlit.inputs[-1] = "DifferentPassword123!"
    register = Mock()
    monkeypatch.setattr(auth_ui, "register_user", register)

    auth_ui.render_registration()

    assert fake_streamlit.errors == [
        "The passwords do not match."
    ]
    register.assert_not_called()


def test_registration_rejects_short_password(
    fake_streamlit,
    monkeypatch,
):
    fake_streamlit.inputs = [
        "Test User",
        "testuser",
        "testuser@example.com",
        "short",
        "short",
    ]
    register = Mock()
    monkeypatch.setattr(auth_ui, "register_user", register)

    auth_ui.render_registration()

    assert fake_streamlit.errors == [
        "Your password must contain at least 12 characters."
    ]
    register.assert_not_called()


def test_registration_requires_application_base_url(
    fake_streamlit,
    monkeypatch,
    valid_registration_inputs,
):
    fake_streamlit.inputs = valid_registration_inputs.copy()
    fake_streamlit.secrets = {}
    monkeypatch.delenv("TIMAN_APP_BASE_URL", raising=False)
    register = Mock()
    monkeypatch.setattr(auth_ui, "register_user", register)

    auth_ui.render_registration()

    assert len(fake_streamlit.errors) == 1
    assert "application URL has not been configured" in (
        fake_streamlit.errors[0]
    )
    register.assert_not_called()


def test_registration_creates_account_and_sends_verification(
    fake_streamlit,
    monkeypatch,
    valid_registration_inputs,
):
    fake_streamlit.inputs = valid_registration_inputs.copy()
    register = Mock(return_value="user-123")
    send_verification = Mock()

    monkeypatch.setattr(auth_ui, "register_user", register)
    monkeypatch.setattr(
        auth_ui,
        "send_email_verification",
        send_verification,
    )

    auth_ui.render_registration()

    register.assert_called_once_with(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        password="SecureTestPassword123!",
    )
    send_verification.assert_called_once_with(
        user_id="user-123",
        base_url="https://timanstat.example.com",
    )
    assert len(fake_streamlit.successes) == 1
    assert "Check your email" in fake_streamlit.successes[0]


def test_registration_displays_validation_error_from_service(
    fake_streamlit,
    monkeypatch,
    valid_registration_inputs,
):
    fake_streamlit.inputs = valid_registration_inputs.copy()
    register = Mock(side_effect=ValueError("Email is already registered."))
    send_verification = Mock()

    monkeypatch.setattr(auth_ui, "register_user", register)
    monkeypatch.setattr(
        auth_ui,
        "send_email_verification",
        send_verification,
    )

    auth_ui.render_registration()

    assert fake_streamlit.errors == [
        "Email is already registered."
    ]
    send_verification.assert_not_called()


def test_registration_handles_email_delivery_failure(
    fake_streamlit,
    monkeypatch,
    valid_registration_inputs,
):
    fake_streamlit.inputs = valid_registration_inputs.copy()
    register = Mock(return_value="user-123")
    send_verification = Mock(
        side_effect=auth_ui.EmailDeliveryError("SMTP unavailable")
    )

    monkeypatch.setattr(auth_ui, "register_user", register)
    monkeypatch.setattr(
        auth_ui,
        "send_email_verification",
        send_verification,
    )

    auth_ui.render_registration()

    register.assert_called_once()
    assert len(fake_streamlit.warnings) == 1
    assert "account has been created" in fake_streamlit.warnings[0]
    assert fake_streamlit.successes == []


def test_registration_handles_unexpected_email_error(
    fake_streamlit,
    monkeypatch,
    valid_registration_inputs,
):
    fake_streamlit.inputs = valid_registration_inputs.copy()
    register = Mock(return_value="user-123")
    send_verification = Mock(
        side_effect=RuntimeError("Unexpected provider error")
    )

    monkeypatch.setattr(auth_ui, "register_user", register)
    monkeypatch.setattr(
        auth_ui,
        "send_email_verification",
        send_verification,
    )

    auth_ui.render_registration()

    assert len(fake_streamlit.warnings) == 1
    assert "email delivery could not be completed" in (
        fake_streamlit.warnings[0]
    )


def test_authentication_page_renders_login_and_registration_tabs(
    fake_streamlit,
    monkeypatch,
):
    render_login = Mock()
    render_registration = Mock()

    monkeypatch.setattr(auth_ui, "render_login", render_login)
    monkeypatch.setattr(
        auth_ui,
        "render_registration",
        render_registration,
    )

    auth_ui.render_authentication()

    assert fake_streamlit.titles == ["Welcome to TimanStat"]
    render_login.assert_called_once()
    render_registration.assert_called_once()
    assert fake_streamlit.buttons == [
        "Forgot password?",
        "Resend verification email",
    ]


def test_registration_does_not_leak_unexpected_account_error(
    fake_streamlit,
    monkeypatch,
    valid_registration_inputs,
):
    fake_streamlit.inputs = valid_registration_inputs.copy()
    register = Mock(side_effect=RuntimeError("Database credentials leaked"))
    send_verification = Mock()

    monkeypatch.setattr(auth_ui, "register_user", register)
    monkeypatch.setattr(
        auth_ui,
        "send_email_verification",
        send_verification,
    )

    auth_ui.render_registration()

    assert len(fake_streamlit.errors) == 1
    assert "system error" in fake_streamlit.errors[0]
    assert "Database credentials leaked" not in fake_streamlit.errors[0]
    send_verification.assert_not_called()


# Development email simulator security tests


def test_development_email_simulator_is_disabled_by_default(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.delenv("TIMAN_ENVIRONMENT", raising=False)
    monkeypatch.delenv("TIMAN_DEV_EMAIL_SIMULATOR", raising=False)

    assert auth_ui._development_email_sender(
        "https://timanstat-dev.streamlit.app"
    ) is None


def test_development_email_simulator_is_disabled_in_production(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "production")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")
    monkeypatch.setenv(
        "TIMAN_DEV_ALLOWED_HOSTS",
        "timanstat-dev.streamlit.app",
    )

    assert auth_ui._development_email_sender(
        "https://timanstat-dev.streamlit.app"
    ) is None


def test_development_email_simulator_requires_explicit_enablement(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "false")
    monkeypatch.setenv(
        "TIMAN_DEV_ALLOWED_HOSTS",
        "timanstat-dev.streamlit.app",
    )

    assert auth_ui._development_email_sender(
        "https://timanstat-dev.streamlit.app"
    ) is None


def test_development_email_simulator_rejects_unapproved_hostname(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")
    monkeypatch.setenv(
        "TIMAN_DEV_ALLOWED_HOSTS",
        "timanstat-dev.streamlit.app",
    )

    with pytest.raises(ValueError, match="not authorised"):
        auth_ui._development_email_sender(
            "https://timanstat.streamlit.app"
        )


def test_development_email_simulator_accepts_approved_hostname(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")
    monkeypatch.setenv(
        "TIMAN_DEV_ALLOWED_HOSTS",
        "timanstat-dev.streamlit.app",
    )

    sender = auth_ui._development_email_sender(
        "https://timanstat-dev.streamlit.app"
    )

    assert isinstance(sender, auth_ui.MockEmailSender)


def test_development_email_simulator_accepts_localhost(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")
    monkeypatch.delenv("TIMAN_DEV_ALLOWED_HOSTS", raising=False)

    sender = auth_ui._development_email_sender(
        "http://localhost:8501"
    )

    assert isinstance(sender, auth_ui.MockEmailSender)


def test_development_email_simulator_rejects_invalid_url(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")

    with pytest.raises(ValueError):
        auth_ui._development_email_sender("not-a-valid-url")


def test_development_email_simulator_uses_exact_hostname_match(
    fake_streamlit,
    monkeypatch,
):
    monkeypatch.setenv("TIMAN_ENVIRONMENT", "development")
    monkeypatch.setenv("TIMAN_DEV_EMAIL_SIMULATOR", "true")
    monkeypatch.setenv(
        "TIMAN_DEV_ALLOWED_HOSTS",
        "timanstat-dev.streamlit.app",
    )

    with pytest.raises(ValueError, match="not authorised"):
        auth_ui._development_email_sender(
            "https://timanstat-dev.streamlit.app.attacker.com"
        )


def test_extract_verification_url_from_mock_email():
    verification_url = (
        "https://timanstat-dev.streamlit.app/"
        "?verify_email=test-token-123"
    )

    body = (
        "Hello Test User,\n\n"
        "Please verify your email address:\n\n"
        f"{verification_url}\n\n"
        "Regards,\nTimanStat"
    )

    assert auth_ui._extract_verification_url(body) == (
        verification_url
    )


def test_extract_verification_url_returns_none_when_missing():
    body = (
        "Hello Test User,\n\n"
        "Thank you for registering with TimanStat.\n"
    )

    assert auth_ui._extract_verification_url(body) is None


def test_password_reset_link_opens_recovery_form_directly(
    fake_streamlit,
    monkeypatch,
):
    """A reset URL should show the new-password form immediately."""

    from timan_intelligence.security import password_reset_ui

    fake_streamlit.query_params = {
        "reset_password": "one-time-reset-token"
    }
    render_login = Mock()
    render_recovery = Mock()
    monkeypatch.setattr(auth_ui, "render_login", render_login)
    monkeypatch.setattr(
        password_reset_ui,
        "render_password_recovery",
        render_recovery,
    )

    auth_ui.render_authentication()

    render_login.assert_not_called()
    render_recovery.assert_called_once()
    assert fake_streamlit.session_state[
        auth_ui.AUTHENTICATION_VIEW_KEY
    ] == "password_recovery"

@pytest.mark.parametrize(
    ("show_password", "expected_type"),
    [
        (False, "password"),
        (True, "default"),
    ],
)
def test_registration_password_visibility_control(
    fake_streamlit,
    show_password,
    expected_type,
):
    """Both registration password fields follow the visibility toggle."""

    fake_streamlit.submitted = False
    fake_streamlit.checkbox_value = show_password

    auth_ui.render_registration()

    assert fake_streamlit.checkboxes == [
        (
            "Show passwords",
            {"key": "timanstat_show_registration_passwords"},
        )
    ]

    password_fields = [
        (args[0], kwargs)
        for args, kwargs in fake_streamlit.text_input_options
        if args and args[0] in {"Password", "Confirm password"}
    ]

    assert [label for label, _ in password_fields] == [
        "Password",
        "Confirm password",
    ]
    assert all(
        kwargs["type"] == expected_type
        for _, kwargs in password_fields
    )
    assert all(
        kwargs["autocomplete"] == "new-password"
        for _, kwargs in password_fields
    )



def test_registration_fields_support_browser_autofill(
    fake_streamlit,
):
    """Registration fields expose standard browser autofill hints."""

    fake_streamlit.submitted = False

    auth_ui.render_registration()

    options_by_label = {
        args[0]: kwargs
        for args, kwargs in fake_streamlit.text_input_options
    }
    assert options_by_label["Full name"]["autocomplete"] == "name"
    assert options_by_label["Username"]["autocomplete"] == "username"
    assert options_by_label["Email address"]["autocomplete"] == "email"

def test_resend_verification_email_field_supports_browser_autofill(
    fake_streamlit,
):
    """The resend-verification form exposes the email autofill hint."""

    fake_streamlit.submitted = False

    auth_ui.render_resend_verification()

    options_by_label = {
        args[0]: kwargs
        for args, kwargs in fake_streamlit.text_input_options
    }
    assert (
        options_by_label["Registered email address"]["autocomplete"]
        == "email"
    )



# Two-step login and password-manager autofill tests


def test_login_password_step_pairs_identifier_with_password_autofill(
    fake_streamlit,
    monkeypatch,
):
    """The password form includes its username field for password managers."""

    from timan_intelligence.security import auth

    fake_streamlit.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "saved@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    fake_streamlit.inputs = ["saved@example.com", ""]
    fake_streamlit.submitted = False

    monkeypatch.setattr(auth, "st", fake_streamlit)
    monkeypatch.setattr(auth, "is_authenticated", lambda: False)
    monkeypatch.setattr(auth, "is_totp_pending", lambda: False)

    auth.render_login()

    fields = {
        args[0]: kwargs
        for args, kwargs in fake_streamlit.text_input_options
    }
    assert fields["Email address or username"]["value"] == "saved@example.com"
    assert fields["Email address or username"]["autocomplete"] == "username"
    assert fields["Password"]["autocomplete"] == "current-password"
    assert fields["Password"]["type"] == "password"


def test_login_uses_edited_identifier_after_password_step(
    fake_streamlit,
    monkeypatch,
):
    """A corrected identifier is used and retained after failed sign-in."""

    from unittest.mock import Mock

    from timan_intelligence.security import auth

    fake_streamlit.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "saved@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    fake_streamlit.inputs = [
        "corrected@example.com",
        "incorrect-password",
    ]
    fake_streamlit.submitted = True

    monkeypatch.setattr(auth, "st", fake_streamlit)
    monkeypatch.setattr(auth, "is_authenticated", lambda: False)
    monkeypatch.setattr(auth, "is_totp_pending", lambda: False)
    monkeypatch.setattr(
        auth,
        "is_login_temporarily_locked",
        lambda identifier: False,
    )
    authenticate = Mock(return_value=False)
    monkeypatch.setattr(auth, "authenticate_user", authenticate)

    auth.render_login()

    authenticate.assert_called_once_with(
        "corrected@example.com",
        "incorrect-password",
    )
    assert fake_streamlit.session_state[auth.LOGIN_IDENTIFIER_KEY] == (
        "corrected@example.com"
    )
    assert len(fake_streamlit.errors) == 1
