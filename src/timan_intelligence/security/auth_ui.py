
"""Streamlit authentication interface for TimanStat."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlsplit

import streamlit as st

from timan_intelligence.identity.email_delivery import (
    EmailDeliveryError,
    MockEmailSender,
)
from timan_intelligence.identity.email_notifications import (
    resend_email_verification,
    send_email_verification,
)
from timan_intelligence.identity.service import register_user
from timan_intelligence.security.auth import render_login


logger = logging.getLogger(__name__)

RESEND_GENERIC_MESSAGE = (
    "If an active, unverified account exists for that email address, "
    "a verification link will be sent. If you recently requested one, "
    "please wait before trying again."
)


def _configuration_value(name: str) -> str:
    """Read a configuration value from Streamlit Secrets or environment."""

    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""

    if value in (None, ""):
        value = os.getenv(name, "")

    return str(value).strip()


def _application_base_url() -> str:
    """Read the trusted public application URL from configuration."""

    return _configuration_value("TIMAN_APP_BASE_URL")


def _development_email_sender(
    base_url: str,
) -> MockEmailSender | None:
    """Create a mock sender only for an authorised development host."""

    environment = _configuration_value(
        "TIMAN_ENVIRONMENT"
    ).lower()

    simulator_enabled = _configuration_value(
        "TIMAN_DEV_EMAIL_SIMULATOR"
    ).lower()

    if environment != "development" or simulator_enabled != "true":
        return None

    try:
        hostname = urlsplit(base_url).hostname
    except ValueError as exc:
        raise ValueError(
            "The development application URL is invalid."
        ) from exc

    if not hostname:
        raise ValueError(
            "The development application URL has no valid hostname."
        )

    allowed_hosts = {
        host.strip().lower()
        for host in _configuration_value(
            "TIMAN_DEV_ALLOWED_HOSTS"
        ).split(",")
        if host.strip()
    }

    allowed_hosts.update(
        {
            "localhost",
            "127.0.0.1",
            "::1",
        }
    )

    if hostname.lower() not in allowed_hosts:
        raise ValueError(
            "The development email simulator is not authorised "
            "for this application hostname."
        )

    return MockEmailSender()


def _extract_verification_url(body: str) -> str | None:
    """Extract the generated verification URL from a mock email."""

    for line in body.splitlines():
        candidate = line.strip()

        if "verify_email=" in candidate:
            return candidate

    return None


def _log_email_delivery_failure(exc: Exception) -> None:
    """Log safe diagnostics without exposing credentials or tokens."""

    cause = exc.__cause__ or exc.__context__

    smtp_code = getattr(cause, "smtp_code", None)
    error_number = getattr(cause, "errno", None)
    failure_stage = getattr(exc, "stage", None) or "unknown"

    logger.error(
        "TimanStat verification email delivery failed. "
        "error_type=%s cause_type=%s failure_stage=%s "
        "smtp_code=%s errno=%s",
        type(exc).__name__,
        type(cause).__name__ if cause else "None",
        failure_stage,
        smtp_code,
        error_number,
    )


def render_registration() -> None:
    """Render the public account registration form."""

    st.subheader("Create your TimanStat account")

    st.write(
        "Register an account to access TimanStat. "
        "You must verify your email address before signing in."
    )

    with st.form("timanstat_registration_form"):
        full_name = st.text_input(
            "Full name",
            max_chars=150,
        )

        username = st.text_input(
            "Username",
            max_chars=30,
            help=(
                "Use 3–30 lowercase letters, numbers, dots, "
                "underscores or hyphens."
            ),
        )

        email = st.text_input(
            "Email address",
            max_chars=254,
        )

        show_password = st.checkbox(
            "Show passwords",
            key="timanstat_show_registration_passwords",
        )
        password_input_type = "default" if show_password else "password"

        password = st.text_input(
            "Password",
            type=password_input_type,
            autocomplete="new-password",
        )

        confirm_password = st.text_input(
            "Confirm password",
            type=password_input_type,
            autocomplete="new-password",
        )

        submitted = st.form_submit_button(
            "Create account",
            use_container_width=True,
        )

    if not submitted:
        return

    if not all(
        value.strip()
        for value in (full_name, username, email)
    ):
        st.error("Complete all required fields.")
        return

    if password != confirm_password:
        st.error("The passwords do not match.")
        return

    if len(password) < 12:
        st.error("Your password must contain at least 12 characters.")
        return

    base_url = _application_base_url()

    if not base_url:
        st.error(
            "Account registration is temporarily unavailable because "
            "the application URL has not been configured. "
            "Please contact the platform administrator."
        )
        return

    try:
        user_id = register_user(
            username=username,
            email=email,
            full_name=full_name,
            password=password,
        )

    except ValueError as exc:
        st.error(str(exc))
        return

    except Exception as exc:
        logger.error(
            "TimanStat account registration failed. error_type=%s",
            type(exc).__name__,
        )
        st.error(
            "The account could not be created due to a system error. "
            "Please try again later."
        )
        return

    development_sender = None

    try:
        development_sender = _development_email_sender(
            base_url
        )

        if development_sender is not None:
            send_email_verification(
                user_id=user_id,
                base_url=base_url,
                sender=development_sender,
            )
        else:
            send_email_verification(
                user_id=user_id,
                base_url=base_url,
            )

    except (ValueError, EmailDeliveryError) as exc:
        _log_email_delivery_failure(exc)
        st.warning(
            "Your account has been created, but email delivery "
            "could not be completed. Please contact the platform "
            "administrator for assistance."
        )
        return

    except Exception as exc:
        _log_email_delivery_failure(exc)
        st.warning(
            "Your account has been created, but email delivery "
            "could not be completed. Please contact the platform "
            "administrator for assistance."
        )
        return

    if development_sender is not None:
        if not development_sender.sent_messages:
            logger.error(
                "Development email simulator produced no message."
            )
            st.warning(
                "Your account was created, but the development "
                "verification message could not be retrieved."
            )
            return

        verification_message = (
            development_sender.sent_messages[-1]
        )

        verification_url = _extract_verification_url(
            verification_message.body
        )

        if verification_url is None:
            logger.error(
                "Development verification URL was not found "
                "in the generated mock email."
            )
            st.warning(
                "Your account was created, but the development "
                "verification link could not be retrieved."
            )
            return

        st.success(
            "Your test account has been created successfully."
        )

        st.warning(
            "Development mode: this is a test verification link. "
            "It is not an email sent to your inbox."
        )

        st.markdown(
            f"[Open development verification link]({verification_url})"
        )

        st.caption(
            "This development-only link uses the same verification "
            "token service as normal email verification."
        )

        return

    st.success(
        "Your account has been created. Check your email for the "
        "verification link before signing in."
    )


def render_resend_verification() -> None:
    """Render the public email-verification resend form."""

    st.subheader("Resend verification email")

    st.write(
        "If you did not receive your verification email, "
        "or your previous link has expired, you can request another."
    )

    with st.form("timanstat_resend_verification_form"):
        email = st.text_input(
            "Registered email address",
            max_chars=254,
        )

        submitted = st.form_submit_button(
            "Resend verification link",
            use_container_width=True,
        )

    if not submitted:
        return

    if not email.strip():
        st.error("Enter your registered email address.")
        return

    base_url = _application_base_url()

    if not base_url:
        st.warning(
            "The verification service is temporarily unavailable. "
            "Please try again later."
        )
        return

    development_sender = None

    try:
        development_sender = _development_email_sender(
            base_url
        )

        if development_sender is not None:
            resend_email_verification(
                email=email,
                base_url=base_url,
                sender=development_sender,
            )
        else:
            resend_email_verification(
                email=email,
                base_url=base_url,
            )

    except (ValueError, EmailDeliveryError) as exc:
        _log_email_delivery_failure(exc)
        st.warning(
            "The verification request could not be completed. "
            "Please try again later."
        )
        return

    except Exception as exc:
        _log_email_delivery_failure(exc)
        st.warning(
            "The verification request could not be completed. "
            "Please try again later."
        )
        return

    # Always display the same public response, regardless of
    # whether an account exists, is verified, or is in cooldown.
    st.success(RESEND_GENERIC_MESSAGE)

    if development_sender is None:
        return

    if not development_sender.sent_messages:
        return

    verification_message = development_sender.sent_messages[-1]

    verification_url = _extract_verification_url(
        verification_message.body
    )

    if verification_url is None:
        logger.error(
            "Development resend verification URL was not found "
            "in the generated mock email."
        )
        return

    st.warning(
        "Development mode: this is a test verification link. "
        "It is not an email sent to your inbox."
    )

    st.markdown(
        f"[Open development verification link]({verification_url})"
    )

    st.caption(
        "This development-only link uses the same verification "
        "token service as normal email verification."
    )


AUTHENTICATION_VIEW_KEY = "timanstat_authentication_view"
AUTHENTICATION_VIEWS = {
    "sign_in",
    "password_recovery",
    "email_verification",
}


def _set_authentication_view(view: str) -> None:
    """Switch the public authentication interface to one focused view."""

    if view in AUTHENTICATION_VIEWS:
        st.session_state[AUTHENTICATION_VIEW_KEY] = view


def render_authentication() -> None:
    """Render a focused, ChatGPT-inspired sign-in and registration interface."""

    st.title("Welcome to TimanStat")

    st.caption(
        "Secure access to statistical analysis, research "
        "and data intelligence."
    )

    if "authenticated" in st.session_state:
        from timan_intelligence.security.auth import is_authenticated

        if is_authenticated():
            st.success(
                f"You are signed in as "
                f"{st.session_state.get('username', 'user')}."
            )
            return

    login_tab, register_tab = st.tabs(
        ["Sign in", "Create account"]
    )

    with login_tab:
        query_params = getattr(st, "query_params", None)
        reset_token = (
            query_params.get("reset_password")
            if query_params is not None
            else None
        )

        if isinstance(reset_token, list):
            reset_token = reset_token[0] if reset_token else None

        if isinstance(reset_token, str) and reset_token.strip():
            # Password-reset links must open the reset form directly,
            # without requiring the user to navigate through Forgot password.
            current_view = "password_recovery"
            st.session_state[AUTHENTICATION_VIEW_KEY] = current_view
        else:
            current_view = st.session_state.get(
                AUTHENTICATION_VIEW_KEY,
                "sign_in",
            )

        if current_view not in AUTHENTICATION_VIEWS:
            current_view = "sign_in"
            st.session_state[AUTHENTICATION_VIEW_KEY] = current_view

        if current_view == "sign_in":
            render_login()

            # Keep secondary actions out of the way during an MFA challenge.
            if st.session_state.get("pending_authentication") is not True:
                st.button(
                    "Forgot password?",
                    key="timanstat_open_password_recovery",
                    on_click=_set_authentication_view,
                    args=("password_recovery",),
                )
                st.button(
                    "Resend verification email",
                    key="timanstat_open_email_verification",
                    on_click=_set_authentication_view,
                    args=("email_verification",),
                )

        elif current_view == "password_recovery":
            st.subheader("Password recovery")

            # Import locally to avoid a circular module import:
            # password_reset_ui reuses helpers from this module.
            from timan_intelligence.security.password_reset_ui import (
                render_password_recovery,
            )

            render_password_recovery()

            st.button(
                "Back to sign in",
                key="timanstat_back_from_password_recovery",
                on_click=_set_authentication_view,
                args=("sign_in",),
            )

        elif current_view == "email_verification":
            st.subheader("Email verification")

            render_resend_verification()

            st.button(
                "Back to sign in",
                key="timanstat_back_from_email_verification",
                on_click=_set_authentication_view,
                args=("sign_in",),
            )

    with register_tab:
        render_registration()
