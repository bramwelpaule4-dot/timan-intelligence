"""Tests for the staged TimanStat sign-in interface."""

from contextlib import nullcontext

import pytest

from timan_intelligence.security import auth


class FakeStreamlit:
    """Small Streamlit test double for the login UI."""

    def __init__(self, inputs=None, submitted=True):
        self.inputs = list(inputs or [])
        self.submitted = submitted
        self.session_state = {}
        self.errors = []
        self.successes = []
        self.captions = []
        self.subheaders = []
        self.infos = []
        self.buttons = []
        self.button_results = {}
        self.forms = []
        self.checkbox_value = False
        self.checkboxes = []
        self.text_input_options = []
        self.submit_button_options = []
        self.rerun_count = 0

    def form(self, *args, **kwargs):
        self.forms.append(args[0] if args else None)
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
        self.submit_button_options.append(kwargs.copy())
        return self.submitted

    def subheader(self, value):
        self.subheaders.append(value)

    def caption(self, value):
        self.captions.append(value)

    def info(self, value):
        self.infos.append(value)

    def error(self, value):
        self.errors.append(value)

    def success(self, value):
        self.successes.append(value)

    def button(self, label, *args, **kwargs):
        self.buttons.append(label)
        return self.button_results.get(label, False)

    def rerun(self):
        self.rerun_count += 1


@pytest.fixture
def login_ui(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(auth, "st", fake)
    monkeypatch.setattr(auth, "is_authenticated", lambda: False)
    monkeypatch.setattr(auth, "is_totp_pending", lambda: False)
    monkeypatch.setattr(
        auth,
        "is_login_temporarily_locked",
        lambda identifier: False,
    )
    return fake


def test_login_starts_with_identifier_step(login_ui):
    login_ui.submitted = False

    auth.render_login()

    assert login_ui.subheaders == ["Welcome back"]
    assert login_ui.forms == ["timanstat_login_identifier_form"]
    assert login_ui.errors == []


def test_identifier_submission_advances_to_password_step(
    login_ui,
):
    login_ui.inputs = ["analyst@example.com"]

    auth.render_login()

    assert login_ui.session_state[auth.LOGIN_IDENTIFIER_KEY] == (
        "analyst@example.com"
    )
    assert login_ui.session_state[auth.LOGIN_STEP_KEY] == "password"
    assert login_ui.rerun_count == 1
    assert login_ui.errors == []


def test_identifier_step_rejects_blank_identifier(login_ui):
    login_ui.inputs = ["   "]

    auth.render_login()

    assert login_ui.errors == [
        "Enter your email address or username."
    ]
    assert auth.LOGIN_IDENTIFIER_KEY not in login_ui.session_state
    assert login_ui.rerun_count == 0


def test_password_step_establishes_session_and_clears_login_state(
    login_ui,
    monkeypatch,
):
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    login_ui.inputs = ["analyst@example.com", "StrongPassword123!"]

    monkeypatch.setattr(
        auth,
        "authenticate_user",
        lambda identifier, password: (
            identifier == "analyst@example.com"
            and password == "StrongPassword123!"
        ),
    )

    auth.render_login()

    assert auth.LOGIN_IDENTIFIER_KEY not in login_ui.session_state
    assert auth.LOGIN_STEP_KEY not in login_ui.session_state
    assert login_ui.successes == ["Authentication successful."]
    assert login_ui.rerun_count == 1


def test_password_step_shows_controlled_error_for_failed_login(
    login_ui,
    monkeypatch,
):
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    login_ui.inputs = ["analyst@example.com", "WrongPassword123!"]

    monkeypatch.setattr(
        auth,
        "authenticate_user",
        lambda identifier, password: False,
    )

    auth.render_login()

    assert len(login_ui.errors) == 1
    assert "could not sign you in" in login_ui.errors[0].lower()
    assert login_ui.rerun_count == 0


def test_password_step_hands_off_to_mfa_without_creating_full_session(
    login_ui,
    monkeypatch,
):
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    login_ui.inputs = ["analyst@example.com", "StrongPassword123!"]

    monkeypatch.setattr(
        auth,
        "authenticate_user",
        lambda identifier, password: False,
    )
    pending_states = iter([False, True])
    monkeypatch.setattr(
        auth,
        "is_totp_pending",
        lambda: next(pending_states),
    )

    auth.render_login()

    assert login_ui.rerun_count == 1
    assert login_ui.errors == []
    assert login_ui.session_state[auth.LOGIN_IDENTIFIER_KEY] == (
        "analyst@example.com"
    )


def test_password_step_allows_user_to_change_account(
    login_ui,
):
    login_ui.submitted = False
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )

    # A non-submitted password form still renders the account-switch control.
    auth.render_login()

    assert "Use a different account" in login_ui.buttons


def test_password_step_explains_temporary_lockout(
    login_ui,
    monkeypatch,
):
    """A locked identifier receives a clear cooldown message."""

    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    login_ui.inputs = ["analyst@example.com", "WrongPassword123!"]

    monkeypatch.setattr(
        auth,
        "authenticate_user",
        lambda identifier, password: False,
    )
    monkeypatch.setattr(
        auth,
        "is_login_temporarily_locked",
        lambda identifier: identifier == "analyst@example.com",
    )

    auth.render_login()

    assert login_ui.errors == [
        "Too many unsuccessful sign-in attempts. For your "
        "security, sign-in is temporarily paused for this "
        "identifier. Please wait 15 minutes before trying again."
    ]
    assert login_ui.rerun_count == 0

def test_password_step_hides_password_by_default(
    login_ui,
):
    """The password field is masked until the user opts to reveal it."""
    login_ui.submitted = False
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )

    auth.render_login()

    password_options = next(
        options
        for options in login_ui.text_input_options
        if options.get("autocomplete") == "current-password"
    )
    assert password_options["type"] == "password"
    assert login_ui.checkboxes[0][0] == "Show password"


def test_password_step_can_show_password(
    login_ui,
):
    """The visibility control switches the password field to plain text."""
    login_ui.submitted = False
    login_ui.checkbox_value = True
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )

    auth.render_login()

    password_options = next(
        options
        for options in login_ui.text_input_options
        if options.get("autocomplete") == "current-password"
    )
    assert password_options["type"] == "default"




def test_mfa_code_field_supports_one_time_code_autofill(
    login_ui,
    monkeypatch,
):
    """Authenticator fields advertise OTP autofill to supported devices."""

    login_ui.submitted = False
    monkeypatch.setattr(
        auth,
        "is_totp_pending",
        lambda: True,
    )

    auth.render_login()

    mfa_options = next(
        options
        for options in login_ui.text_input_options
        if options.get("max_chars") == 40
    )
    assert mfa_options["autocomplete"] == "one-time-code"

def test_login_explains_expired_mfa_challenge_once(login_ui, monkeypatch):
    """An expired second-factor challenge receives a clear recovery message."""

    login_ui.session_state[auth.PENDING_AUTHENTICATION_EXPIRED_KEY] = True
    login_ui.submitted = False

    auth.render_login()

    assert login_ui.infos == [
        "Your verification session has expired. Please sign in again "
        "to receive a new authenticator challenge."
    ]
    assert auth.PENDING_AUTHENTICATION_EXPIRED_KEY not in login_ui.session_state

    login_ui.infos.clear()
    auth.render_login()
    assert login_ui.infos == []



def test_mfa_login_explains_temporary_verification_lockout(
    login_ui,
    monkeypatch,
):
    """A locked MFA challenge receives a clear cooldown message."""

    login_ui.inputs = ["123456"]
    monkeypatch.setattr(
        auth,
        "is_totp_pending",
        lambda: True,
    )
    monkeypatch.setattr(
        auth,
        "verify_pending_second_factor",
        lambda code: False,
    )
    monkeypatch.setattr(
        auth,
        "is_pending_second_factor_temporarily_locked",
        lambda: True,
    )

    auth.render_login()

    assert login_ui.errors == [
        "Too many unsuccessful verification attempts. For your "
        "security, verification is temporarily paused for this "
        "account. Please wait 15 minutes before trying again."
    ]
    assert login_ui.rerun_count == 0


def test_mfa_login_keeps_generic_error_when_not_locked(
    login_ui,
    monkeypatch,
):
    """An ordinary invalid code keeps the existing safe error message."""

    login_ui.inputs = ["000000"]
    monkeypatch.setattr(
        auth,
        "is_totp_pending",
        lambda: True,
    )
    monkeypatch.setattr(
        auth,
        "verify_pending_second_factor",
        lambda code: False,
    )
    monkeypatch.setattr(
        auth,
        "is_pending_second_factor_temporarily_locked",
        lambda: False,
    )

    auth.render_login()

    assert login_ui.errors == [
        "We could not verify that code. Check it and try again, "
        "or sign in again if the verification request has expired."
    ]
    assert login_ui.rerun_count == 0


def test_locked_mfa_form_disables_code_entry_and_submission(
    login_ui,
    monkeypatch,
):
    """A locked challenge cannot submit another verification attempt."""

    login_ui.inputs = ["123456"]
    monkeypatch.setattr(auth, "is_totp_pending", lambda: True)
    monkeypatch.setattr(
        auth,
        "is_pending_second_factor_temporarily_locked",
        lambda: True,
    )
    verification_calls = []
    monkeypatch.setattr(
        auth,
        "verify_pending_second_factor",
        lambda code: verification_calls.append(code) or False,
    )

    auth.render_login()

    mfa_options = next(
        options
        for options in login_ui.text_input_options
        if options.get("max_chars") == 40
    )
    assert mfa_options["disabled"] is True
    assert login_ui.submit_button_options[-1]["disabled"] is True
    assert verification_calls == []
    assert login_ui.errors == [
        "Too many unsuccessful verification attempts. For your "
        "security, verification is temporarily paused for this "
        "account. Please wait 15 minutes before trying again."
    ]
    assert "Cancel sign in" in login_ui.buttons


def test_locked_password_step_disables_credentials_and_sign_in(
    login_ui,
    monkeypatch,
):
    """A locked identifier cannot submit another password attempt."""

    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    login_ui.submitted = True
    login_ui.inputs = ["analyst@example.com", "WrongPassword123!"]
    monkeypatch.setattr(
        auth,
        "is_login_temporarily_locked",
        lambda identifier: identifier == "analyst@example.com",
    )
    authentication_calls = []
    monkeypatch.setattr(
        auth,
        "authenticate_user",
        lambda identifier, password: authentication_calls.append(
            (identifier, password)
        ) or False,
    )

    auth.render_login()

    username_options = next(
        options
        for options in login_ui.text_input_options
        if options.get("autocomplete") == "username"
    )
    password_options = next(
        options
        for options in login_ui.text_input_options
        if options.get("autocomplete") == "current-password"
    )
    assert username_options["disabled"] is True
    assert password_options["disabled"] is True
    assert login_ui.checkboxes[0][1]["disabled"] is True
    assert login_ui.submit_button_options[-1]["disabled"] is True
    assert authentication_calls == []
    assert login_ui.errors == [
        "Too many unsuccessful sign-in attempts. For your "
        "security, sign-in is temporarily paused for this "
        "identifier. Please wait 15 minutes before trying again."
    ]
    assert "Use a different account" in login_ui.buttons


def test_locked_password_step_can_recheck_lockout(login_ui, monkeypatch):
    """The user can refresh the password lockout status after waiting."""

    login_ui.submitted = False
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )
    monkeypatch.setattr(
        auth,
        "is_login_temporarily_locked",
        lambda identifier: True,
    )
    login_ui.button_results["Check sign-in again"] = True

    auth.render_login()

    assert login_ui.rerun_count == 1


def test_locked_mfa_challenge_can_recheck_lockout(login_ui, monkeypatch):
    """The user can refresh the MFA lockout status after waiting."""

    monkeypatch.setattr(auth, "is_totp_pending", lambda: True)
    monkeypatch.setattr(
        auth,
        "is_pending_second_factor_temporarily_locked",
        lambda: True,
    )
    login_ui.button_results["Check verification again"] = True

    auth.render_login()

    assert login_ui.rerun_count == 1
