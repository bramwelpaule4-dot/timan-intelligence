"""Session lifecycle and expiry management for TimanStat."""

from __future__ import annotations

import math
import time

from collections.abc import MutableMapping
from typing import Callable


SESSION_IDLE_TIMEOUT_SECONDS = 30 * 60
SESSION_ABSOLUTE_TIMEOUT_SECONDS = 12 * 60 * 60

SESSION_AUTHENTICATION_KEYS = (
    "authenticated",
    "username",
    "role",
    "authenticated_at",
    "last_activity_at",
)

VALID_SESSION_ROLES = {
    "developer",
    "admin",
    "user",
}


class SessionManager:
    """Manage authenticated session creation, validation and expiry."""

    def __init__(
        self,
        idle_timeout_seconds: float = SESSION_IDLE_TIMEOUT_SECONDS,
        absolute_timeout_seconds: float = SESSION_ABSOLUTE_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(idle_timeout_seconds, bool)
            or not isinstance(idle_timeout_seconds, (int, float))
            or not math.isfinite(idle_timeout_seconds)
            or idle_timeout_seconds <= 0
        ):
            raise ValueError(
                "idle_timeout_seconds must be a positive finite number."
            )

        if (
            isinstance(absolute_timeout_seconds, bool)
            or not isinstance(absolute_timeout_seconds, (int, float))
            or not math.isfinite(absolute_timeout_seconds)
            or absolute_timeout_seconds <= 0
        ):
            raise ValueError(
                "absolute_timeout_seconds must be a positive finite number."
            )

        if absolute_timeout_seconds < idle_timeout_seconds:
            raise ValueError(
                "Absolute timeout cannot be shorter than idle timeout."
            )

        if not callable(clock):
            raise ValueError("clock must be callable.")

        self.idle_timeout_seconds = float(idle_timeout_seconds)
        self.absolute_timeout_seconds = float(absolute_timeout_seconds)
        self._clock = clock

    def create_session(
        self,
        session_state: MutableMapping,
        username: str,
        role: str,
    ) -> None:
        """Create a new authenticated session."""

        if not isinstance(username, str) or not username.strip():
            raise ValueError("A valid username is required.")

        if not isinstance(role, str) or role not in VALID_SESSION_ROLES:
            raise ValueError("A valid account role is required.")

        now = self._clock()

        session_state["authenticated"] = True
        session_state["username"] = username.strip().casefold()
        session_state["role"] = role
        session_state["authenticated_at"] = now
        session_state["last_activity_at"] = now

    def clear_session(self, session_state: MutableMapping) -> None:
        """Remove all authentication-related session information."""

        for key in SESSION_AUTHENTICATION_KEYS:
            session_state.pop(key, None)

    def is_valid(self, session_state: MutableMapping) -> bool:
        """Validate a session and refresh its activity timestamp."""

        if session_state.get("authenticated") is not True:
            self.clear_session(session_state)
            return False

        username = session_state.get("username")
        role = session_state.get("role")
        authenticated_at = session_state.get("authenticated_at")
        last_activity_at = session_state.get("last_activity_at")

        if (
            not isinstance(username, str)
            or not username.strip()
            or not isinstance(role, str)
            or role not in VALID_SESSION_ROLES
        ):
            self.clear_session(session_state)
            return False

        timestamps = (authenticated_at, last_activity_at)

        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in timestamps
        ):
            self.clear_session(session_state)
            return False

        now = self._clock()

        if authenticated_at > now or last_activity_at > now:
            self.clear_session(session_state)
            return False

        if now - authenticated_at >= self.absolute_timeout_seconds:
            self.clear_session(session_state)
            return False

        if now - last_activity_at >= self.idle_timeout_seconds:
            self.clear_session(session_state)
            return False

        session_state["last_activity_at"] = now

        return True
