"""Streamlit OIDC provider integration for TimanStat."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import streamlit as st

from timan_intelligence.identity.federated import (
    authenticate_federated_identity,
)
from timan_intelligence.security.auth import (
    establish_federated_session,
    is_authenticated,
)


FEDERATED_LOGIN_ERROR_KEY = "timanstat_federated_login_error"
PROVIDER_LABELS = {
    "google": "Google",
    "microsoft": "Microsoft",
}


def configured_federated_providers() -> list[str]:
    """Return supported OIDC providers with complete named configuration."""

    try:
        auth_settings = st.secrets.get("auth", {})
    except Exception:
        return []

    if not isinstance(auth_settings, Mapping):
        return []

    configured = []
    for provider in PROVIDER_LABELS:
        settings = auth_settings.get(provider)
        if not isinstance(settings, Mapping):
            continue
        if all(
            isinstance(settings.get(key), str) and settings.get(key).strip()
            for key in ("client_id", "client_secret", "server_metadata_url")
        ):
            configured.append(provider)

    return configured


def _identity_claims() -> dict[str, Any] | None:
    """Read OIDC claims without exposing tokens or other credentials."""

    identity = getattr(st, "user", None)
    if identity is None or not getattr(identity, "is_logged_in", False):
        return None

    try:
        claims = identity.to_dict()
    except Exception:
        try:
            claims = dict(identity)
        except Exception:
            return None

    return claims if isinstance(claims, dict) else None


def process_federated_login_callback() -> bool:
    """Resolve a Streamlit OIDC callback into a protected TimanStat session."""

    if is_authenticated():
        return True

    if st.session_state.get("pending_authentication") is True:
        return False

    claims = _identity_claims()
    if claims is None:
        return False

    issuer = claims.get("iss")
    subject = claims.get("sub")
    if not isinstance(issuer, str) or not isinstance(subject, str):
        st.session_state[FEDERATED_LOGIN_ERROR_KEY] = (
            "The identity provider did not return a usable identity. "
            "Please use email sign-in or contact the administrator."
        )
        return False

    issuer = issuer.lower()
    if issuer in {"https://accounts.google.com", "accounts.google.com"}:
        provider = "google"
    elif "login.microsoftonline.com/" in issuer:
        provider = "microsoft"
    else:
        st.session_state[FEDERATED_LOGIN_ERROR_KEY] = (
            "This identity provider is not enabled for TimanStat."
        )
        return False

    email = claims.get("email")
    email_verified = claims.get("email_verified") is True
    full_name = claims.get("name") or claims.get("preferred_username") or ""

    if not isinstance(email, str) or not email.strip():
        st.session_state[FEDERATED_LOGIN_ERROR_KEY] = (
            "The identity provider did not supply an email address. "
            "Use email and password sign-in instead."
        )
        return False

    try:
        user = authenticate_federated_identity(
            provider=provider,
            subject=subject,
            email=email,
            email_verified=email_verified,
            full_name=full_name if isinstance(full_name, str) else "",
        )
    except Exception:
        st.session_state[FEDERATED_LOGIN_ERROR_KEY] = (
            "Federated sign-in could not be completed because the account "
            "service is temporarily unavailable. Please try again later."
        )
        return False

    if user is None:
        st.session_state[FEDERATED_LOGIN_ERROR_KEY] = (
            "TimanStat could not verify this account's email address or "
            "account status. Use a verified Google account, or sign in "
            "with your existing TimanStat credentials."
        )
        return False

    if not establish_federated_session(user):
        if st.session_state.get("pending_authentication") is True:
            st.session_state.pop(FEDERATED_LOGIN_ERROR_KEY, None)
            return False
        st.session_state[FEDERATED_LOGIN_ERROR_KEY] = (
            "Federated sign-in could not establish a secure TimanStat "
            "session. Please try again later."
        )
        return False

    st.session_state.pop(FEDERATED_LOGIN_ERROR_KEY, None)
    return True


def render_federated_login_buttons() -> None:
    """Render only providers that have actually been configured."""

    message = st.session_state.pop(FEDERATED_LOGIN_ERROR_KEY, None)
    if isinstance(message, str) and message:
        st.error(message)

    providers = configured_federated_providers()
    if not providers:
        return

    st.caption("Or continue with an identity provider")
    for provider in providers:
        label = PROVIDER_LABELS[provider]
        if st.button(
            f"Continue with {label}",
            key=f"timanstat_oidc_login_{provider}",
            use_container_width=True,
        ):
            st.login(provider)
