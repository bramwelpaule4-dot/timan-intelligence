"""Tests for the TimanStat authenticated password-change interface."""

from contextlib import nullcontext

import pytest

from timan_intelligence.security import password_change_ui


class FakeStreamlit:
    """Minimal Streamlit test double for password-change tests."""

    def __init__(self, checkbox_value=False):
        self.session_state = {"user_id": "user-123"}
        self.text_input_options = []
        self.checkboxes = []
        self.checkbox_value = checkbox_value
        self.submitted = False

    def subheader(self, value):
        pass

    def write(self, value):
        pass

    def caption(self, value):
        pass

    def form(self, *args, **kwargs):
        return nullcontext()

    def checkbox(self, label, *args, **kwargs):
        self.checkboxes.append((label, kwargs.copy()))
        return self.checkbox_value

    def text_input(self, *args, **kwargs):
        self.text_input_options.append((args, kwargs.copy()))
        return ""

    def form_submit_button(self, *args, **kwargs):
        return self.submitted


def _render_password_change(monkeypatch, checkbox_value=False):
    fake_streamlit = FakeStreamlit(checkbox_value=checkbox_value)
    monkeypatch.setattr(password_change_ui, "st", fake_streamlit)
    monkeypatch.setattr(
        password_change_ui,
        "is_authenticated",
        lambda: True,
    )

    password_change_ui.render_password_change()
    return fake_streamlit


def test_password_change_fields_support_browser_autofill(monkeypatch):
    """Current and new password fields expose standard autofill hints."""

    fake_streamlit = _render_password_change(monkeypatch)

    options_by_label = {
        args[0]: options
        for args, options in fake_streamlit.text_input_options
    }

    assert (
        options_by_label["Current password"]["autocomplete"]
        == "current-password"
    )
    assert (
        options_by_label["New password"]["autocomplete"]
        == "new-password"
    )
    assert (
        options_by_label["Confirm new password"]["autocomplete"]
        == "new-password"
    )


@pytest.mark.parametrize(
    ("show_passwords", "expected_type"),
    [
        (False, "password"),
        (True, "default"),
    ],
)
def test_password_change_visibility_control(
    monkeypatch,
    show_passwords,
    expected_type,
):
    """All three password fields follow the visibility control."""

    fake_streamlit = _render_password_change(
        monkeypatch,
        checkbox_value=show_passwords,
    )

    assert fake_streamlit.checkboxes == [
        (
            "Show passwords",
            {"key": "timanstat_show_password_change_passwords"},
        )
    ]

    assert all(
        options["type"] == expected_type
        for _, options in fake_streamlit.text_input_options
    )
