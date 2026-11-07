"""Authenticated TOTP two-factor authentication management interface."""

from __future__ import annotations

import logging

import streamlit as st

from timan_intelligence.security.auth import is_authenticated, logout
from timan_intelligence.security.totp_service import (
    TOTPServiceError,
    begin_totp_enrolment,
    confirm_totp_enrolment,
    disable_totp_for_user,
    get_totp_status,
)


logger = logging.getLogger(__name__)

_PENDING_SECRET_KEY = "totp_management_pending_secret"


def _clear_pending_enrolment() -> None:
    """Remove temporary enrolment material from the Streamlit session."""

    st.session_state.pop(_PENDING_SECRET_KEY, None)


def render_totp_management() -> None:
    """Render secure authenticator-app enrolment and disablement controls."""

    st.subheader("Two-factor authentication")

    if not is_authenticated():
        st.warning("Sign in to manage two-factor authentication.")
        return

    user_id = st.session_state.get("user_id")

    if not isinstance(user_id, str) or not user_id.strip():
        logout()
        st.error("Your account session is invalid. Please sign in again.")
        return

    try:
        enabled = get_totp_status(user_id)
    except Exception as exc:
        logger.error(
            "TimanStat TOTP status lookup failed. error_type=%s",
            type(exc).__name__,
        )
        st.error(
            "Two-factor authentication settings are temporarily "
            "unavailable. Please try again later."
        )
        return

    if enabled:
        _clear_pending_enrolment()
        st.success("Authenticator-based two-factor authentication is enabled.")
        st.write(
            "Your account requires a fresh authenticator code after "
            "password verification when you sign in."
        )

        st.warning(
            "Disabling two-factor authentication requires your current "
            "password and a fresh code from your authenticator app. "
            "All active sessions will be signed out."
        )

        with st.form("timanstat_disable_totp_form"):
            current_password = st.text_input(
                "Current password",
                type="password",
                max_chars=1024,
            )
            code = st.text_input(
                "Authenticator code",
                max_chars=6,
                placeholder="000000",
            )
            submitted = st.form_submit_button(
                "Disable two-factor authentication",
                use_container_width=True,
            )

        if not submitted:
            return

        if not current_password or not code.strip():
            st.error("Enter your current password and authenticator code.")
            return

        try:
            disabled = disable_totp_for_user(
                user_id=user_id,
                current_password=current_password,
                code=code.strip(),
            )
        except Exception as exc:
            logger.error(
                "TimanStat TOTP disablement failed. error_type=%s",
                type(exc).__name__,
            )
            st.error(
                "Two-factor authentication could not be disabled due "
                "to a system error. Please try again later."
            )
            return

        if not disabled:
            st.error(
                "The password or authenticator code is incorrect, "
                "or the security setting could not be updated."
            )
            return

        _clear_pending_enrolment()
        logout()
        st.success("Two-factor authentication has been disabled.")
        st.info(
            "For your security, all sessions have been signed out. "
            "Sign in again using your password."
        )
        st.stop()
        return

    st.info("Authenticator-based two-factor authentication is not enabled.")
    st.write(
        "Use an authenticator application such as Google Authenticator, "
        "Microsoft Authenticator, 1Password or another TOTP-compatible app."
    )

    pending_secret = st.session_state.get(_PENDING_SECRET_KEY)

    if not isinstance(pending_secret, str) or not pending_secret:
        if st.button(
            "Set up authenticator app",
            use_container_width=True,
            key="timanstat_begin_totp_enrolment",
        ):
            try:
                enrolment = begin_totp_enrolment(user_id)
            except Exception as exc:
                logger.error(
                    "TimanStat TOTP enrolment start failed. error_type=%s",
                    type(exc).__name__,
                )
                st.error(
                    "Authenticator setup could not be started. "
                    "Please try again later."
                )
                return

            secret = enrolment.get("secret")
            if not isinstance(secret, str) or not secret:
                st.error(
                    "Authenticator setup could not be completed. "
                    "Please try again later."
                )
                return

            # Keep the plaintext secret only in this server-side session
            # while the user completes enrolment. It is never logged or
            # written to the database in plaintext.
            st.session_state[_PENDING_SECRET_KEY] = secret
            st.rerun()

        return

    st.markdown("**Step 1 — Add this account to your authenticator app**")
    st.write(
        "Choose the option to enter a setup key manually. Use the "
        "account name shown in your authenticator app and enter this key:"
    )
    st.code(pending_secret)
    st.caption(
        "Treat this setup key like a password. Do not share it or save "
        "it in an unprotected location. The pending setup expires after "
        "15 minutes."
    )

    st.markdown("**Step 2 — Verify the authenticator app**")
    st.write(
        "Enter the current six-digit code generated for this TimanStat "
        "account to complete setup."
    )

    with st.form("timanstat_confirm_totp_form"):
        confirmation_code = st.text_input(
            "Six-digit authenticator code",
            max_chars=6,
            placeholder="000000",
        )
        confirm_submitted = st.form_submit_button(
            "Verify and enable two-factor authentication",
            use_container_width=True,
        )

    if confirm_submitted:
        if not confirmation_code.strip():
            st.error("Enter the six-digit authenticator code.")
            return

        try:
            confirmed = confirm_totp_enrolment(
                user_id=user_id,
                code=confirmation_code.strip(),
            )
        except TOTPServiceError as exc:
            logger.error(
                "TimanStat TOTP enrolment confirmation failed. error_type=%s",
                type(exc).__name__,
            )
            st.error(
                "Authenticator setup could not be verified. "
                "Please start setup again."
            )
            return
        except Exception as exc:
            logger.error(
                "TimanStat TOTP enrolment confirmation failed. error_type=%s",
                type(exc).__name__,
            )
            st.error(
                "Authenticator setup could not be completed due to "
                "a system error. Please try again later."
            )
            return

        if not confirmed:
            st.error(
                "The code is invalid, expired or already used. "
                "Check your authenticator app and try the current code."
            )
            return

        _clear_pending_enrolment()
        logout()
        st.success("Two-factor authentication has been enabled.")
        st.info(
            "For your security, all active sessions have been signed out. "
            "Sign in again; your authenticator code will now be required."
        )
        st.stop()
        return

    if st.button(
        "Cancel authenticator setup",
        key="timanstat_cancel_totp_enrolment",
    ):
        _clear_pending_enrolment()
        st.info(
            "The setup key has been cleared from this browser session. "
            "Any pending server-side enrolment will expire automatically."
        )
        st.rerun()
