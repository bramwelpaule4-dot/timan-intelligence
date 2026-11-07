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
        self.forms = []
        self.rerun_count = 0

    def form(self, *args, **kwargs):
        self.forms.append(args[0] if args else None)
        return nullcontext()

    def text_input(self, *args, **kwargs):
        if self.inputs:
            return self.inputs.pop(0)
        return ""

    def form_submit_button(self, *args, **kwargs):
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
        return False

    def rerun(self):
        self.rerun_count += 1


@pytest.fixture
def login_ui(monkeypatch):
    fake = FakeStreamlit()
    monkeypatch.setattr(auth, "st", fake)
    monkeypatch.setattr(auth, "is_authenticated", lambda: False)
    monkeypatch.setattr(auth, "is_totp_pending", lambda: False)
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
    login_ui.inputs = ["StrongPassword123!"]

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
    login_ui.inputs = ["WrongPassword123!"]

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
    login_ui.inputs = ["StrongPassword123!"]

    monkeypatch.setattr(
        auth,
        "authenticate_user",
        lambda identifier, password: False,
    )
    monkeypatch.setattr(auth, "is_totp_pending", lambda: True)

    auth.render_login()

    assert login_ui.rerun_count == 1
    assert login_ui.errors == []
    assert login_ui.session_state[auth.LOGIN_IDENTIFIER_KEY] == (
        "analyst@example.com"
    )


def test_password_step_allows_user_to_change_account(
    login_ui,
):
    login_ui.session_state.update(
        {
            auth.LOGIN_IDENTIFIER_KEY: "analyst@example.com",
            auth.LOGIN_STEP_KEY: "password",
        }
    )

    # The fake button is not clicked; the control is rendered for the user.
    auth.render_login()

    assert "Use a different account" in login_ui.buttons
