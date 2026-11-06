
"""Streamlit authentication interface for TimanStat."""

from __future__ import annotations

import logging
import os

import streamlit as st

from timan_intelligence.identity.email_delivery import (
    EmailDeliveryError,
)
from timan_intelligence.identity.email_notifications import (
    send_email_verification,
)
from timan_intelligence.identity.service import register_user
from timan_intelligence.security.auth import render_login


logger = logging.getLogger(__name__)


def _application_base_url() -> str:
    """Read the trusted public application URL from configuration."""

    try:
        configured_url = st.secrets.get("TIMAN_APP_BASE_URL", "")
    except Exception:
        configured_url = ""

    return (
        configured_url
        or os.getenv("TIMAN_APP_BASE_URL", "").strip()
    )


def _log_email_delivery_failure(exc: Exception) -> None:
    """Log safe diagnostic details without exposing credentials or tokens."""

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

        password = st.text_input(
            "Password",
            type="password",
        )

        confirm_password = st.text_input(
            "Confirm password",
            type="password",
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

    try:
        send_email_verification(
            user_id=user_id,
            base_url=base_url,
        )

    except (ValueError, EmailDeliveryError) as exc:
        _log_email_delivery_failure(exc)
        st.warning(
            "Your account has been created, but the verification "
            "email could not be sent. Please contact the platform "
            "administrator for assistance."
        )
        return

    except Exception as exc:
        _log_email_delivery_failure(exc)
        st.warning(
            "Your account has been created, but email delivery "
            "could not be completed. Please contact the platform "
            "administrator."
        )
        return

    st.success(
        "Your account has been created. Check your email for the "
        "verification link before signing in."
    )


def render_authentication() -> None:
    """Render the TimanStat sign-in and registration interface."""

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
        render_login()

    with register_tab:
        render_registration()
