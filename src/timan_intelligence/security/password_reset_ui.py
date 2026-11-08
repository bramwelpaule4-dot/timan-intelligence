"""Streamlit password-recovery interface for TimanStat."""

from __future__ import annotations

import logging

from urllib.parse import urlsplit

import streamlit as st

from timan_intelligence.identity.email_delivery import (
    EmailDeliveryError,
    MockEmailSender,
)
from timan_intelligence.identity.email_notifications import (
    request_password_reset,
)
from timan_intelligence.identity.password_reset import (
    reset_password_with_token,
)

from timan_intelligence.security.auth_ui import (
    _application_base_url,
    _development_email_sender,
    _log_email_delivery_failure,
)


logger = logging.getLogger(__name__)

PASSWORD_RESET_GENERIC_MESSAGE = (
    "If an active account exists for that email address, "
    "a password-reset link will be sent. Check your inbox "
    "and follow the instructions. If you recently requested "
    "a link, please wait before trying again."
)


def _extract_password_reset_url(body: str) -> str | None:
    """Extract a password-reset URL from a mock email."""

    for line in body.splitlines():
        candidate = line.strip()

        if "reset_password=" in candidate:
            return candidate

    return None


def _show_development_reset_link(
    sender: MockEmailSender | None,
) -> None:
    """Display a reset link only in the authorised simulator."""

    if sender is None or not sender.sent_messages:
        return

    message = sender.sent_messages[-1]

    reset_url = _extract_password_reset_url(message.body)

    if reset_url is None:
        logger.error(
            "Development password-reset URL was not found "
            "in the generated mock email."
        )
        return

    st.warning(
        "Development mode: this is a test password-reset link. "
        "It is not an email sent to your inbox."
    )

    st.markdown(
        f"[Open development password-reset link]({reset_url})"
    )

    st.caption(
        "This development-only link uses the same password-reset "
        "token service as normal email delivery."
    )


def _clear_password_reset_query_param() -> None:
    """Remove the reset token from the browser URL."""

    query_params = getattr(st, "query_params", None)

    if query_params is None:
        return

    try:
        if "reset_password" in query_params:
            del query_params["reset_password"]

    except Exception as exc:
        # Do not log the token or the complete URL.
        logger.warning(
            "Could not clear password-reset query parameter. "
            "error_type=%s",
            type(exc).__name__,
        )


def render_password_reset_request() -> None:
    """Render the public password-reset request form."""

    st.subheader("Forgot your password?")

    st.write(
        "Enter the email address associated with your TimanStat "
        "account. If the account is eligible, a reset link will "
        "be sent."
    )

    with st.form("timanstat_password_reset_request_form"):
        email = st.text_input(
            "Registered email address",
            max_chars=254,
            autocomplete="email",
        )

        submitted = st.form_submit_button(
            "Send password-reset link",
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
            "The password-recovery service is temporarily "
            "unavailable. Please try again later."
        )
        return

    development_sender = None

    try:
        development_sender = _development_email_sender(base_url)

        request_password_reset(
            email=email,
            base_url=base_url,
            sender=development_sender,
        )

    except (ValueError, EmailDeliveryError) as exc:
        _log_email_delivery_failure(exc)

        st.warning(
            "The password-reset request could not be completed. "
            "Please try again later."
        )
        return

    except Exception as exc:
        _log_email_delivery_failure(exc)

        st.warning(
            "The password-reset request could not be completed. "
            "Please try again later."
        )
        return

    # Do not reveal whether the email address belongs to an account.
    st.success(PASSWORD_RESET_GENERIC_MESSAGE)

    # Expose a link only through the authorised development simulator.
    _show_development_reset_link(development_sender)


def render_password_reset_form(token: str) -> None:
    """Render the form for choosing a new password."""

    st.subheader("Choose a new password")

    st.write(
        "Enter your new password below. Passwords must contain "
        "at least 12 characters."
    )

    with st.form("timanstat_password_reset_completion_form"):
        show_passwords = st.checkbox(
            "Show passwords",
            key="timanstat_show_password_reset_passwords",
        )
        password_input_type = "default" if show_passwords else "password"

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
            "Reset password",
            use_container_width=True,
        )

    if not submitted:
        return

    if not new_password or not confirm_password:
        st.error("Complete both password fields.")
        return

    if new_password != confirm_password:
        st.error("The passwords do not match.")
        return

    if len(new_password) < 12:
        st.error(
            "Your password must contain at least 12 characters."
        )
        return

    try:
        successful = reset_password_with_token(
            token=token,
            new_password=new_password,
        )

    except ValueError as exc:
        st.error(str(exc))
        return

    except Exception as exc:
        logger.error(
            "TimanStat password reset failed. error_type=%s",
            type(exc).__name__,
        )

        st.error(
            "The password could not be changed due to a system "
            "error. Please try again later."
        )
        return

    if not successful:
        st.error(
            "This password-reset link is invalid, expired, or "
            "has already been used. Request a new link and try again."
        )
        return

    # The reset succeeded. Remove the sensitive token from the URL.
    _clear_password_reset_query_param()

    st.success(
        "Your password has been changed successfully. "
        "You can now return to the sign-in page."
    )


def render_password_recovery() -> None:
    """Render the appropriate password-recovery screen."""

    query_params = getattr(st, "query_params", None)

    if query_params is None:
        render_password_reset_request()
        return

    token = query_params.get("reset_password")

    if isinstance(token, list):
        token = token[0] if token else None

    if not isinstance(token, str) or not token.strip():
        render_password_reset_request()
        return

    # Validate the configured URL before processing a token.
    # The token itself is validated by the reset service.
    base_url = _application_base_url()

    if not base_url:
        st.warning(
            "The password-recovery service is temporarily "
            "unavailable. Please try again later."
        )
        return

    try:
        parsed = urlsplit(base_url)

        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            raise ValueError("Invalid application URL.")

    except ValueError:
        st.warning(
            "The password-recovery service is temporarily "
            "unavailable. Please try again later."
        )
        return

    render_password_reset_form(token.strip())
