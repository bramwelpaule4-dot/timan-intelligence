"""Tests for shared database-backed rate limiting."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.security.distributed_rate_limit import DatabaseRateLimiter


@pytest.fixture
def rate_limit_database(tmp_path, monkeypatch):
    path = tmp_path / "rate_limits.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
    monkeypatch.setenv("TIMANSTAT_RATE_LIMIT_HMAC_KEY", "test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum")
    initialise_database()
    return path


def test_separate_limiter_instances_share_lockout(rate_limit_database):
    first = DatabaseRateLimiter(scope="login")
    second = DatabaseRateLimiter(scope="login")

    for _ in range(4):
        assert first.record_failure("Person@Example.com") is False

    assert second.record_failure(" person@example.com ") is True
    assert first.is_locked("PERSON@example.com") is True


def test_lockout_expires_and_attempt_counter_resets(rate_limit_database):
    clock = [1_000.0]
    limiter = DatabaseRateLimiter(
        scope="login",
        max_failed_attempts=5,
        window_seconds=900,
        lockout_seconds=900,
        clock=lambda: clock[0],
    )

    for _ in range(5):
        limiter.record_failure("user-1")

    assert limiter.is_locked("user-1") is True

    clock[0] += 901

    assert limiter.is_locked("user-1") is False
    assert limiter.record_failure("user-1") is False
    assert limiter.is_locked("user-1") is False


def test_failure_window_expires_before_lockout_threshold(rate_limit_database):
    clock = [1_000.0]
    limiter = DatabaseRateLimiter(
        scope="login",
        max_failed_attempts=3,
        window_seconds=10,
        lockout_seconds=20,
        clock=lambda: clock[0],
    )

    limiter.record_failure("user-1")
    limiter.record_failure("user-1")
    clock[0] += 11

    assert limiter.record_failure("user-1") is False
    assert limiter.is_locked("user-1") is False


def test_success_clears_only_matching_scope_and_identifier(rate_limit_database):
    login = DatabaseRateLimiter(scope="login")
    recovery = DatabaseRateLimiter(scope="recovery")

    for _ in range(5):
        login.record_failure("user-1")
        recovery.record_failure("user-1")

    login.record_success("user-1")

    assert login.is_locked("user-1") is False
    assert recovery.is_locked("user-1") is True


def test_rate_limit_storage_does_not_contain_raw_identifier(rate_limit_database):
    limiter = DatabaseRateLimiter(scope="login")
    limiter.record_failure("private-user@example.com")

    with database_connection() as connection:
        rows = connection.execute(
            "SELECT key_hash FROM rate_limit_states"
        ).fetchall()

    assert len(rows) == 1
    assert "private-user@example.com" not in rows[0]["key_hash"]
    assert len(rows[0]["key_hash"]) == 64


@pytest.mark.parametrize("identifier", [None, "", "  "])
def test_invalid_identifiers_are_rejected(rate_limit_database, identifier):
    limiter = DatabaseRateLimiter(scope="login")

    with pytest.raises((TypeError, ValueError)):
        limiter.is_locked(identifier)



def test_request_throttle_is_shared_between_instances(rate_limit_database):
    clock = [5_000.0]
    first = DatabaseRateLimiter(
        scope="email-reset",
        max_failed_attempts=1,
        window_seconds=60,
        lockout_seconds=60,
        clock=lambda: clock[0],
    )
    second = DatabaseRateLimiter(
        scope="email-reset",
        max_failed_attempts=1,
        window_seconds=60,
        lockout_seconds=60,
        clock=lambda: clock[0],
    )

    assert first.consume_attempt("user@example.com") is True
    assert second.consume_attempt("USER@example.com") is False

    clock[0] += 61

    assert second.consume_attempt("user@example.com") is True


def test_request_throttle_allows_configured_number_of_attempts(rate_limit_database):
    limiter = DatabaseRateLimiter(
        scope="email-verification",
        max_failed_attempts=2,
        window_seconds=60,
        lockout_seconds=60,
        clock=lambda: 8_000.0,
    )

    assert limiter.consume_attempt("user@example.com") is True
    assert limiter.consume_attempt("user@example.com") is True
    assert limiter.consume_attempt("user@example.com") is False


def test_hmac_identifier_hash_is_stable_and_scope_separated(rate_limit_database):
    """The same key and identifier produce stable, namespaced digests."""
    first = DatabaseRateLimiter(scope="login", hmac_secret="test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum")
    second = DatabaseRateLimiter(scope="login", hmac_secret="test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum")
    other_scope = DatabaseRateLimiter(scope="recovery", hmac_secret="test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum")

    assert first._key_hash("User@Example.com") == second._key_hash(
        " user@example.com "
    )
    assert first._key_hash("user@example.com") != other_scope._key_hash(
        "user@example.com"
    )


def test_hmac_identifier_hash_changes_when_secret_changes(rate_limit_database):
    """A different application secret produces unrelated stored keys."""
    first = DatabaseRateLimiter(scope="login", hmac_secret="test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum")
    second = DatabaseRateLimiter(
        scope="login",
        hmac_secret="different-test-only-key-with-at-least-32-bytes",
    )

    assert first._key_hash("user@example.com") != second._key_hash(
        "user@example.com"
    )


@pytest.mark.parametrize("secret", ["", "short", "é" * 10])
def test_hmac_requires_at_least_32_secret_bytes(rate_limit_database, secret):
    """Weak or absent HMAC secrets are rejected rather than downgraded."""
    limiter = DatabaseRateLimiter(scope="login", hmac_secret=secret)

    with pytest.raises(RuntimeError, match="HMAC key"):
        limiter.is_locked("user@example.com")

def test_different_identifiers_have_independent_rate_limit_state(
    rate_limit_database,
):
    limiter = DatabaseRateLimiter(
        scope="login",
        max_failed_attempts=2,
        window_seconds=60,
        lockout_seconds=60,
    )

    assert limiter.record_failure("first-user@example.com") is False
    assert limiter.record_failure("first-user@example.com") is True

    assert limiter.is_locked("first-user@example.com") is True
    assert limiter.is_locked("second-user@example.com") is False


def test_hmac_key_rotation_does_not_reuse_previous_rate_limit_digest(
    rate_limit_database,
):
    """Changing the HMAC secret deliberately starts a fresh key namespace."""
    old_key = "test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum"
    new_key = "rotated-test-only-rate-limit-hmac-key-with-32-bytes"

    previous = DatabaseRateLimiter(
        scope="login",
        max_failed_attempts=1,
        window_seconds=60,
        lockout_seconds=60,
        hmac_secret=old_key,
    )
    rotated = DatabaseRateLimiter(
        scope="login",
        max_failed_attempts=1,
        window_seconds=60,
        lockout_seconds=60,
        hmac_secret=new_key,
    )

    assert previous.record_failure("rotation-user@example.com") is True
    assert previous.is_locked("rotation-user@example.com") is True

    # A new HMAC key produces a distinct digest. This resets historical
    # limiter state; operators must account for that during key rotation.
    assert rotated.is_locked("rotation-user@example.com") is False
    assert rotated.record_failure("rotation-user@example.com") is True

