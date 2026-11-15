"""Restricted, development-only diagnostics for TimanStat authentication services.

This module deliberately exposes no account lookup, credentials, tokens, or
arbitrary email recipient controls. It is available only on the named
development deployment when explicitly enabled and protected by a secret key.
"""

from __future__ import annotations

import hmac
import logging
import os
import re
from urllib.parse import urlsplit

import streamlit as st

from timan_intelligence.database.connection import database_connection
from timan_intelligence.security.distributed_rate_limit import DatabaseRateLimiter
from timan_intelligence.identity.email_delivery import (
    EmailDeliverySettings,
    OutboundEmail,
    build_email_sender,
)

logger = logging.getLogger(__name__)

DIAGNOSTIC_SESSION_KEY = "timanstat_dev_diagnostics_unlocked"
DIAGNOSTIC_ATTEMPTS_KEY = "timanstat_dev_diagnostics_attempts"
ALLOWED_DEVELOPMENT_HOST = "timanstat-dev.streamlit.app"
MINIMUM_KEY_LENGTH = 32


def _configuration_value(name: str) -> str:
    """Read one non-secret setting from Streamlit Secrets or environment."""
    try:
        value = st.secrets.get(name, "")
    except Exception:
        value = ""
    if value in (None, ""):
        value = os.getenv(name, "")
    return str(value).strip()


def diagnostics_enabled() -> bool:
    """Return true only for the explicitly enabled TimanStat dev deployment."""
    if _configuration_value("TIMAN_ENVIRONMENT").lower() != "development":
        return False
    if _configuration_value("TIMAN_DEV_DIAGNOSTICS_ENABLED").lower() != "true":
        return False

    base_url = _configuration_value("TIMAN_APP_BASE_URL")
    try:
        hostname = urlsplit(base_url).hostname
    except ValueError:
        return False

    return hostname == ALLOWED_DEVELOPMENT_HOST


def _configured_access_key() -> str:
    return _configuration_value("TIMAN_DEV_DIAGNOSTICS_KEY")


def _check_database() -> tuple[bool, str]:
    """Perform read-only connectivity and identity-schema checks."""
    try:
        with database_connection() as connection:
            connection.execute("SELECT 1").fetchone()
            connection.execute("SELECT id FROM users LIMIT 0")
        return True, "Database reachable; identity table is present."
    except Exception as exc:
        logger.error(
            "TimanStat developer diagnostic failed. check=database "
            "error_type=%s",
            type(exc).__name__,
        )
        return False, f"Database check failed ({type(exc).__name__})."


def _check_rate_limiter() -> tuple[bool, str]:
    """Read the shared limiter using a synthetic key, never a real account."""
    try:
        limiter = DatabaseRateLimiter(
            scope="developer-diagnostics-health",
            max_failed_attempts=1,
        )
        limiter.is_locked("synthetic-health-check")
        return True, (
            "Rate-limit HMAC configuration and rate_limit_states storage are working."
        )
    except Exception as exc:
        logger.error(
            "TimanStat developer diagnostic failed. check=rate_limiter "
            "error_type=%s",
            type(exc).__name__,
        )
        return False, (
            f"Rate-limiter check failed ({type(exc).__name__}). "
            "Verify TIMANSTAT_RATE_LIMIT_HMAC_KEY and the rate-limit database table."
        )


def _check_email_configuration() -> tuple[bool, str, EmailDeliverySettings | None]:
    """Validate provider selection and required configuration without sending."""
    try:
        settings = EmailDeliverySettings.from_environment()
        if settings.provider not in {"smtp", "gmail_api"}:
            return False, "Email provider is mock or unsupported; real delivery is not active.", settings

        if not settings.sender_email:
            return False, "The configured sender address is missing.", settings

        if settings.provider == "gmail_api":
            required = (
                settings.gmail_client_id,
                settings.gmail_client_secret,
                settings.gmail_refresh_token,
            )
        else:
            required = (
                settings.smtp_host,
                settings.smtp_username,
                settings.smtp_password,
            )

        if not all(required):
            return False, "One or more required provider settings are missing.", settings

        # Constructing the sender validates provider-specific configuration
        # without refreshing credentials or submitting an email.
        build_email_sender(settings)
        return True, f"{settings.provider} provider configuration is present.", settings
    except Exception as exc:
        logger.error(
            "TimanStat developer diagnostic failed. check=email_configuration "
            "error_type=%s",
            type(exc).__name__,
        )
        return False, f"Email configuration check failed ({type(exc).__name__}).", None


def _send_controlled_test_email(settings: EmailDeliverySettings) -> tuple[bool, str]:
    """Send a test message only to the configured sender mailbox."""
    recipient = settings.sender_email
    if not recipient:
        return False, "No configured sender mailbox is available for the test."

    try:
        sender = build_email_sender(settings)
        sender.send(
            OutboundEmail(
                recipient=recipient,
                subject="TimanStat development email-delivery test",
                body=(
                    "This is a controlled email-delivery test initiated "
                    "from the TimanStat development diagnostics page. "
                    "No account password or recovery token is included."
                ),
            )
        )
        return True, (
            "The configured provider accepted the test message for the "
            "sender mailbox. Check that mailbox's Inbox and Spam folders."
        )
    except Exception as exc:
        stage = getattr(exc, "stage", None)
        safe_stage = (
            stage if isinstance(stage, str) and stage.isidentifier() else "unknown"
        )
        oauth_error = getattr(exc, "oauth_error", None)
        safe_oauth_error = (
            oauth_error
            if oauth_error in {
                "invalid_grant",
                "invalid_client",
                "unauthorized_client",
                "access_denied",
                "invalid_scope",
            }
            else "unclassified"
        )
        http_status = getattr(exc, "http_status", None)
        safe_http_status = (
            http_status
            if isinstance(http_status, int) and 100 <= http_status <= 599
            else "unknown"
        )
        api_reason = getattr(exc, "api_reason", None)
        safe_api_reason = (
            api_reason
            if isinstance(api_reason, str)
            and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", api_reason)
            else "unknown"
        )
        logger.error(
            "TimanStat developer diagnostic failed. check=email_delivery "
            "error_type=%s stage=%s oauth_error=%s http_status=%s api_reason=%s",
            type(exc).__name__,
            safe_stage,
            safe_oauth_error,
            safe_http_status,
            safe_api_reason,
        )
        return False, (
            f"Email delivery failed ({type(exc).__name__}; stage: {safe_stage}; "
            f"OAuth error: {safe_oauth_error}; HTTP status: {safe_http_status}; "
            f"API reason: {safe_api_reason}). "
            "No credentials, raw provider response, or message content were exposed."
        )


def render_development_diagnostics() -> None:
    """Render the locked diagnostics panel on the public authentication screen."""
    if not diagnostics_enabled():
        return

    access_key = _configured_access_key()
    if len(access_key) < MINIMUM_KEY_LENGTH:
        st.warning(
            "Developer diagnostics are disabled because the access key "
            "has not been configured securely."
        )
        return

    with st.expander("Developer diagnostics — development deployment"):
        st.caption(
            "Restricted troubleshooting for the development environment. "
            "This panel never looks up individual accounts or displays secrets."
        )

        if st.session_state.get(DIAGNOSTIC_SESSION_KEY) is not True:
            attempts = st.session_state.get(DIAGNOSTIC_ATTEMPTS_KEY, 0)
            if attempts >= 5:
                st.error(
                    "The diagnostics access limit has been reached for this session."
                )
                return

            with st.form("timanstat_developer_diagnostics_unlock"):
                supplied_key = st.text_input(
                    "Development diagnostics access key",
                    type="password",
                    max_chars=256,
                )
                submitted = st.form_submit_button("Unlock diagnostics")

            if submitted:
                if hmac.compare_digest(supplied_key, access_key):
                    st.session_state[DIAGNOSTIC_SESSION_KEY] = True
                    st.session_state.pop(DIAGNOSTIC_ATTEMPTS_KEY, None)
                    st.rerun()
                else:
                    st.session_state[DIAGNOSTIC_ATTEMPTS_KEY] = attempts + 1
                    st.error("The diagnostics access key is not valid.")
            return

        st.info(
            "The database check is read-only. The email test sends one "
            "message only to the configured sender mailbox, never to an "
            "address entered by a visitor."
        )

        if st.button("Run database and email-configuration checks"):
            database_ok, database_message = _check_database()
            rate_limit_ok, rate_limit_message = _check_rate_limiter()
            email_ok, email_message, settings = _check_email_configuration()

            st.session_state["timanstat_diagnostic_database_result"] = (
                database_ok,
                database_message,
            )
            st.session_state["timanstat_diagnostic_rate_limit_result"] = (
                rate_limit_ok,
                rate_limit_message,
            )
            st.session_state["timanstat_diagnostic_email_result"] = (
                email_ok,
                email_message,
            )
            st.session_state["timanstat_diagnostic_email_settings_ready"] = (
                settings is not None and email_ok
            )

        database_result = st.session_state.get(
            "timanstat_diagnostic_database_result"
        )
        rate_limit_result = st.session_state.get(
            "timanstat_diagnostic_rate_limit_result"
        )
        email_result = st.session_state.get(
            "timanstat_diagnostic_email_result"
        )

        if database_result:
            (st.success if database_result[0] else st.error)(
                f"Database: {database_result[1]}"
            )
        if rate_limit_result:
            (st.success if rate_limit_result[0] else st.error)(
                f"Rate limiter: {rate_limit_result[1]}"
            )
        if email_result:
            (st.success if email_result[0] else st.error)(
                f"Email configuration: {email_result[1]}"
            )

        if st.session_state.get("timanstat_diagnostic_email_settings_ready"):
            st.warning(
                "The next step sends a real test email to the configured "
                "sender mailbox. It does not send to a user account."
            )
            if st.button("Send one controlled test email"):
                _, _, settings = _check_email_configuration()
                if settings is None:
                    st.error("Email settings could not be loaded. Run the checks again.")
                else:
                    succeeded, message = _send_controlled_test_email(settings)
                    (st.success if succeeded else st.error)(message)

        if st.button("Lock diagnostics"):
            for key in (
                DIAGNOSTIC_SESSION_KEY,
                DIAGNOSTIC_ATTEMPTS_KEY,
                "timanstat_diagnostic_database_result",
                "timanstat_diagnostic_rate_limit_result",
                "timanstat_diagnostic_email_result",
                "timanstat_diagnostic_email_settings_ready",
            ):
                st.session_state.pop(key, None)
            st.rerun()
