"""Thread-safe login rate limiting for TimanStat."""

from __future__ import annotations

import math
import threading
import time

from collections import deque
from dataclasses import dataclass, field
from typing import Callable


MAX_FAILED_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 15 * 60
LOCKOUT_SECONDS = 15 * 60


@dataclass
class _AttemptState:
    """Track failed login attempts for one account identifier."""

    failures: deque[float] = field(default_factory=deque)
    locked_until: float | None = None


class LoginRateLimiter:
    """Apply a configurable failed-login limit to account identifiers.

    The limiter is thread-safe and uses a monotonic clock so that changes
    to the system clock do not affect lockout calculations.

    State is held in application memory. It is not shared across separate
    application processes or preserved after an application restart.
    """

    def __init__(
        self,
        max_failed_attempts: int = MAX_FAILED_ATTEMPTS,
        window_seconds: float = ATTEMPT_WINDOW_SECONDS,
        lockout_seconds: float = LOCKOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if (
            isinstance(max_failed_attempts, bool)
            or not isinstance(max_failed_attempts, int)
            or max_failed_attempts < 1
        ):
            raise ValueError("max_failed_attempts must be a positive integer.")

        if (
            isinstance(window_seconds, bool)
            or not isinstance(window_seconds, (int, float))
            or not math.isfinite(window_seconds)
            or window_seconds <= 0
        ):
            raise ValueError("window_seconds must be a positive finite number.")

        if (
            isinstance(lockout_seconds, bool)
            or not isinstance(lockout_seconds, (int, float))
            or not math.isfinite(lockout_seconds)
            or lockout_seconds <= 0
        ):
            raise ValueError("lockout_seconds must be a positive finite number.")

        if not callable(clock):
            raise ValueError("clock must be callable.")

        self.max_failed_attempts = max_failed_attempts
        self.window_seconds = float(window_seconds)
        self.lockout_seconds = float(lockout_seconds)
        self._clock = clock

        self._attempts: dict[str, _AttemptState] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _normalise_identifier(identifier: str) -> str:
        """Validate and normalise an account identifier."""

        if not isinstance(identifier, str):
            raise TypeError("The account identifier must be a string.")

        normalised = identifier.strip().casefold()

        if not normalised:
            raise ValueError("The account identifier cannot be empty.")

        return normalised

    def _cleanup_expired_states(self, now: float) -> None:
        """Remove expired lockouts and obsolete failure histories."""

        expired_identifiers = []

        for identifier, state in self._attempts.items():
            if state.locked_until is not None:
                if now < state.locked_until:
                    continue

                state.locked_until = None
                state.failures.clear()

            cutoff = now - self.window_seconds

            while state.failures and state.failures[0] <= cutoff:
                state.failures.popleft()

            if not state.failures:
                expired_identifiers.append(identifier)

        for identifier in expired_identifiers:
            self._attempts.pop(identifier, None)

    def is_locked(self, identifier: str) -> bool:
        """Return whether an account identifier is currently locked."""

        key = self._normalise_identifier(identifier)
        now = self._clock()

        with self._lock:
            self._cleanup_expired_states(now)

            state = self._attempts.get(key)

            if state is None or state.locked_until is None:
                return False

            return now < state.locked_until

    def record_failure(self, identifier: str) -> bool:
        """Record a failed login and return whether the account is locked."""

        key = self._normalise_identifier(identifier)
        now = self._clock()

        with self._lock:
            self._cleanup_expired_states(now)

            state = self._attempts.setdefault(key, _AttemptState())

            if state.locked_until is not None:
                return True

            cutoff = now - self.window_seconds

            while state.failures and state.failures[0] <= cutoff:
                state.failures.popleft()

            state.failures.append(now)

            if len(state.failures) >= self.max_failed_attempts:
                state.failures.clear()
                state.locked_until = now + self.lockout_seconds
                return True

            return False

    def record_success(self, identifier: str) -> None:
        """Clear failed-login history after successful authentication."""

        key = self._normalise_identifier(identifier)

        with self._lock:
            self._attempts.pop(key, None)
