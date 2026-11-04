
"""Tests for TimanStat session lifecycle and expiry management."""

import pytest

from timan_intelligence.security.session import (
    SESSION_ABSOLUTE_TIMEOUT_SECONDS,
    SESSION_AUTHENTICATION_KEYS,
    SESSION_IDLE_TIMEOUT_SECONDS,
    SessionManager,
)


class FakeClock:
    """Provide controllable time for deterministic session tests."""

    def __init__(self, initial_time=1_000_000.0):
        self.current_time = initial_time

    def __call__(self):
        return self.current_time

    def advance(self, seconds):
        self.current_time += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def manager(clock):
    return SessionManager(clock=clock)


@pytest.fixture
def session_state():
    return {}


def assert_session_cleared(session_state):
    """Confirm that all authentication-related fields are removed."""

    for key in SESSION_AUTHENTICATION_KEYS:
        assert key not in session_state


def test_session_manager_uses_expected_default_timeouts():
    manager = SessionManager()

    assert manager.idle_timeout_seconds == SESSION_IDLE_TIMEOUT_SECONDS
    assert manager.absolute_timeout_seconds == SESSION_ABSOLUTE_TIMEOUT_SECONDS


def test_session_creation_sets_authentication_details(
    manager,
    session_state,
    clock,
):
    manager.create_session(
        session_state,
        "Bramwel",
        "user",
    )

    assert session_state["authenticated"] is True
    assert session_state["username"] == "bramwel"
    assert session_state["role"] == "user"
    assert session_state["authenticated_at"] == clock()
    assert session_state["last_activity_at"] == clock()


def test_session_creation_normalises_username(
    manager,
    session_state,
):
    manager.create_session(
        session_state,
        "  BRAMWEL  ",
        "user",
    )

    assert session_state["username"] == "bramwel"


@pytest.mark.parametrize(
    "role",
    ["developer", "admin", "user"],
)
def test_session_creation_accepts_valid_roles(
    manager,
    session_state,
    role,
):
    manager.create_session(
        session_state,
        "bramwel",
        role,
    )

    assert session_state["role"] == role


@pytest.mark.parametrize(
    "username",
    ["", " ", None, 123],
)
def test_session_creation_rejects_invalid_usernames(
    manager,
    session_state,
    username,
):
    with pytest.raises(ValueError):
        manager.create_session(
            session_state,
            username,
            "user",
        )


@pytest.mark.parametrize(
    "role",
    ["", "unknown", "superuser", None, 123],
)
def test_session_creation_rejects_invalid_roles(
    manager,
    session_state,
    role,
):
    with pytest.raises(ValueError):
        manager.create_session(
            session_state,
            "bramwel",
            role,
        )


def test_valid_session_passes_validation_and_refreshes_activity(
    manager,
    session_state,
    clock,
):
    manager.create_session(
        session_state,
        "bramwel",
        "user",
    )

    clock.advance(60)

    assert manager.is_valid(session_state) is True
    assert session_state["last_activity_at"] == clock()


def test_session_expires_after_idle_timeout(
    manager,
    session_state,
    clock,
):
    manager.create_session(
        session_state,
        "bramwel",
        "user",
    )

    clock.advance(SESSION_IDLE_TIMEOUT_SECONDS)

    assert manager.is_valid(session_state) is False
    assert_session_cleared(session_state)


def test_session_remains_valid_before_idle_timeout(
    manager,
    session_state,
    clock,
):
    manager.create_session(
        session_state,
        "bramwel",
        "user",
    )

    clock.advance(SESSION_IDLE_TIMEOUT_SECONDS - 1)

    assert manager.is_valid(session_state) is True


def test_session_expires_after_absolute_timeout_despite_activity(
    manager,
    session_state,
    clock,
):
    manager.create_session(
        session_state,
        "bramwel",
        "user",
    )

    activity_interval = 20 * 60

    for _ in range(36):
        clock.advance(activity_interval)

        if clock() - session_state.get(
            "authenticated_at",
            clock(),
        ) >= SESSION_ABSOLUTE_TIMEOUT_SECONDS:
            break

        assert manager.is_valid(session_state) is True

    clock.advance(SESSION_ABSOLUTE_TIMEOUT_SECONDS)

    assert manager.is_valid(session_state) is False
    assert_session_cleared(session_state)


def test_expired_session_is_cleared(
    manager,
    session_state,
    clock,
):
    manager.create_session(
        session_state,
        "bramwel",
        "user",
    )

    clock.advance(SESSION_IDLE_TIMEOUT_SECONDS)

    assert manager.is_valid(session_state) is False

    for key in SESSION_AUTHENTICATION_KEYS:
        assert key not in session_state


def test_unauthenticated_session_is_rejected_and_cleared(
    manager,
    session_state,
):
    session_state.update(
        {
            "authenticated": False,
            "username": "bramwel",
            "role": "user",
            "authenticated_at": 1_000_000.0,
            "last_activity_at": 1_000_000.0,
        }
    )

    assert manager.is_valid(session_state) is False
    assert_session_cleared(session_state)


def test_missing_authentication_fields_are_rejected(
    manager,
    session_state,
):
    session_state["authenticated"] = True
    session_state["username"] = "bramwel"

    assert manager.is_valid(session_state) is False
    assert_session_cleared(session_state)


def test_invalid_role_in_existing_session_is_rejected(
    manager,
    session_state,
):
    session_state.update(
        {
            "authenticated": True,
            "username": "bramwel",
            "role": "superuser",
            "authenticated_at": 1_000_000.0,
            "last_activity_at": 1_000_000.0,
        }
    )

    assert manager.is_valid(session_state) is False
    assert_session_cleared(session_state)


@pytest.mark.parametrize(
    "invalid_timestamp",
    [
        None,
        "1000000",
        True,
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_invalid_session_timestamps_are_rejected(
    manager,
    session_state,
    invalid_timestamp,
):
    session_state.update(
        {
            "authenticated": True,
            "username": "bramwel",
            "role": "user",
            "authenticated_at": invalid_timestamp,
            "last_activity_at": 1_000_000.0,
        }
    )

    assert manager.is_valid(session_state) is False
    assert_session_cleared(session_state)


def test_future_session_timestamp_is_rejected(
    manager,
    session_state,
    clock,
):
    manager.create_session(
        session_state,
        "bramwel",
        "user",
    )

    session_state["last_activity_at"] = clock() + 60

    assert manager.is_valid(session_state) is False
    assert_session_cleared(session_state)


def test_clear_session_removes_authentication_fields(
    manager,
    session_state,
):
    manager.create_session(
        session_state,
        "bramwel",
        "user",
    )

    session_state["unrelated_setting"] = "keep"

    manager.clear_session(session_state)

    assert_session_cleared(session_state)
    assert session_state["unrelated_setting"] == "keep"


@pytest.mark.parametrize(
    "idle_timeout,absolute_timeout",
    [
        (0, 3600),
        (-1, 3600),
        (float("inf"), 3600),
        (float("nan"), 3600),
        (3600, 0),
        (3600, -1),
        (3600, float("inf")),
        (3600, float("nan")),
        (3600, 1800),
        (True, 3600),
        (3600, True),
    ],
)
def test_session_manager_rejects_invalid_timeout_configuration(
    idle_timeout,
    absolute_timeout,
):
    with pytest.raises(ValueError):
        SessionManager(
            idle_timeout_seconds=idle_timeout,
            absolute_timeout_seconds=absolute_timeout,
        )


def test_session_manager_rejects_non_callable_clock():
    with pytest.raises(ValueError):
        SessionManager(clock=123)
