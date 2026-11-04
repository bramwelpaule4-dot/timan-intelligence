
"""Authentication and role-based access control for TimanStat."""

from __future__ import annotations

from typing import Any

import streamlit as st

from timan_intelligence.identity.service import (
    _verify_password as _verify_identity_password,
)


VALID_ROLES = {"developer", "admin", "user"}

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


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate an active account and establish its session."""

    username = username.strip().casefold()
    users = _get_users()

    account = users.get(username)

    if not account:
        return False

    try:
        account = dict(account)
    except (TypeError, ValueError):
        return False

    if not account.get("active", False):
        return False

    role = str(account.get("role", "")).strip().casefold()

    if role not in VALID_ROLES:
        return False

    stored_hash = str(account.get("password_hash", ""))

    if not _verify_password(password, stored_hash):
        return False

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
