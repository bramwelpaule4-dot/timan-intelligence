"""Integration tests for TimanStat authentication rate limiting."""

from types import SimpleNamespace

import pytest

from timan_intelligence.identity.service import _hash_password
from timan_intelligence.security import auth
from timan_intelligence.security.rate_limit import LoginRateLimiter


VALID_PASSWORD = "SecureTestPassword123!"


@pytest.fixture
def rate_limit_environment(monkeypatch):
    """Provide an isolated authentication environment and controllable clock."""

    current_time = [1_000.0]
    session_state = {}

    limiter = LoginRateLimiter(
        max_failed_attempts=5,
        window_seconds=900,
        lockout_seconds=900,
        clock=lambda: current_time[0],
    )

    account = {
        "active": True,
        "role": "user",
        "password_hash": _hash_password(VALID_PASSWORD),
    }

    monkeypatch.setattr(
        auth,
        "st",
        SimpleNamespace(session_state=session_state),
    )
    monkeypatch.setattr(auth, "LOGIN_RATE_LIMITER", limiter)
    monkeypatch.setattr(
        auth,
        "_get_users",
        lambda: {"testuser": account},
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
        auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        )

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
        auth.authenticate_user(
            "testuser",
            "WrongPassword123!",
        )

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
