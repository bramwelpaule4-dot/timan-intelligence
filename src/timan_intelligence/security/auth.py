"""Authentication and role-based access control for TimanStat."""

from __future__ import annotations

import math
import re
import time
from typing import Any, MutableMapping

import streamlit as st

from timan_intelligence.identity.service import (
    _verify_password as _verify_identity_password,
    authenticate_user as authenticate_identity_user,
)
from timan_intelligence.security.rate_limit import LoginRateLimiter
from timan_intelligence.security.recovery_codes import consume_recovery_code
from timan_intelligence.security.session import SessionManager
from timan_intelligence.security.totp_service import (
    TOTPServiceError,
    verify_totp_for_user,
)


VALID_ROLES = {"developer", "admin", "user"}

# Five failed password attempts within 15 minutes trigger a 15-minute lockout.
LOGIN_RATE_LIMITER = LoginRateLimiter()

# Every authenticated session must have a valid database-backed
# account identity and session version.
SESSION_MANAGER = SessionManager(require_versioned_sessions=True)

# A pending second-factor challenge expires after five minutes.
PENDING_TOTP_TIMEOUT_SECONDS = 5 * 60

PENDING_AUTHENTICATION_KEYS = (
    "pending_authentication",
    "pending_user_id",
    "pending_username",
    "pending_role",
    "pending_session_version",
    "pending_authenticated_at",
    "pending_expires_at",
)

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


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password using the shared secure password verifier."""

    return _verify_identity_password(password, stored_hash)


def _reject_login(identifier: str) -> bool:
    """Record a failed password attempt and reject authentication."""

    LOGIN_RATE_LIMITER.record_failure(identifier)
    return False


def _clear_pending_authentication(
    session_state: MutableMapping[str, Any],
) -> None:
    """Remove all pending second-factor authentication information."""

    for key in PENDING_AUTHENTICATION_KEYS:
        session_state.pop(key, None)


def _create_pending_authentication(
    session_state: MutableMapping[str, Any],
    user: dict[str, Any],
) -> None:
    """Create a short-lived pending authentication challenge."""

    user_id = user.get("id")
    username = user.get("username")
    role = user.get("role")

    if (
        not isinstance(user_id, str)
        or not user_id.strip()
        or not isinstance(username, str)
        or not username.strip()
        or not isinstance(role, str)
        or role not in VALID_ROLES
    ):
        raise ValueError("The authenticated account record is invalid.")

    try:
        session_version = SESSION_MANAGER.get_current_session_version(
            user_id.strip()
        )
    except Exception as exc:
        raise RuntimeError(
            "The account security state could not be verified."
        ) from exc

    if (
        isinstance(session_version, bool)
        or not isinstance(session_version, int)
        or session_version < 0
    ):
        raise ValueError(
            "The account security state is unavailable."
        )

    now = time.monotonic()

    session_state["pending_authentication"] = True
    session_state["pending_user_id"] = user_id.strip()
    session_state["pending_username"] = username.strip().casefold()
    session_state["pending_role"] = role
    session_state["pending_session_version"] = session_version
    session_state["pending_authenticated_at"] = now
    session_state["pending_expires_at"] = (
        now + PENDING_TOTP_TIMEOUT_SECONDS
    )


def is_totp_pending() -> bool:
    """Return whether a valid second-factor challenge is pending."""

    session_state = st.session_state

    if session_state.get("pending_authentication") is not True:
        _clear_pending_authentication(session_state)
        return False

    username = session_state.get("pending_username")
    user_id = session_state.get("pending_user_id")
    role = session_state.get("pending_role")
    pending_session_version = session_state.get("pending_session_version")
    authenticated_at = session_state.get("pending_authenticated_at")
    expires_at = session_state.get("pending_expires_at")

    timestamps_valid = all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        for value in (authenticated_at, expires_at)
    )

    if (
        not isinstance(user_id, str)
        or not user_id.strip()
        or not isinstance(username, str)
        or not username.strip()
        or role not in VALID_ROLES
        or isinstance(pending_session_version, bool)
        or not isinstance(pending_session_version, int)
        or pending_session_version < 0
        or not timestamps_valid
    ):
        _clear_pending_authentication(session_state)
        return False

    now = time.monotonic()

    if (
        authenticated_at > now
        or expires_at <= now
        or expires_at <= authenticated_at
    ):
        _clear_pending_authentication(session_state)
        return False

    # Bind the challenge to the account security state observed
    # immediately after password authentication. Any password change,
    # recovery-code regeneration, or other session revocation invalidates it.
    try:
        current_version = SESSION_MANAGER.get_current_session_version(user_id)
    except Exception:
        _clear_pending_authentication(session_state)
        return False

    if (
        isinstance(current_version, bool)
        or not isinstance(current_version, int)
        or current_version != pending_session_version
    ):
        _clear_pending_authentication(session_state)
        return False

    # A pending challenge must never coexist with a full session.
    SESSION_MANAGER.clear_session(session_state)

    return True


def authenticate_user(username: str, password: str) -> bool:
    """
    Authenticate using the database-backed identity service.

    Accounts without TOTP receive a full authenticated session after
    successful password verification.

    Accounts with TOTP receive only a pending second-factor challenge.
    They are not authenticated until the authenticator code is verified.

    Returns:
        True only when a full authenticated session is established.
        False for failed login attempts and pending TOTP challenges.
    """

    if not isinstance(username, str) or not isinstance(password, str):
        return False

    identifier = username.strip().casefold()

    if not identifier or not password:
        return False

    # Never allow an existing authenticated session to survive a new
    # password-login attempt.
    SESSION_MANAGER.clear_session(st.session_state)
    _clear_pending_authentication(st.session_state)

    if LOGIN_RATE_LIMITER.is_locked(identifier):
        return False

    try:
        user = authenticate_identity_user(identifier, password)
    except (TypeError, ValueError):
        return _reject_login(identifier)

    if user is None:
        return _reject_login(identifier)

    if not isinstance(user, dict):
        return _reject_login(identifier)

    role = str(user.get("role", "")).strip().casefold()

    if role not in VALID_ROLES:
        return _reject_login(identifier)

    actual_username = user.get("username")
    user_id = user.get("id")

    if (
        not isinstance(actual_username, str)
        or not actual_username.strip()
        or not isinstance(user_id, str)
        or not user_id.strip()
    ):
        return _reject_login(identifier)

    LOGIN_RATE_LIMITER.record_success(identifier)

    # Password authentication succeeded. TOTP-enabled accounts must
    # complete the second factor before receiving a full session.
    if bool(user.get("totp_enabled")):
        _create_pending_authentication(
            st.session_state,
            {
                "id": user_id,
                "username": actual_username,
                "role": role,
            },
        )
        return False

    SESSION_MANAGER.create_session(
        st.session_state,
        actual_username,
        role,
        user_id=user_id,
    )

    return True


def verify_pending_recovery_code(code: str) -> bool:
    """Verify and consume a recovery code for a pending login challenge."""

    if not isinstance(code, str) or not is_totp_pending():
        return False

    session_state = st.session_state
    user_id = session_state.get("pending_user_id")
    username = session_state.get("pending_username")
    role = session_state.get("pending_role")
    expected_session_version = session_state.get("pending_session_version")

    if (
        not isinstance(user_id, str)
        or not isinstance(username, str)
        or role not in VALID_ROLES
        or isinstance(expected_session_version, bool)
        or not isinstance(expected_session_version, int)
        or expected_session_version < 0
    ):
        _clear_pending_authentication(session_state)
        return False

    try:
        verified = consume_recovery_code(user_id, code)
    except Exception:
        return False

    if not verified or not is_totp_pending():
        return False

    _clear_pending_authentication(session_state)
    SESSION_MANAGER.create_session(
        session_state,
        username,
        role,
        user_id=user_id,
        expected_session_version=expected_session_version,
    )
    return True


def verify_pending_second_factor(code: str) -> bool:
    """Accept either an authenticator code or a formatted recovery code."""

    if not isinstance(code, str):
        return False

    compact = code.strip().replace("-", "").replace(" ", "")
    if re.fullmatch(r"[A-Fa-f0-9]{32}", compact):
        return verify_pending_recovery_code(code)

    return verify_pending_totp(code)


def verify_pending_totp(code: str) -> bool:
    """
    Verify the authenticator code for a pending login.

    A successful verification promotes the pending challenge to a
    fully authenticated session. Failed verification leaves the
    challenge pending, subject to the TOTP service's rate limiter.
    """

    if not isinstance(code, str):
        return False

    if not is_totp_pending():
        return False

    session_state = st.session_state

    user_id = session_state.get("pending_user_id")
    username = session_state.get("pending_username")
    role = session_state.get("pending_role")
    expected_session_version = session_state.get("pending_session_version")

    if (
        not isinstance(user_id, str)
        or not isinstance(username, str)
        or role not in VALID_ROLES
        or isinstance(expected_session_version, bool)
        or not isinstance(expected_session_version, int)
        or expected_session_version < 0
    ):
        _clear_pending_authentication(session_state)
        return False

    try:
        verified = verify_totp_for_user(user_id, code.strip())
    except TOTPServiceError:
        # Fail closed. Do not create a session when verification cannot
        # be completed reliably.
        return False

    if not verified:
        return False

    # Recheck the challenge before promoting it.
    if not is_totp_pending():
        return False

    # Remove the pending state before creating the full session.
    _clear_pending_authentication(session_state)

    SESSION_MANAGER.create_session(
        session_state,
        username,
        role,
        user_id=user_id,
        expected_session_version=expected_session_version,
    )

    return True


def is_authenticated() -> bool:
    """Validate the current full session and enforce session expiry."""

    if is_totp_pending():
        SESSION_MANAGER.clear_session(st.session_state)
        return False

    return SESSION_MANAGER.is_valid(st.session_state)


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

    role = st.session_state.get("role")

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
    """Clear full and pending authentication information."""

    SESSION_MANAGER.clear_session(st.session_state)
    _clear_pending_authentication(st.session_state)


def render_login() -> None:
    """Render the TimanStat password and TOTP login interfaces."""

    st.title("TimanStat Sign In")

    if is_authenticated():
        st.success("You are already signed in.")
        return

    if is_totp_pending():
        st.caption("Password accepted. Complete two-factor verification.")

        st.info(
            "Enter your six-digit authenticator code. You may use a recovery code if you cannot access your authenticator."
        )

        with st.form("timanstat_totp_login_form"):
            code = st.text_input(
                "Authenticator code",
                max_chars=40,
                placeholder="Authenticator code or recovery code",
            )
            submitted = st.form_submit_button("Verify and sign in")

        if submitted:
            if verify_pending_second_factor(code):
                st.success("Authentication successful.")
                st.rerun()
            else:
                st.error(
                    "The authenticator code could not be verified. "
                    "Check the code or sign in again if the challenge expired."
                )

        if st.button("Cancel sign in"):
            logout()
            st.rerun()

        return

    st.caption("Sign in using your authorised account.")

    with st.form("timanstat_login_form"):
        username = st.text_input("Username or email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if authenticate_user(username, password):
            st.success("Authentication successful.")
            st.rerun()
        elif is_totp_pending():
            st.rerun()
        else:
            st.error(
                "Invalid username, password or inactive account. "
                "You may also be temporarily locked out after repeated failures."
            )
