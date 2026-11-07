"""Tests for shared database-backed rate limiting."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.security.distributed_rate_limit import DatabaseRateLimiter


@pytest.fixture
def rate_limit_database(tmp_path, monkeypatch):
    path = tmp_path / "rate_limits.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
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
