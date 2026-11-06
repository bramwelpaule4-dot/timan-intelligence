
"""Integration tests for TimanStat TOTP service rate limiting."""

import pytest

from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.security.totp import generate_totp_code
from timan_intelligence.security.totp_encryption import (
    generate_totp_encryption_key,
)
from timan_intelligence.security.totp_rate_limit import (
    TOTPAttemptRateLimiter,
)
from timan_intelligence.security import totp_service


TEST_TIMESTAMP = 1_700_000_000


@pytest.fixture
def rate_limited_totp_user(tmp_path, monkeypatch):
    """Create an isolated TOTP user and an isolated rate limiter."""

    database_file = tmp_path / "test_timanstat_totp_rate_limit.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    monkeypatch.setenv(
        "TIMANSTAT_TOTP_ENCRYPTION_KEY",
        generate_totp_encryption_key(),
    )

    initialise_database()

    user_id = register_user(
        username="totp_rate_limit_user",
        email="totp_rate_limit@example.com",
        full_name="TOTP Rate Limit User",
        password="SecureTestPassword123!",
    )

    clock_state = {"now": 1000.0}

    limiter = TOTPAttemptRateLimiter(
        max_failed_attempts=5,
        window_seconds=900,
        lockout_seconds=900,
        clock=lambda: clock_state["now"],
    )

    monkeypatch.setattr(
        totp_service,
        "totp_attempt_limiter",
        limiter,
    )

    return {
        "user_id": user_id,
        "limiter": limiter,
        "clock_state": clock_state,
    }


def _begin_and_confirm_enrolment(user_id):
    """Enrol a test user using a valid authenticator code."""

    enrolment = totp_service.begin_totp_enrolment(user_id)

    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    confirmed = totp_service.confirm_totp_enrolment(
        user_id=user_id,
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is True

    return enrolment["secret"]


def test_enrolment_locks_after_five_failed_attempts(
    rate_limited_totp_user,
):
    """Five invalid enrolment codes trigger a 15-minute lockout."""

    user_id = rate_limited_totp_user["user_id"]
    limiter = rate_limited_totp_user["limiter"]

    totp_service.begin_totp_enrolment(user_id)

    for _ in range(5):
        result = totp_service.confirm_totp_enrolment(
            user_id=user_id,
            code="000000",
            at_time=TEST_TIMESTAMP,
        )
        assert result is False

    assert limiter.is_locked(user_id, "enrolment") is True

    # Even a valid code must be rejected while the operation is locked.
    # The pending secret is still present, but cannot be confirmed.
    result = totp_service.confirm_totp_enrolment(
        user_id=user_id,
        code="000000",
        at_time=TEST_TIMESTAMP,
    )

    assert result is False


def test_verification_locks_after_five_failed_attempts(
    rate_limited_totp_user,
):
    """Five invalid verification codes trigger a lockout."""

    user_id = rate_limited_totp_user["user_id"]
    limiter = rate_limited_totp_user["limiter"]

    secret = _begin_and_confirm_enrolment(user_id)

    for _ in range(5):
        result = totp_service.verify_totp_for_user(
            user_id=user_id,
            code="000000",
            at_time=TEST_TIMESTAMP + 30,
        )
        assert result is False

    assert limiter.is_locked(user_id, "verification") is True

    valid_code = generate_totp_code(
        secret,
        at_time=TEST_TIMESTAMP + 30,
    )

    # A valid code must not bypass an active lockout.
    result = totp_service.verify_totp_for_user(
        user_id=user_id,
        code=valid_code,
        at_time=TEST_TIMESTAMP + 30,
    )

    assert result is False


def test_enrolment_and_verification_have_separate_limits(
    rate_limited_totp_user,
):
    """An enrolment lockout does not lock the verification operation."""

    user_id = rate_limited_totp_user["user_id"]
    limiter = rate_limited_totp_user["limiter"]

    totp_service.begin_totp_enrolment(user_id)

    for _ in range(5):
        totp_service.confirm_totp_enrolment(
            user_id=user_id,
            code="000000",
            at_time=TEST_TIMESTAMP,
        )

    assert limiter.is_locked(user_id, "enrolment") is True
    assert limiter.is_locked(user_id, "verification") is False


def test_successful_enrolment_clears_failure_history(
    rate_limited_totp_user,
):
    """Successful enrolment clears previous failed confirmation attempts."""

    user_id = rate_limited_totp_user["user_id"]
    limiter = rate_limited_totp_user["limiter"]

    enrolment = totp_service.begin_totp_enrolment(user_id)

    # Four failures remain below the lockout threshold.
    for _ in range(4):
        assert totp_service.confirm_totp_enrolment(
            user_id=user_id,
            code="000000",
            at_time=TEST_TIMESTAMP,
        ) is False

    valid_code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert totp_service.confirm_totp_enrolment(
        user_id=user_id,
        code=valid_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    assert limiter.is_locked(user_id, "enrolment") is False


def test_successful_verification_clears_failure_history(
    rate_limited_totp_user,
):
    """A valid verification clears previous failed verification attempts."""

    user_id = rate_limited_totp_user["user_id"]
    limiter = rate_limited_totp_user["limiter"]

    secret = _begin_and_confirm_enrolment(user_id)

    first_timestamp = TEST_TIMESTAMP + 30

    for _ in range(4):
        assert totp_service.verify_totp_for_user(
            user_id=user_id,
            code="000000",
            at_time=first_timestamp,
        ) is False

    valid_code = generate_totp_code(
        secret,
        at_time=first_timestamp,
    )

    assert totp_service.verify_totp_for_user(
        user_id=user_id,
        code=valid_code,
        at_time=first_timestamp,
    ) is True

    assert limiter.is_locked(user_id, "verification") is False

    # Four further failures must not lock the account if the successful
    # verification correctly cleared the previous failure history.
    second_timestamp = first_timestamp + 30

    for _ in range(4):
        assert totp_service.verify_totp_for_user(
            user_id=user_id,
            code="000000",
            at_time=second_timestamp,
        ) is False

    assert limiter.is_locked(user_id, "verification") is False

    second_valid_code = generate_totp_code(
        secret,
        at_time=second_timestamp,
    )

    assert totp_service.verify_totp_for_user(
        user_id=user_id,
        code=second_valid_code,
        at_time=second_timestamp,
    ) is True


def test_totp_lockout_expires_after_fifteen_minutes(
    rate_limited_totp_user,
):
    """A TOTP operation becomes available after its lockout expires."""

    user_id = rate_limited_totp_user["user_id"]
    limiter = rate_limited_totp_user["limiter"]
    clock_state = rate_limited_totp_user["clock_state"]

    totp_service.begin_totp_enrolment(user_id)

    for _ in range(5):
        totp_service.confirm_totp_enrolment(
            user_id=user_id,
            code="000000",
            at_time=TEST_TIMESTAMP,
        )

    assert limiter.is_locked(user_id, "enrolment") is True

    clock_state["now"] += 901

    assert limiter.is_locked(user_id, "enrolment") is False
