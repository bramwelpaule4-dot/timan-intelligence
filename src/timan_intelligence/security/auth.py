"""Authentication and role-based access control for TimanStat."""

from __future__ import annotations

from typing import Any

import streamlit as st

from timan_intelligence.identity.service import (
    _verify_password as _verify_identity_password,
)
from timan_intelligence.security.rate_limit import LoginRateLimiter


VALID_ROLES = {"developer", "admin", "user"}

# Five failed attempts within 15 minutes trigger a 15-minute lockout.
LOGIN_RATE_LIMITER = LoginRateLimiter()

# Permissions are deliberately explicit.
ROLE_PERMISSIONS = {
    "user": {
        "use_application",
        "manage_own_data",
    },
    "developer": {
        "use_application",
        "manage_own_data",
        "view_project_status",
        "access_developer_tools",
    },
    "admin": {
        "use_application",
        "manage_own_data",
        "view_project_status",
        "manage_users",
        "view_system_monitoring",
        "manage_governance",
        "view_audit_logs",
    },
}


def _get_auth_config() -> dict[str, Any]:
    """Read authentication configuration from Streamlit secrets."""

    try:
        config = st.secrets.get("auth", {})
        return dict(config)
    except Exception:
        return {}


def _get_users() -> dict[str, Any]:
    """Return configured user accounts."""

    config = _get_auth_config()
    users = config.get("users", {})

    try:
        return dict(users)
    except (TypeError, ValueError):
        return {}


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a configured account password using the shared secure verifier."""

    return _verify_identity_password(password, stored_hash)


def _reject_login(username: str) -> bool:
    """Record a failed login attempt and reject authentication."""

    LOGIN_RATE_LIMITER.record_failure(username)
    return False


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate an active account with login rate limiting."""

    if not isinstance(username, str):
        return False

    username = username.strip().casefold()

    if not username:
        return False

    # Reject locked identifiers before performing password verification.
    if LOGIN_RATE_LIMITER.is_locked(username):
        return False

    users = _get_users()
    account = users.get(username)

    if not account:
        return _reject_login(username)

    try:
        account = dict(account)
    except (TypeError, ValueError):
        return _reject_login(username)

    if not account.get("active", False):
        return _reject_login(username)

    role = str(account.get("role", "")).strip().casefold()

    if role not in VALID_ROLES:
        return _reject_login(username)

    stored_hash = str(account.get("password_hash", ""))

    if not _verify_password(password, stored_hash):
        return _reject_login(username)

    # Successful authentication clears the previous failure history.
    LOGIN_RATE_LIMITER.record_success(username)

    st.session_state["authenticated"] = True
    st.session_state["username"] = username
    st.session_state["role"] = role

    return True


def is_authenticated() -> bool:
    """Check whether the current session is authenticated."""

    return bool(st.session_state.get("authenticated", False))


def current_username() -> str | None:
    """Return the authenticated username."""

    if not is_authenticated():
        return None

    return st.session_state.get("username")


def current_role() -> str | None:
    """Return the authenticated user's role."""

    if not is_authenticated():
        return None

    return st.session_state.get("role")


def has_permission(permission: str) -> bool:
    """Check whether the current account has a specific permission."""

    if not is_authenticated():
        return False

    role = current_role()

    if role not in ROLE_PERMISSIONS:
        return False

    return permission in ROLE_PERMISSIONS[role]


def require_permission(permission: str) -> bool:
    """Display an access-denied message when permission is missing."""

    if has_permission(permission):
        return True

    st.error("Access denied. You do not have permission to view this page.")
    return False


def logout() -> None:
    """Clear authentication information from the current session."""

    for key in ("authenticated", "username", "role"):
        st.session_state.pop(key, None)


def render_login() -> None:
    """Render the TimanStat login interface."""

    st.title("TimanStat Sign In")
    st.caption("Sign in using your authorised account.")

    with st.form("timanstat_login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if authenticate_user(username, password):
            st.success("Authentication successful.")
            st.rerun()
        else:
            st.error("Invalid username, password or inactive account.")
