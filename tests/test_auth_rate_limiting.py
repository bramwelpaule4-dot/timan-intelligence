
"""Integration tests for TimanStat authentication rate limiting."""

from types import SimpleNamespace

import pytest

from timan_intelligence.security import auth
from timan_intelligence.security.rate_limit import LoginRateLimiter
from timan_intelligence.security.session import SessionManager


VALID_PASSWORD = "SecureTestPassword123!"


@pytest.fixture
def rate_limit_environment(monkeypatch):
    """Provide isolated authentication and a controllable clock."""

    current_time = [1_000.0]
    session_state = {}

    limiter = LoginRateLimiter(
        max_failed_attempts=5,
        window_seconds=900,
        lockout_seconds=900,
        clock=lambda: current_time[0],
    )

    account = {
        "id": "test-user-id",
        "username": "testuser",
        "email": "testuser@example.com",
        "role": "user",
        "totp_enabled": False,
    }

    def authenticate_identity_user(identifier, password):
        """Simulate the database identity-service boundary."""

        if (
            identifier == "testuser"
            and password == VALID_PASSWORD
        ):
            return dict(account)

        return None

    monkeypatch.setattr(
        auth,
        "st",
        SimpleNamespace(session_state=session_state),
    )

    monkeypatch.setattr(
        auth,
        "LOGIN_RATE_LIMITER",
        limiter,
    )

    monkeypatch.setattr(
        auth,
        "authenticate_identity_user",
        authenticate_identity_user,
    )

    # The test account is simulated, so use a controlled session-version
    # loader rather than attempting to query a real database.
    manager = SessionManager(
        session_version_loader=lambda user_id: 0,
        require_versioned_sessions=False,
    )

    monkeypatch.setattr(
        auth,
        "SESSION_MANAGER",
        manager,
    )

    return SimpleNamespace(
        clock=current_time,
        session=session_state,
        limiter=limiter,
        account=account,
    )


def test_five_failed_logins_trigger_authentication_lockout(
    rate_limit_environment,
):
    """Five consecutive failed logins should lock the account identifier."""

    environment = rate_limit_environment

    for _ in range(4):
        assert auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        ) is False

    assert environment.limiter.is_locked("testuser") is False

    assert auth.authenticate_user(
        "testuser",
        "WrongPassword123!",
    ) is False

    assert environment.limiter.is_locked("testuser") is True
    assert environment.session == {}


def test_locked_account_rejects_correct_password(
    rate_limit_environment,
):
    """A correct password must not bypass an active lockout."""

    environment = rate_limit_environment

    for _ in range(5):
        assert auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        ) is False

    assert environment.limiter.is_locked("testuser") is True

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is False

    assert environment.session == {}


def test_lockout_expires_after_fifteen_minutes(
    rate_limit_environment,
):
    """Authentication should be possible after the lockout expires."""

    environment = rate_limit_environment

    for _ in range(5):
        assert auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        ) is False

    assert environment.limiter.is_locked("testuser") is True

    environment.clock[0] += 899

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is False

    environment.clock[0] += 1

    assert environment.limiter.is_locked("testuser") is False

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is True

    assert environment.session["authenticated"] is True
    assert environment.session["username"] == "testuser"
    assert environment.session["user_id"] == "test-user-id"
    assert environment.session["session_version"] == 0


def test_successful_login_clears_previous_failed_attempts(
    rate_limit_environment,
):
    """A successful login should reset the failed-attempt history."""

    environment = rate_limit_environment

    for _ in range(4):
        assert auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        ) is False

    assert auth.authenticate_user(
        "testuser",
        VALID_PASSWORD,
    ) is True

    auth.logout()

    for _ in range(4):
        assert auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        ) is False

    assert environment.limiter.is_locked("testuser") is False

    assert auth.authenticate_user(
        "testuser",
        "WrongPassword123!",
    ) is False

    assert environment.limiter.is_locked("testuser") is True


def test_username_case_and_whitespace_share_same_lockout(
    rate_limit_environment,
):
    """Username normalisation must prevent lockout bypass by case changes."""

    environment = rate_limit_environment

    for _ in range(4):
        assert auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        ) is False

    assert auth.authenticate_user(
        "  TESTUSER  ",
        "WrongPassword123!",
    ) is False

    assert environment.limiter.is_locked("testuser") is True
