
"""Tests for TimanStat authentication and access-control security."""

import time
from types import SimpleNamespace

import pytest

from timan_intelligence.identity.service import _hash_password
from timan_intelligence.security import auth
from timan_intelligence.security.rate_limit import LoginRateLimiter
from timan_intelligence.security.session import (
    SESSION_EXPIRED_KEY,
    SessionManager,
)


VALID_PASSWORD = "SecureTestPassword123!"


@pytest.fixture
def mock_session(monkeypatch):
    """Provide isolated Streamlit session state and login services."""

    session_state = {}

    monkeypatch.setattr(
        auth,
        "st",
        SimpleNamespace(session_state=session_state),
    )

    monkeypatch.setattr(
        auth,
        "LOGIN_RATE_LIMITER",
        LoginRateLimiter(),
    )

    # Test accounts are artificial and do not exist in the database.
    # Their session version is therefore controlled by this test loader.
    manager = SessionManager(
        session_version_loader=lambda user_id: 0,
        require_versioned_sessions=False,
    )

    monkeypatch.setattr(auth, "SESSION_MANAGER", manager)

    return session_state


@pytest.fixture
def valid_account():
    """Return a valid simulated identity-service account."""

    return {
        "id": "test-user-id",
        "username": "testuser",
        "email": "testuser@example.com",
        "role": "user",
        "totp_enabled": False,
    }


@pytest.fixture
def mock_identity_authentication(monkeypatch, valid_account):
    """Mock the database identity-service authentication boundary."""

    calls = []

    def authenticate(identifier, password):
        calls.append((identifier, password))

        if identifier == "testuser" and password == VALID_PASSWORD:
            return dict(valid_account)

        return None

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        authenticate,
    )

    return SimpleNamespace(
        account=valid_account,
        calls=calls,
    )


@pytest.fixture
def controlled_session_manager(monkeypatch):
    """Provide a session manager with a controllable clock."""

    current_time = [1_000_000.0]

    manager = SessionManager(
        idle_timeout_seconds=1800,
        absolute_timeout_seconds=43200,
        clock=lambda: current_time[0],
        session_version_loader=lambda user_id: 0,
        require_versioned_sessions=False,
    )

    monkeypatch.setattr(auth, "SESSION_MANAGER", manager)

    return SimpleNamespace(
        manager=manager,
        clock=current_time,
    )


def test_password_verification_accepts_correct_password():
    """The shared password verifier should accept a correct password."""

    password_hash = _hash_password(VALID_PASSWORD)

    assert auth._verify_password(
        VALID_PASSWORD,
        password_hash,
    ) is True


def test_password_verification_rejects_incorrect_password():
    """The shared password verifier should reject an incorrect password."""

    password_hash = _hash_password(VALID_PASSWORD)

    assert auth._verify_password(
        "DifferentSecurePassword123!",
        password_hash,
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
    """Malformed or unsupported password hashes must fail safely."""

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
    mock_session,
    mock_identity_authentication,
    controlled_session_manager,
):
    """A valid database account should establish a managed session."""

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
    assert mock_session["user_id"] == "test-user-id"
    assert mock_session["session_version"] == 0

    assert auth.is_authenticated() is True


def test_authentication_normalises_username(
    mock_session,
    mock_identity_authentication,
    controlled_session_manager,
):
    """Login identifiers should be trimmed and case-normalised."""

    result = auth.authenticate_user(
        "  TESTUSER  ",
        VALID_PASSWORD,
    )

    assert result is True
    assert mock_session["username"] == "testuser"

    assert mock_identity_authentication.calls == [
        ("testuser", VALID_PASSWORD)
    ]


def test_login_fails_closed_and_marks_unavailable_when_rate_limiter_fails(
    mock_session,
    monkeypatch,
    mock_identity_authentication,
):
    """A missing security key must not look like an incorrect password."""

    monkeypatch.setattr(
        auth,
        "LOGIN_RATE_LIMITER",
        SimpleNamespace(
            is_locked=lambda identifier: (_ for _ in ()).throw(
                RuntimeError("rate limiter unavailable")
            )
        ),
    )

    result = auth.authenticate_user("testuser", VALID_PASSWORD)

    assert result is False
    assert mock_session.get("authenticated") is not True
    assert mock_session[auth.LOGIN_UNAVAILABLE_KEY] is True
    assert mock_identity_authentication.calls == []


def test_login_marks_identity_database_failure_as_unavailable(
    mock_session,
    monkeypatch,
):
    """An identity database outage must not be presented as bad credentials."""

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: (_ for _ in ()).throw(
            RuntimeError("database unavailable")
        ),
    )

    result = auth.authenticate_user("testuser", VALID_PASSWORD)

    assert result is False
    assert mock_session.get("authenticated") is not True
    assert mock_session[auth.LOGIN_UNAVAILABLE_KEY] is True


def test_authentication_rejects_unknown_user(
    monkeypatch,
    mock_session,
):
    """Unknown database accounts must not authenticate."""

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: None,
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
):
    """An inactive account rejected by the identity service cannot sign in."""

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: None,
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

    account = dict(valid_account)
    account["role"] = role

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
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
):
    """An incorrect password rejected by the identity service cannot sign in."""

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: None,
    )

    result = auth.authenticate_user(
        "testuser",
        "WrongPassword123!",
    )

    assert result is False
    assert mock_session == {}


@pytest.mark.parametrize(
    "malformed_account",
    [
        None,
        [],
        "invalid-account",
    ],
)
def test_authentication_rejects_malformed_account(
    monkeypatch,
    mock_session,
    malformed_account,
):
    """Malformed identity-service responses must be rejected."""

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: malformed_account,
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session == {}


def test_authentication_rejects_account_without_valid_user_id(
    monkeypatch,
    mock_session,
    valid_account,
):
    """An account without a valid database identifier must be rejected."""

    account = dict(valid_account)
    account["id"] = ""

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session == {}


def test_authentication_rejects_account_without_valid_username(
    monkeypatch,
    mock_session,
    valid_account,
):
    """An account without a valid username must be rejected."""

    account = dict(valid_account)
    account["username"] = ""

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session == {}


def test_totp_enabled_account_receives_pending_authentication(
    monkeypatch,
    mock_session,
    valid_account,
):
    """A TOTP-enabled account must not receive a full session after password login."""

    account = dict(valid_account)
    account["totp_enabled"] = True

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )

    result = auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    )

    assert result is False
    assert mock_session["pending_authentication"] is True
    assert mock_session["pending_user_id"] == "test-user-id"
    assert mock_session["pending_username"] == "testuser"
    assert mock_session["pending_role"] == "user"

    assert "authenticated" not in mock_session
    assert auth.is_authenticated() is False
    assert auth.has_permission("use_application") is False


def test_totp_disabled_account_receives_full_session(
    mock_session,
    mock_identity_authentication,
):
    """An account without TOTP should receive a full session after password login."""

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is True

    assert mock_session["authenticated"] is True
    assert "pending_authentication" not in mock_session


def test_pending_totp_authentication_can_be_promoted(
    monkeypatch,
    mock_session,
    valid_account,
):
    """A valid second factor should promote pending authentication."""

    account = dict(valid_account)
    account["totp_enabled"] = True

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )
    monkeypatch.setattr(
        auth,
        "verify_totp_for_user",
        lambda user_id, code: (
            user_id == "test-user-id" and code == "123456"
        ),
    )

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is False

    assert auth.is_authenticated() is False

    assert auth.verify_pending_totp("123456") is True

    assert mock_session["authenticated"] is True
    assert mock_session["username"] == "testuser"
    assert mock_session["role"] == "user"
    assert mock_session["user_id"] == "test-user-id"
    assert mock_session["session_version"] == 0
    assert "pending_authentication" not in mock_session

    assert auth.is_authenticated() is True


def test_pending_challenge_is_invalidated_when_account_version_changes(
    monkeypatch,
    mock_session,
    valid_account,
    controlled_session_manager,
):
    """A security-state change must invalidate an outstanding MFA challenge."""

    account = dict(valid_account)
    account["totp_enabled"] = True
    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )
    verification_calls = []
    monkeypatch.setattr(
        auth,
        "verify_totp_for_user",
        lambda user_id, code: verification_calls.append((user_id, code)) or True,
    )

    assert auth.authenticate_user("testuser", VALID_PASSWORD) is False
    assert mock_session["pending_session_version"] == 0

    controlled_session_manager.manager._session_version_loader = (
        lambda user_id: 1
    )

    assert auth.is_totp_pending() is False
    assert auth.verify_pending_totp("123456") is False
    assert verification_calls == []
    assert mock_session == {
        auth.PENDING_AUTHENTICATION_REVOKED_KEY: True
    }


def test_mfa_promotion_rejects_version_change_during_session_creation(
    monkeypatch,
    mock_session,
    valid_account,
    controlled_session_manager,
):
    """A version change at promotion must not establish a fresh session."""

    account = dict(valid_account)
    account["totp_enabled"] = True
    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )
    monkeypatch.setattr(
        auth,
        "verify_totp_for_user",
        lambda user_id, code: True,
    )

    manager = controlled_session_manager.manager
    original_create_session = manager.create_session

    def change_version_then_create(*args, **kwargs):
        manager._session_version_loader = lambda user_id: 1
        return original_create_session(*args, **kwargs)

    monkeypatch.setattr(manager, "create_session", change_version_then_create)

    assert auth.authenticate_user("testuser", VALID_PASSWORD) is False
    assert auth.verify_pending_totp("123456") is False
    assert "authenticated" not in mock_session
    assert "pending_authentication" not in mock_session


def test_invalid_totp_does_not_create_authenticated_session(
    monkeypatch,
    mock_session,
    valid_account,
):
    """An incorrect authenticator code must not establish a full session."""

    account = dict(valid_account)
    account["totp_enabled"] = True

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )
    monkeypatch.setattr(
        auth,
        "verify_totp_for_user",
        lambda user_id, code: False,
    )

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is False

    assert auth.verify_pending_totp("000000") is False

    assert mock_session["pending_authentication"] is True
    assert "authenticated" not in mock_session
    assert auth.is_authenticated() is False
    assert auth.has_permission("use_application") is False


def test_totp_service_error_does_not_create_session(
    monkeypatch,
    mock_session,
    valid_account,
):
    """A TOTP service failure must fail closed."""

    account = dict(valid_account)
    account["totp_enabled"] = True

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )

    def raise_totp_error(user_id, code):
        raise auth.TOTPServiceError("Verification unavailable.")

    monkeypatch.setattr(
        auth,
        "verify_totp_for_user",
        raise_totp_error,
    )

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is False

    assert auth.verify_pending_totp("123456") is False

    assert mock_session["pending_authentication"] is True
    assert "authenticated" not in mock_session


def test_expired_pending_authentication_is_rejected(
    monkeypatch,
    mock_session,
    valid_account,
):
    """An expired pending challenge must not be promoted."""

    account = dict(valid_account)
    account["totp_enabled"] = True

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )

    verification_calls = []

    monkeypatch.setattr(
        auth,
        "verify_totp_for_user",
        lambda user_id, code: verification_calls.append(
            (user_id, code)
        ) or True,
    )

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is False

    mock_session["pending_expires_at"] = time.monotonic() - 1

    assert auth.is_totp_pending() is False
    assert auth.verify_pending_totp("123456") is False

    assert verification_calls == []
    assert mock_session == {}



def test_pending_totp_challenge_is_revoked_when_account_version_changes(
    monkeypatch,
    mock_session,
    valid_account,
):
    """A changed account security version invalidates the pending MFA challenge."""

    account = dict(valid_account)
    account["totp_enabled"] = True
    versions = [0]
    manager = SessionManager(
        session_version_loader=lambda user_id: versions[0],
        require_versioned_sessions=True,
    )
    monkeypatch.setattr(auth, "SESSION_MANAGER", manager)
    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )

    assert auth.authenticate_user("testuser", VALID_PASSWORD) is False
    assert auth.is_totp_pending() is True

    versions[0] = 1

    assert auth.is_totp_pending() is False
    assert mock_session[auth.PENDING_AUTHENTICATION_REVOKED_KEY] is True
    assert "pending_authentication" not in mock_session
    assert "authenticated" not in mock_session


def test_logout_clears_full_and_pending_authentication(mock_session):
    """Logout must clear authentication while preserving unrelated state."""

    mock_session.update(
        {
            "authenticated": True,
            "username": "testuser",
            "role": "admin",
            "user_id": "test-user-id",
            "session_version": 0,
            "authenticated_at": time.monotonic(),
            "last_activity_at": time.monotonic(),
            "pending_authentication": True,
            "pending_user_id": "test-user-id",
            "pending_username": "testuser",
            "pending_role": "user",
            "pending_session_version": 0,
            "pending_authenticated_at": time.monotonic(),
            "pending_expires_at": time.monotonic() + 300,
            auth.PENDING_AUTHENTICATION_REVOKED_KEY: True,
            auth.LOGIN_IDENTIFIER_KEY: "private@example.com",
            auth.LOGIN_STEP_KEY: "password",
            "timanstat_show_login_password": True,
            "unrelated_setting": "preserve",
        }
    )

    auth.logout()

    for key in (
        "authenticated",
        "username",
        "role",
        "user_id",
        "session_version",
        "authenticated_at",
        "last_activity_at",
        "pending_authentication",
        "pending_user_id",
        "pending_username",
        "pending_role",
        "pending_session_version",
        "pending_authenticated_at",
        "pending_expires_at",
        auth.PENDING_AUTHENTICATION_REVOKED_KEY,
        auth.LOGIN_IDENTIFIER_KEY,
        auth.LOGIN_STEP_KEY,
        "timanstat_show_login_password",
    ):
        assert key not in mock_session

    assert mock_session["unrelated_setting"] == "preserve"


def test_unauthenticated_session_has_no_permissions(mock_session):
    """Unauthenticated sessions must not receive permissions."""

    assert auth.is_authenticated() is False
    assert auth.has_permission("use_application") is False
    assert auth.has_permission("manage_users") is False


def test_authenticated_user_receives_only_assigned_permissions(mock_session):
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
    assert mock_session == {SESSION_EXPIRED_KEY: "idle"}


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
    assert mock_session == {SESSION_EXPIRED_KEY: "idle"}


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
    assert mock_session == {SESSION_EXPIRED_KEY: "idle"}


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
    assert mock_session == {SESSION_EXPIRED_KEY: "idle"}


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

    for _ in range(28):
        controlled_session_manager.clock[0] += 1500
        assert auth.is_authenticated() is True

    assert (
        controlled_session_manager.clock[0]
        - mock_session["authenticated_at"]
        == 42000
    )

    controlled_session_manager.clock[0] += 1200

    assert auth.is_authenticated() is False
    assert mock_session == {SESSION_EXPIRED_KEY: "absolute"}


def test_pending_recovery_code_authentication_can_be_promoted(
    monkeypatch,
    mock_session,
    valid_account,
):
    """A valid single-use recovery code should complete second-factor login."""

    account = dict(valid_account)
    account["totp_enabled"] = True
    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )
    consumed = []
    monkeypatch.setattr(
        auth,
        "consume_recovery_code",
        lambda user_id, code: (
            consumed.append((user_id, code)) or code == "ABCD1234-EF001122-33445566-77889900"
        ),
    )

    assert auth.authenticate_user("testuser", VALID_PASSWORD) is False
    assert auth.verify_pending_recovery_code(
        "ABCD1234-EF001122-33445566-77889900"
    ) is True

    assert consumed == [
        ("test-user-id", "ABCD1234-EF001122-33445566-77889900")
    ]
    assert mock_session["authenticated"] is True
    assert mock_session["user_id"] == "test-user-id"
    assert "pending_authentication" not in mock_session


def test_invalid_recovery_code_does_not_create_session(
    monkeypatch,
    mock_session,
    valid_account,
):
    """An invalid recovery code must leave the second-factor challenge pending."""

    account = dict(valid_account)
    account["totp_enabled"] = True
    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )
    monkeypatch.setattr(
        auth,
        "consume_recovery_code",
        lambda user_id, code: False,
    )

    assert auth.authenticate_user("testuser", VALID_PASSWORD) is False
    assert auth.verify_pending_second_factor(
        "ABCD1234-EF001122-33445566-77889900"
    ) is False

    assert mock_session["pending_authentication"] is True
    assert "authenticated" not in mock_session

def test_expired_pending_authentication_sets_one_time_ui_notice(
    monkeypatch,
    mock_session,
    valid_account,
):
    """Expiry is recorded for one user-facing notice, without retaining MFA state."""

    account = dict(valid_account)
    account["totp_enabled"] = True
    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )

    assert auth.authenticate_user("testuser", VALID_PASSWORD) is False
    authenticated_at = mock_session["pending_authenticated_at"]
    mock_session["pending_expires_at"] = authenticated_at + 1
    monkeypatch.setattr(
        auth.time,
        "monotonic",
        lambda: authenticated_at + 2,
    )

    assert auth.is_totp_pending() is False
    assert mock_session[auth.PENDING_AUTHENTICATION_EXPIRED_KEY] is True
    assert "pending_authentication" not in mock_session



def test_federated_login_establishes_standard_user_session(
    mock_session,
    monkeypatch,
):
    """A federated identity receives only its database-assigned role."""

    monkeypatch.setattr(
        auth.LOGIN_RATE_LIMITER,
        "record_success",
        lambda identifier: None,
    )
    user = {
        "id": "federated-user-id",
        "username": "federated.user",
        "email": "federated@example.com",
        "role": "user",
        "is_active": True,
        "email_verified": True,
        "totp_enabled": False,
    }

    assert auth.establish_federated_session(user) is True
    assert mock_session["authenticated"] is True
    assert mock_session["user_id"] == "federated-user-id"
    assert mock_session["role"] == "user"
    assert auth.has_permission("use_application") is True
    assert auth.has_permission("manage_users") is False


def test_federated_login_requires_verified_active_account(mock_session):
    """Federated session creation rejects inactive or unverified accounts."""

    user = {
        "id": "federated-user-id",
        "username": "federated.user",
        "email": "federated@example.com",
        "role": "user",
        "is_active": False,
        "email_verified": True,
        "totp_enabled": False,
    }

    assert auth.establish_federated_session(user) is False
    assert mock_session == {}


def test_federated_login_preserves_timanstat_totp_requirement(
    mock_session,
    monkeypatch,
):
    """Federated sign-in must still complete TimanStat TOTP when enabled."""

    monkeypatch.setattr(
        auth.LOGIN_RATE_LIMITER,
        "record_success",
        lambda identifier: None,
    )
    user = {
        "id": "federated-user-id",
        "username": "federated.user",
        "email": "federated@example.com",
        "role": "user",
        "is_active": True,
        "email_verified": True,
        "totp_enabled": True,
    }

    assert auth.establish_federated_session(user) is False
    assert mock_session["pending_authentication"] is True
    assert mock_session["pending_user_id"] == "federated-user-id"
    assert "authenticated" not in mock_session



def _prepare_pending_totp_login(monkeypatch, mock_session, valid_account):
    account = dict(valid_account)
    account["totp_enabled"] = True
    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        lambda identifier, password: account,
    )
    assert auth.authenticate_user("testuser", VALID_PASSWORD) is False
    assert auth.is_totp_pending() is True


def test_pending_login_can_send_otp_to_verified_recovery_email(
    monkeypatch, mock_session, valid_account
):
    _prepare_pending_totp_login(monkeypatch, mock_session, valid_account)
    monkeypatch.setattr(
        auth, "get_contact_method_status",
        lambda user_id: {
            "recovery_email": "recovery@example.com",
            "recovery_email_verified": True,
            "phone_number_e164": None,
            "phone_verified": False,
        },
    )
    monkeypatch.setattr(
        auth, "create_otp_challenge",
        lambda user_id, purpose, channel: {
            "challenge_id": "challenge-123", "code": "123456", "channel": "email"
        },
    )
    delivered = []
    monkeypatch.setattr(
        auth, "send_email_otp",
        lambda recipient, code, purpose: delivered.append(
            (recipient, code, purpose)
        ),
    )
    monkeypatch.setattr(
        auth, "totp_attempt_limiter",
        SimpleNamespace(is_locked=lambda *args: False),
    )

    assert auth.send_pending_email_otp() is True
    assert delivered == [
        ("recovery@example.com", "123456", "login_mfa")
    ]
    assert mock_session["pending_email_otp_challenge_id"] == "challenge-123"
    assert auth.is_authenticated() is False


def test_pending_login_email_otp_requires_verified_recovery_email(
    monkeypatch, mock_session, valid_account
):
    _prepare_pending_totp_login(monkeypatch, mock_session, valid_account)
    monkeypatch.setattr(
        auth, "get_contact_method_status",
        lambda user_id: {
            "recovery_email": "recovery@example.com",
            "recovery_email_verified": False,
        },
    )
    monkeypatch.setattr(
        auth, "create_otp_challenge",
        lambda *args: pytest.fail(
            "An unverified recovery email must not receive a sign-in code."
        ),
    )
    monkeypatch.setattr(
        auth, "totp_attempt_limiter",
        SimpleNamespace(is_locked=lambda *args: False),
    )

    assert auth.send_pending_email_otp() is False
    assert "pending_email_otp_challenge_id" not in mock_session


def test_pending_email_otp_promotes_login_to_authenticated_session(
    monkeypatch, mock_session, valid_account
):
    _prepare_pending_totp_login(monkeypatch, mock_session, valid_account)
    mock_session["pending_email_otp_challenge_id"] = "challenge-123"
    monkeypatch.setattr(
        auth, "verify_otp_challenge",
        lambda challenge_id, user_id, purpose, code: (
            challenge_id == "challenge-123"
            and user_id == "test-user-id"
            and purpose == "login_mfa"
            and code == "123456"
        ),
    )
    limiter_calls = []
    monkeypatch.setattr(
        auth, "totp_attempt_limiter",
        SimpleNamespace(
            is_locked=lambda *args: False,
            record_success=lambda *args: limiter_calls.append(("success", args)),
            record_failure=lambda *args: limiter_calls.append(("failure", args)),
        ),
    )

    assert auth.verify_pending_email_otp("123456") is True
    assert mock_session["authenticated"] is True
    assert mock_session["user_id"] == "test-user-id"
    assert "pending_authentication" not in mock_session
    assert "pending_email_otp_challenge_id" not in mock_session
    assert limiter_calls == [("success", ("test-user-id", "email_otp"))]


def test_invalid_pending_email_otp_records_rate_limit_failure(
    monkeypatch, mock_session, valid_account
):
    _prepare_pending_totp_login(monkeypatch, mock_session, valid_account)
    mock_session["pending_email_otp_challenge_id"] = "challenge-123"
    monkeypatch.setattr(auth, "verify_otp_challenge", lambda *args: False)
    limiter_calls = []
    monkeypatch.setattr(
        auth, "totp_attempt_limiter",
        SimpleNamespace(
            is_locked=lambda *args: False,
            record_success=lambda *args: None,
            record_failure=lambda *args: limiter_calls.append(args),
        ),
    )

    assert auth.verify_pending_email_otp("000000") is False
    assert limiter_calls == [("test-user-id", "email_otp")]
    assert mock_session["pending_authentication"] is True
    assert "authenticated" not in mock_session
