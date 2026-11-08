"""Authenticated password-change interface for TimanStat."""

from __future__ import annotations

import logging

import streamlit as st

from timan_intelligence.identity.service import (
    PASSWORD_CHANGE_RATE_LIMITER,
    change_password,
)
from timan_intelligence.security.auth import (
    is_authenticated,
    logout,
)


logger = logging.getLogger(__name__)


def render_password_change() -> None:
    """Render the authenticated user's password-change form."""

    st.subheader("Change password")

    if not is_authenticated():
        st.warning("Sign in to manage your account password.")
        return

    user_id = st.session_state.get("user_id")

    if not isinstance(user_id, str) or not user_id.strip():
        logout()
        st.error(
            "Your account session is invalid. "
            "Please sign in again."
        )
        return

    try:
        password_change_locked = PASSWORD_CHANGE_RATE_LIMITER.is_locked(user_id)
    except Exception as exc:
        logger.error(
            "TimanStat password-change rate-limit check failed. error_type=%s",
            type(exc).__name__,
        )
        st.error(
            "Password changes are temporarily unavailable. "
            "Please try again later."
        )
        return

    if password_change_locked:
        st.error(
            "Too many unsuccessful password-change attempts. "
            "For your security, this action is temporarily paused."
        )
        st.info("Please wait 15 minutes before trying again.")
        return

    st.write(
        "Change your account password. "
        "You will need to sign in again after a successful change."
    )

    st.caption(
        "Your new password must contain at least 12 characters."
    )

    with st.form("timanstat_change_password_form"):
        show_passwords = st.checkbox(
            "Show passwords",
            key="timanstat_show_password_change_passwords",
        )
        password_input_type = "default" if show_passwords else "password"

        current_password = st.text_input(
            "Current password",
            type=password_input_type,
            max_chars=1024,
            autocomplete="current-password",
        )

        new_password = st.text_input(
            "New password",
            type=password_input_type,
            max_chars=1024,
            autocomplete="new-password",
        )

        confirm_password = st.text_input(
            "Confirm new password",
            type=password_input_type,
            max_chars=1024,
            autocomplete="new-password",
        )

        submitted = st.form_submit_button(
            "Change password",
            use_container_width=True,
        )

    if not submitted:
        return

    if not current_password or not new_password or not confirm_password:
        st.error("Complete all three password fields.")
        return

    if new_password != confirm_password:
        st.error("The new passwords do not match.")
        return

    if len(new_password) < 12:
        st.error(
            "Your new password must contain at least 12 characters."
        )
        return

    try:
        successful = change_password(
            user_id=user_id,
            current_password=current_password,
            new_password=new_password,
        )

    except ValueError as exc:
        st.error(str(exc))
        return

    except Exception as exc:
        logger.error(
            "TimanStat password change failed. error_type=%s",
            type(exc).__name__,
        )
        st.error(
            "Your password could not be changed due to a system "
            "error. Please try again later."
        )
        return

    if not successful:
        try:
            password_change_locked = PASSWORD_CHANGE_RATE_LIMITER.is_locked(
                user_id
            )
        except Exception:
            password_change_locked = False

        if password_change_locked:
            st.error(
                "Too many unsuccessful password-change attempts. "
                "For your security, this action is temporarily paused."
            )
            st.info("Please wait 15 minutes before trying again.")
        else:
            st.error(
                "The current password is incorrect, or the account "
                "could not be updated. Check your current password "
                "and try again."
            )
        return

    # The backend has incremented session_version. Explicitly clear
    # this browser session as well, requiring a fresh sign-in.
    logout()

    st.success("Your password has been changed successfully.")
    st.info(
        "For your security, you have been signed out. "
        "Sign in again using your new password."
    )

    # Prevent the remainder of the authenticated application
    # from rendering during this run.
    st.stop()
