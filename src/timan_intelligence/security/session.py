
"""Session lifecycle and expiry management for TimanStat."""

from __future__ import annotations

import math
import time

from collections.abc import MutableMapping
from typing import Callable

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


SESSION_IDLE_TIMEOUT_SECONDS = 30 * 60
SESSION_ABSOLUTE_TIMEOUT_SECONDS = 12 * 60 * 60

SESSION_AUTHENTICATION_KEYS = (
    "authenticated",
    "username",
    "role",
    "user_id",
    "session_version",
    "authenticated_at",
    "last_activity_at",
)

VALID_SESSION_ROLES = {
    "developer",
    "admin",
    "user",
}


def _load_session_version(user_id: str) -> int | None:
    """Retrieve the current session version for an active account."""

    placeholder = (
        "%s" if get_database_type() == "postgresql" else "?"
    )

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT session_version
            FROM users
            WHERE id = {placeholder}
              AND is_active = TRUE
            """,
            (user_id,),
        ).fetchone()

    if user is None:
        return None

    version = user["session_version"]

    if (
        isinstance(version, bool)
        or not isinstance(version, int)
        or version < 0
    ):
        return None

    return version


class SessionManager:
    """Manage authenticated session creation, validation and expiry."""

    def __init__(
        self,
        idle_timeout_seconds: float = SESSION_IDLE_TIMEOUT_SECONDS,
        absolute_timeout_seconds: float = SESSION_ABSOLUTE_TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        session_version_loader: Callable[[str], int | None] | None = None,
        require_versioned_sessions: bool = False,
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

        if session_version_loader is not None and not callable(
            session_version_loader
        ):
            raise ValueError(
                "session_version_loader must be callable."
            )

        if not isinstance(require_versioned_sessions, bool):
            raise ValueError(
                "require_versioned_sessions must be a boolean."
            )

        self.idle_timeout_seconds = float(idle_timeout_seconds)
        self.absolute_timeout_seconds = float(absolute_timeout_seconds)
        self._clock = clock
        self._session_version_loader = (
            session_version_loader or _load_session_version
        )
        self.require_versioned_sessions = require_versioned_sessions

    def create_session(
        self,
        session_state: MutableMapping,
        username: str,
        role: str,
        *,
        user_id: str | None = None,
    ) -> None:
        """Create a new authenticated session."""

        if not isinstance(username, str) or not username.strip():
            raise ValueError("A valid username is required.")

        if not isinstance(role, str) or role not in VALID_SESSION_ROLES:
            raise ValueError("A valid account role is required.")

        if user_id is not None:
            if not isinstance(user_id, str) or not user_id.strip():
                raise ValueError("A valid user ID is required.")

            user_id = user_id.strip()

            try:
                session_version = self._session_version_loader(user_id)
            except Exception as exc:
                raise RuntimeError(
                    "The account session version could not be verified."
                ) from exc

            if (
                isinstance(session_version, bool)
                or not isinstance(session_version, int)
                or session_version < 0
            ):
                raise ValueError(
                    "The account session version is invalid."
                )

        else:
            if self.require_versioned_sessions:
                raise ValueError(
                    "A user ID is required for authenticated sessions."
                )

            session_version = None

        now = self._clock()

        session_state["authenticated"] = True
        session_state["username"] = username.strip().casefold()
        session_state["role"] = role
        session_state["user_id"] = user_id
        session_state["session_version"] = session_version
        session_state["authenticated_at"] = now
        session_state["last_activity_at"] = now

    def clear_session(self, session_state: MutableMapping) -> None:
        """Remove all authentication-related session information."""

        for key in SESSION_AUTHENTICATION_KEYS:
            session_state.pop(key, None)

    def _validate_account_session(
        self,
        session_state: MutableMapping,
    ) -> bool:
        """Check whether the session still matches the account version."""

        user_id = session_state.get("user_id")
        session_version = session_state.get("session_version")

        if user_id is None and session_version is None:
            return not self.require_versioned_sessions

        if (
            not isinstance(user_id, str)
            or not user_id.strip()
            or isinstance(session_version, bool)
            or not isinstance(session_version, int)
            or session_version < 0
        ):
            return False

        try:
            current_version = self._session_version_loader(user_id)
        except Exception:
            return False

        if (
            isinstance(current_version, bool)
            or not isinstance(current_version, int)
            or current_version < 0
        ):
            return False

        return current_version == session_version

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

        if not self._validate_account_session(session_state):
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
