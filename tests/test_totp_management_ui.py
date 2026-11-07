"""UI tests for TimanStat authenticator-based account security."""

from __future__ import annotations

from contextlib import nullcontext

import pytest

from timan_intelligence.security import totp_management_ui as ui


class FakeStop(Exception):
    """Represent Streamlit's stop signal in isolated UI tests."""


class FakeStreamlit:
    """Minimal Streamlit surface used by the TOTP management interface."""

    def __init__(
        self,
        *,
        buttons=None,
        form_buttons=None,
        inputs=None,
        session_state=None,
    ):
        self.buttons = buttons or {}
        self.form_buttons = form_buttons or {}
        self.inputs = inputs or {}
        self.session_state = session_state if session_state is not None else {}
        self.messages = []
        self.codes = []
        self.rerun_called = False
        self.stop_called = False

    def __getattr__(self, name):
        if name in {
            "subheader",
            "warning",
            "success",
            "info",
            "error",
            "write",
            "caption",
            "markdown",
            "divider",
        }:
            return lambda message, *args, **kwargs: self.messages.append(
                (name, str(message))
            )
        raise AttributeError(name)

    def form(self, *args, **kwargs):
        return nullcontext()

    def text_input(self, label, *args, **kwargs):
        return self.inputs.get(label, "")

    def form_submit_button(self, label, *args, **kwargs):
        return self.form_buttons.get(label, False)

    def button(self, label, *args, **kwargs):
        return self.buttons.get(label, False)

    def code(self, value, *args, **kwargs):
        self.codes.append(value)

    def rerun(self):
        self.rerun_called = True
        raise FakeStop()

    def stop(self):
        self.stop_called = True
        raise FakeStop()


@pytest.fixture
def fake_st(monkeypatch):
    """Install a controllable Streamlit test double."""

    fake = FakeStreamlit(session_state={"user_id": "test-user"})
    monkeypatch.setattr(ui, "st", fake)
    monkeypatch.setattr(ui, "is_authenticated", lambda: True)
    monkeypatch.setattr(ui, "logout", lambda: None)
    return fake


def _message_contains(fake_st, message):
    return any(message in text for _, text in fake_st.messages)


def test_totp_management_requires_authentication(fake_st, monkeypatch):
    monkeypatch.setattr(ui, "is_authenticated", lambda: False)

    ui.render_totp_management()

    assert _message_contains(fake_st, "Sign in to manage two-factor authentication.")


def test_totp_management_clears_invalid_session(fake_st, monkeypatch):
    fake_st.session_state.pop("user_id")
    logout_calls = []
    monkeypatch.setattr(ui, "logout", lambda: logout_calls.append(True))

    ui.render_totp_management()

    assert logout_calls == [True]
    assert _message_contains(fake_st, "Your account session is invalid.")


def test_totp_management_starts_enrolment_and_displays_setup_key(
    fake_st,
    monkeypatch,
):
    monkeypatch.setattr(ui, "get_totp_status", lambda user_id: False)
    monkeypatch.setattr(
        ui,
        "begin_totp_enrolment",
        lambda user_id: {
            "secret": "JBSWY3DPEHPK3PXP",
            "provisioning_uri": "otpauth://totp/TimanStat:test",
        },
    )
    fake_st.buttons["Set up authenticator app"] = True

    with pytest.raises(FakeStop):
        ui.render_totp_management()

    assert (
        fake_st.session_state[ui._PENDING_SECRET_KEY]
        == "JBSWY3DPEHPK3PXP"
    )
    assert fake_st.rerun_called


def test_totp_management_confirms_enrolment_and_revokes_local_session(
    fake_st,
    monkeypatch,
):
    fake_st.session_state[ui._PENDING_SECRET_KEY] = "TESTSETUPKEY"
    fake_st.form_buttons[
        "Verify and enable two-factor authentication"
    ] = True
    fake_st.inputs["Six-digit authenticator code"] = "123456"
    confirmed = []
    logout_calls = []

    monkeypatch.setattr(ui, "get_totp_status", lambda user_id: False)
    monkeypatch.setattr(
        ui,
        "confirm_totp_enrolment",
        lambda user_id, code: confirmed.append((user_id, code)) or True,
    )
    monkeypatch.setattr(
        ui,
        "generate_recovery_codes",
        lambda user_id: ["CODE-ONE", "CODE-TWO"],
    )
    monkeypatch.setattr(ui, "logout", lambda: logout_calls.append(True))

    with pytest.raises(FakeStop):
        ui.render_totp_management()

    assert confirmed == [("test-user", "123456")]
    assert ui._PENDING_SECRET_KEY not in fake_st.session_state
    assert logout_calls == [True]
    assert fake_st.stop_called
    assert _message_contains(fake_st, "Two-factor authentication has been enabled.")
    assert "CODE-ONE\\nCODE-TWO" in fake_st.codes


def test_totp_management_rejects_invalid_confirmation_code(
    fake_st,
    monkeypatch,
):
    fake_st.session_state[ui._PENDING_SECRET_KEY] = "TESTSETUPKEY"
    fake_st.form_buttons[
        "Verify and enable two-factor authentication"
    ] = True
    fake_st.inputs["Six-digit authenticator code"] = "000000"

    monkeypatch.setattr(ui, "get_totp_status", lambda user_id: False)
    monkeypatch.setattr(
        ui,
        "confirm_totp_enrolment",
        lambda user_id, code: False,
    )

    ui.render_totp_management()

    assert ui._PENDING_SECRET_KEY in fake_st.session_state
    assert _message_contains(fake_st, "The code is invalid, expired or already used.")


def test_totp_management_cancels_enrolment_and_clears_local_secret(
    fake_st,
    monkeypatch,
):
    fake_st.session_state[ui._PENDING_SECRET_KEY] = "TESTSETUPKEY"
    fake_st.buttons["Cancel authenticator setup"] = True
    monkeypatch.setattr(ui, "get_totp_status", lambda user_id: False)

    with pytest.raises(FakeStop):
        ui.render_totp_management()

    assert ui._PENDING_SECRET_KEY not in fake_st.session_state
    assert fake_st.rerun_called
    assert _message_contains(fake_st, "The setup key has been cleared")


def test_totp_management_disables_authenticator_and_logs_out(
    fake_st,
    monkeypatch,
):
    fake_st.form_buttons[
        "Disable two-factor authentication"
    ] = True
    fake_st.inputs["Current password"] = "SecureTestPassword123!"
    fake_st.inputs["Authenticator code"] = "123456"
    logout_calls = []
    disable_calls = []

    monkeypatch.setattr(ui, "get_totp_status", lambda user_id: True)
    monkeypatch.setattr(ui, "get_recovery_code_count", lambda user_id: 8)
    monkeypatch.setattr(
        ui,
        "disable_totp_for_user",
        lambda user_id, current_password, code: (
            disable_calls.append((user_id, current_password, code)) or True
        ),
    )
    monkeypatch.setattr(ui, "logout", lambda: logout_calls.append(True))

    with pytest.raises(FakeStop):
        ui.render_totp_management()

    assert disable_calls == [
        ("test-user", "SecureTestPassword123!", "123456")
    ]
    assert logout_calls == [True]
    assert fake_st.stop_called
    assert _message_contains(fake_st, "Two-factor authentication has been disabled.")


def test_totp_management_reports_incorrect_disable_credentials(
    fake_st,
    monkeypatch,
):
    fake_st.form_buttons[
        "Disable two-factor authentication"
    ] = True
    fake_st.inputs["Current password"] = "WrongPassword123!"
    fake_st.inputs["Authenticator code"] = "000000"

    monkeypatch.setattr(ui, "get_totp_status", lambda user_id: True)
    monkeypatch.setattr(ui, "get_recovery_code_count", lambda user_id: 8)
    monkeypatch.setattr(
        ui,
        "disable_totp_for_user",
        lambda user_id, current_password, code: False,
    )

    ui.render_totp_management()

    assert _message_contains(
        fake_st,
        "The password or authenticator code is incorrect",
    )


def test_totp_management_handles_status_lookup_failure(
    fake_st,
    monkeypatch,
):
    def fail_status(user_id):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(ui, "get_totp_status", fail_status)

    ui.render_totp_management()

    assert _message_contains(
        fake_st,
        "Two-factor authentication settings are temporarily unavailable.",
    )
