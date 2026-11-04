
"""Tests for TimanStat Streamlit authentication security."""

import time
from types import SimpleNamespace

import pytest

from timan_intelligence.identity.service import _hash_password
from timan_intelligence.security import auth
from timan_intelligence.security.session import SessionManager


VALID_PASSWORD = "SecureTestPassword123!"


@pytest.fixture
def mock_session(monkeypatch):
    """Provide isolated session state for authentication tests."""

    session_state = {}

    monkeypatch.setattr(
        auth,
        "st",
        SimpleNamespace(session_state=session_state),
    )

    return session_state


@pytest.fixture
def valid_account():
    """Return an active account with a valid password hash."""

    return {
        "active": True,
        "role": "user",
        "password_hash": _hash_password(VALID_PASSWORD),
    }


@pytest.fixture
def controlled_session_manager(monkeypatch):
    """Provide a session manager with a controllable clock."""

    current_time = [1_000_000.0]

    manager = SessionManager(
        idle_timeout_seconds=1800,
        absolute_timeout_seconds=43200,
        clock=lambda: current_time[0],
    )

    monkeypatch.setattr(auth, "SESSION_MANAGER", manager)

    return SimpleNamespace(
        manager=manager,
        clock=current_time,
    )


def test_password_verification_accepts_correct_password(valid_account):
    """The configured account password should verify successfully."""

    assert auth._verify_password(
        VALID_PASSWORD,
        valid_account["password_hash"],
    ) is True


def test_password_verification_rejects_incorrect_password(valid_account):
    """An incorrect password must be rejected."""

    assert auth._verify_password(
        "DifferentSecurePassword123!",
        valid_account["password_hash"],
    ) is False


@pytest.mark.parametrize(
    "stored_hash",
    [
        "",
        "invalid",
        "md5$invalid",
        "scrypt$invalid",
        "scrypt$16384$8$1$not-hex$not-hex",
    ],
)
def test_password_verification_rejects_malformed_hashes(stored_hash):
    """Malformed or unsupported stored hashes must fail safely."""

    assert auth._verify_password(
        VALID_PASSWORD,
        stored_hash,
    ) is False


def test_password_verification_rejects_modified_scrypt_parameters():
    """Stored parameters must not override application security settings."""

    password_hash = _hash_password(VALID_PASSWORD)
    parts = password_hash.split("$")
    parts[1] = "2"

    tampered_hash = "$".join(parts)

    assert auth._verify_password(
        VALID_PASSWORD,
        tampered_hash,
    ) is False


def test_authentication_accepts_valid_active_account(
    monkeypatch,
    mock_session,
    valid_account,
    controlled_session_manager,
):
    """A valid active account should establish a managed session."""

    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {"testuser": valid_account},
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is True
    assert mock_session["authenticated"] is True
    assert mock_session["username"] == "testuser"
    assert mock_session["role"] == "user"
    assert mock_session["authenticated_at"] == 1_000_000.0
    assert mock_session["last_activity_at"] == 1_000_000.0

    assert auth.is_authenticated() is True


def test_authentication_normalises_username(
    monkeypatch,
    mock_session,
    valid_account,
    controlled_session_manager,
):
    """Username matching should be case-insensitive and trim whitespace."""

    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {"testuser": valid_account},
    )

    result = auth.authenticate_user(
        "  TESTUSER  ",
        VALID_PASSWORD,
    )

    assert result is True
    assert mock_session["username"] == "testuser"


def test_authentication_rejects_unknown_user(
    monkeypatch,
    mock_session,
):
    """Unknown accounts must not authenticate."""

    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {},
    )

    result = auth.authenticate_user(
        "unknownuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session == {}


def test_authentication_rejects_inactive_account(
    monkeypatch,
    mock_session,
    valid_account,
):
    """Inactive accounts must not establish authenticated sessions."""

    valid_account["active"] = False

    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {"testuser": valid_account},
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session == {}


@pytest.mark.parametrize(
    "role",
    [
        "",
        "superuser",
        "owner",
        "invalid",
    ],
)
def test_authentication_rejects_unsupported_roles(
    monkeypatch,
    mock_session,
    valid_account,
    role,
):
    """Accounts with unsupported roles must not authenticate."""

    valid_account["role"] = role

    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {"testuser": valid_account},
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session == {}


def test_authentication_rejects_incorrect_password(
    monkeypatch,
    mock_session,
    valid_account,
):
    """An incorrect password must not establish a session."""

    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {"testuser": valid_account},
    )

    result = auth.authenticate_user(
        "testuser",
        "WrongPassword123!",
    )

    assert result is False
    assert mock_session == {}


def test_authentication_rejects_malformed_account(
    monkeypatch,
    mock_session,
):
    """An account that cannot be converted to a mapping must be rejected."""

    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {"testuser": None},
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session == {}


def test_logout_clears_authentication_session(mock_session):
    """Logout should remove all authentication session fields."""

    mock_session.update(
        {
            "authenticated": True,
            "username": "testuser",
            "role": "admin",
            "authenticated_at": time.monotonic(),
            "last_activity_at": time.monotonic(),
            "unrelated_setting": "preserve",
        }
    )

    auth.logout()

    assert "authenticated" not in mock_session
    assert "username" not in mock_session
    assert "role" not in mock_session
    assert "authenticated_at" not in mock_session
    assert "last_activity_at" not in mock_session
    assert mock_session["unrelated_setting"] == "preserve"


def test_unauthenticated_session_has_no_permissions(mock_session):
    """Unauthenticated sessions must not receive permissions."""

    assert auth.is_authenticated() is False
    assert auth.has_permission("use_application") is False
    assert auth.has_permission("manage_users") is False


def test_authenticated_user_receives_only_assigned_permissions(
    mock_session,
):
    """A normal user should receive only explicitly assigned permissions."""

    auth.SESSION_MANAGER.create_session(
        mock_session,
        "testuser",
        "user",
    )

    assert auth.has_permission("use_application") is True
    assert auth.has_permission("manage_own_data") is True
    assert auth.has_permission("manage_users") is False
    assert auth.has_permission("view_audit_logs") is False


def test_unknown_session_role_receives_no_permissions(mock_session):
    """An unrecognised session role must not receive permissions."""

    mock_session.update(
        {
            "authenticated": True,
            "username": "testuser",
            "role": "superuser",
            "authenticated_at": time.monotonic(),
            "last_activity_at": time.monotonic(),
        }
    )

    assert auth.has_permission("use_application") is False
    assert auth.has_permission("manage_users") is False


def test_is_authenticated_rejects_and_clears_expired_session(
    mock_session,
    controlled_session_manager,
):
    """The authentication interface must enforce session expiry."""

    auth.SESSION_MANAGER.create_session(
        mock_session,
        "testuser",
        "user",
    )

    controlled_session_manager.clock[0] += 1800

    assert auth.is_authenticated() is False
    assert mock_session == {}


def test_permission_check_rejects_expired_session(
    mock_session,
    controlled_session_manager,
):
    """Expired sessions must not retain application permissions."""

    auth.SESSION_MANAGER.create_session(
        mock_session,
        "testuser",
        "admin",
    )

    controlled_session_manager.clock[0] += 1800

    assert auth.has_permission("manage_users") is False
    assert mock_session == {}


def test_current_username_rejects_expired_session(
    mock_session,
    controlled_session_manager,
):
    """An expired session must not expose the current username."""

    auth.SESSION_MANAGER.create_session(
        mock_session,
        "testuser",
        "user",
    )

    controlled_session_manager.clock[0] += 1800

    assert auth.current_username() is None
    assert mock_session == {}


def test_current_role_rejects_expired_session(
    mock_session,
    controlled_session_manager,
):
    """An expired session must not expose the current role."""

    auth.SESSION_MANAGER.create_session(
        mock_session,
        "testuser",
        "admin",
    )

    controlled_session_manager.clock[0] += 1800

    assert auth.current_role() is None
    assert mock_session == {}


def test_valid_session_activity_refreshes_idle_timeout(
    mock_session,
    controlled_session_manager,
):
    """Authenticated activity should refresh the idle timeout."""

    auth.SESSION_MANAGER.create_session(
        mock_session,
        "testuser",
        "user",
    )

    controlled_session_manager.clock[0] += 600

    assert auth.is_authenticated() is True
    assert mock_session["last_activity_at"] == 1_000_600.0


def test_absolute_timeout_is_enforced_through_authentication(
    mock_session,
    controlled_session_manager,
):
    """Repeated activity must not extend the absolute session lifetime."""

    auth.SESSION_MANAGER.create_session(
        mock_session,
        "testuser",
        "user",
    )

    # Refresh activity every 25 minutes, within the 30-minute idle timeout.
    for _ in range(28):
        controlled_session_manager.clock[0] += 1500

        assert auth.is_authenticated() is True

    # Total elapsed time is now 11 hours and 40 minutes.
    assert (
        controlled_session_manager.clock[0]
        - mock_session["authenticated_at"]
        == 42000
    )

    # Advance to exactly 12 hours after initial authentication.
    controlled_session_manager.clock[0] += 1200

    assert auth.is_authenticated() is False
    assert mock_session == {}
