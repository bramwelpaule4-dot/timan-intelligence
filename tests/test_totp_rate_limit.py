
"""Tests for TimanStat TOTP attempt rate limiting."""

import pytest

from timan_intelligence.security.totp_rate_limit import (
    TOTPAttemptRateLimiter,
)


@pytest.fixture
def clock():
    """Provide a controllable monotonic clock."""

    return {"now": 1_000.0}


@pytest.fixture
def limiter(clock):
    """Create a limiter with short test-friendly settings."""

    return TOTPAttemptRateLimiter(
        max_failed_attempts=5,
        window_seconds=900,
        lockout_seconds=900,
        clock=lambda: clock["now"],
    )


def test_totp_limiter_allows_attempts_below_limit(limiter):
    """Fewer than five failures do not cause lockout."""

    for _ in range(4):
        assert limiter.record_failure(
            "user-1",
            "verification",
        ) is False

    assert limiter.is_locked("user-1", "verification") is False


def test_totp_limiter_locks_after_maximum_failed_attempts(limiter):
    """The fifth failed attempt triggers a lockout."""

    for _ in range(4):
        limiter.record_failure("user-1", "verification")

    assert limiter.record_failure(
        "user-1",
        "verification",
    ) is True

    assert limiter.is_locked("user-1", "verification") is True


def test_totp_limiter_rejects_attempts_during_lockout(limiter):
    """A locked operation remains locked until the lockout expires."""

    for _ in range(5):
        limiter.record_failure("user-1", "verification")

    assert limiter.is_locked("user-1", "verification") is True

    assert limiter.record_failure(
        "user-1",
        "verification",
    ) is True


def test_totp_limiter_unlocks_after_lockout_period(limiter, clock):
    """A user can attempt verification again after 15 minutes."""

    for _ in range(5):
        limiter.record_failure("user-1", "verification")

    assert limiter.is_locked("user-1", "verification") is True

    clock["now"] += 900

    assert limiter.is_locked("user-1", "verification") is False

    assert limiter.record_failure(
        "user-1",
        "verification",
    ) is False


def test_totp_limiter_success_clears_failure_history(limiter):
    """A successful attempt resets the failed-attempt counter."""

    for _ in range(4):
        limiter.record_failure("user-1", "verification")

    limiter.record_success("user-1", "verification")

    for _ in range(4):
        assert limiter.record_failure(
            "user-1",
            "verification",
        ) is False

    assert limiter.is_locked("user-1", "verification") is False


def test_totp_limiter_tracks_users_independently(limiter):
    """One user's failures do not lock another user's account."""

    for _ in range(5):
        limiter.record_failure("user-1", "verification")

    assert limiter.is_locked("user-1", "verification") is True
    assert limiter.is_locked("user-2", "verification") is False


def test_totp_limiter_separates_enrolment_and_verification(limiter):
    """Enrolment and normal verification have separate limits."""

    for _ in range(5):
        limiter.record_failure("user-1", "enrolment")

    assert limiter.is_locked("user-1", "enrolment") is True
    assert limiter.is_locked("user-1", "verification") is False


def test_totp_limiter_success_only_resets_matching_operation(limiter):
    """Success in one operation does not clear another operation."""

    for _ in range(5):
        limiter.record_failure("user-1", "enrolment")

    for _ in range(3):
        limiter.record_failure("user-1", "verification")

    limiter.record_success("user-1", "verification")

    assert limiter.is_locked("user-1", "enrolment") is True
    assert limiter.is_locked("user-1", "verification") is False


@pytest.mark.parametrize(
    "invalid_user_id",
    [None, "", " ", 0, -1],
)
def test_totp_limiter_rejects_invalid_user_ids(
    limiter,
    invalid_user_id,
):
    """Invalid user identifiers cannot be used as limiter keys."""

    with pytest.raises(ValueError):
        limiter.is_locked(invalid_user_id, "verification")

    with pytest.raises(ValueError):
        limiter.record_failure(invalid_user_id, "verification")

    with pytest.raises(ValueError):
        limiter.record_success(invalid_user_id, "verification")


def test_totp_limiter_rejects_unsupported_operation(limiter):
    """Only enrolment and verification operations are accepted."""

    with pytest.raises(ValueError):
        limiter.is_locked("user-1", "password-reset")
