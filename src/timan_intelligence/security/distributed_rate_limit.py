"""Shared database-backed rate limiting for TimanStat."""

from __future__ import annotations

import hashlib
import math
import time
from typing import Callable

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


def _placeholder() -> str:
    return "%s" if get_database_type() == "postgresql" else "?"


class DatabaseRateLimiter:
    """Apply atomic rate limits shared by workers using the same database.

    PostgreSQL is the recommended shared production backend. SQLite state is
    shared only by processes using the same database file on the same host.
    Identifiers are hashed before storage.
    """

    def __init__(
        self,
        scope: str,
        max_failed_attempts: int = 5,
        window_seconds: float = 900,
        lockout_seconds: float = 900,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError("A rate-limit scope is required.")
        if (
            isinstance(max_failed_attempts, bool)
            or not isinstance(max_failed_attempts, int)
            or max_failed_attempts < 1
        ):
            raise ValueError("max_failed_attempts must be a positive integer.")
        for name, value in (
            ("window_seconds", window_seconds),
            ("lockout_seconds", lockout_seconds),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError(f"{name} must be a positive finite number.")
        if not callable(clock):
            raise ValueError("clock must be callable.")

        self.scope = scope.strip().casefold()
        self.max_failed_attempts = max_failed_attempts
        self.window_seconds = float(window_seconds)
        self.lockout_seconds = float(lockout_seconds)
        self._clock = clock

    def _key_hash(self, identifier: str) -> str:
        if not isinstance(identifier, str):
            raise TypeError("The rate-limit identifier must be a string.")
        normalised = identifier.strip().casefold()
        if not normalised:
            raise ValueError("The rate-limit identifier cannot be empty.")
        material = f"{self.scope}:{normalised}".encode("utf-8")
        return hashlib.sha256(material).hexdigest()

    def is_locked(self, identifier: str) -> bool:
        """Return whether the identifier is currently locked."""
        key_hash = self._key_hash(identifier)
        now = float(self._clock())
        p = _placeholder()
        with database_connection() as connection:
            row = connection.execute(
                f"""
                SELECT locked_until
                FROM rate_limit_states
                WHERE key_hash = {p}
                """,
                (key_hash,),
            ).fetchone()
        return bool(
            row is not None
            and row["locked_until"] is not None
            and float(row["locked_until"]) > now
        )

    def record_failure(self, identifier: str) -> bool:
        """Atomically record a failure and return the resulting lock state."""
        key_hash = self._key_hash(identifier)
        now = float(self._clock())
        cutoff = now - self.window_seconds
        lockout_until = now + self.lockout_seconds
        p = _placeholder()

        with database_connection() as connection:
            connection.execute(
                f"""
                INSERT INTO rate_limit_states (
                    key_hash, window_started_at, failure_count, locked_until
                )
                VALUES ({p}, {p}, 1, NULL)
                ON CONFLICT (key_hash) DO UPDATE SET
                    window_started_at = CASE
                        WHEN rate_limit_states.locked_until > {p}
                            THEN rate_limit_states.window_started_at
                        WHEN rate_limit_states.window_started_at <= {p}
                          OR (
                              rate_limit_states.locked_until IS NOT NULL
                              AND rate_limit_states.locked_until <= {p}
                          )
                            THEN {p}
                        ELSE rate_limit_states.window_started_at
                    END,
                    failure_count = CASE
                        WHEN rate_limit_states.locked_until > {p}
                            THEN rate_limit_states.failure_count
                        WHEN rate_limit_states.window_started_at <= {p}
                          OR (
                              rate_limit_states.locked_until IS NOT NULL
                              AND rate_limit_states.locked_until <= {p}
                          )
                            THEN 1
                        ELSE rate_limit_states.failure_count + 1
                    END,
                    locked_until = CASE
                        WHEN rate_limit_states.locked_until > {p}
                            THEN rate_limit_states.locked_until
                        WHEN rate_limit_states.window_started_at <= {p}
                          OR (
                              rate_limit_states.locked_until IS NOT NULL
                              AND rate_limit_states.locked_until <= {p}
                          )
                            THEN NULL
                        WHEN rate_limit_states.failure_count + 1 >= {p}
                            THEN {p}
                        ELSE rate_limit_states.locked_until
                    END
                """,
                (
                    key_hash, now,
                    now, cutoff, now, now,
                    now, cutoff, now,
                    now, cutoff, now, self.max_failed_attempts,
                    lockout_until,
                ),
            )
            row = connection.execute(
                f"""
                SELECT locked_until
                FROM rate_limit_states
                WHERE key_hash = {p}
                """,
                (key_hash,),
            ).fetchone()
            connection.execute(
                f"""
                DELETE FROM rate_limit_states
                WHERE window_started_at <= {p}
                  AND (locked_until IS NULL OR locked_until <= {p})
                """,
                (
                    now - max(self.window_seconds, self.lockout_seconds),
                    now,
                ),
            )

        return bool(
            row is not None
            and row["locked_until"] is not None
            and float(row["locked_until"]) > now
        )


    def consume_attempt(self, identifier: str) -> bool:
        """Atomically allow at most the configured attempts in a time window.

        Unlike failure counting, this records every request. It is intended
        for outbound email and other request-throttling workflows.
        """
        key_hash = self._key_hash(identifier)
        now = float(self._clock())
        cutoff = now - self.window_seconds
        lockout_until = now + self.lockout_seconds
        p = _placeholder()

        with database_connection() as connection:
            result = connection.execute(
                f"""
                INSERT INTO rate_limit_states (
                    key_hash, window_started_at, failure_count, locked_until
                )
                VALUES (
                    {p}, {p}, 1,
                    CASE WHEN {p} = 1 THEN {p} ELSE NULL END
                )
                ON CONFLICT (key_hash) DO UPDATE SET
                    window_started_at = CASE
                        WHEN rate_limit_states.window_started_at <= {p}
                          OR (
                              rate_limit_states.locked_until IS NOT NULL
                              AND rate_limit_states.locked_until <= {p}
                          )
                            THEN {p}
                        ELSE rate_limit_states.window_started_at
                    END,
                    failure_count = CASE
                        WHEN rate_limit_states.window_started_at <= {p}
                          OR (
                              rate_limit_states.locked_until IS NOT NULL
                              AND rate_limit_states.locked_until <= {p}
                          )
                            THEN 1
                        ELSE rate_limit_states.failure_count + 1
                    END,
                    locked_until = CASE
                        WHEN rate_limit_states.window_started_at <= {p}
                          OR (
                              rate_limit_states.locked_until IS NOT NULL
                              AND rate_limit_states.locked_until <= {p}
                          )
                            THEN CASE WHEN {p} = 1 THEN {p} ELSE NULL END
                        WHEN rate_limit_states.failure_count + 1 >= {p}
                            THEN {p}
                        ELSE rate_limit_states.locked_until
                    END
                WHERE (
                    rate_limit_states.locked_until IS NULL
                    OR rate_limit_states.locked_until <= {p}
                )
                  AND (
                    rate_limit_states.window_started_at <= {p}
                    OR rate_limit_states.failure_count < {p}
                    OR (
                        rate_limit_states.locked_until IS NOT NULL
                        AND rate_limit_states.locked_until <= {p}
                    )
                )
                """,
                (
                    key_hash, now, self.max_failed_attempts, lockout_until,
                    cutoff, now, now,
                    cutoff, now,
                    cutoff, now, self.max_failed_attempts, lockout_until,
                    self.max_failed_attempts, lockout_until,
                    now, cutoff, self.max_failed_attempts, now,
                ),
            )

            connection.execute(
                f"""
                DELETE FROM rate_limit_states
                WHERE window_started_at <= {p}
                  AND (locked_until IS NULL OR locked_until <= {p})
                """,
                (
                    now - max(self.window_seconds, self.lockout_seconds),
                    now,
                ),
            )

        return result.rowcount == 1

    def record_success(self, identifier: str) -> None:
        """Clear the failure history for an identifier."""
        key_hash = self._key_hash(identifier)
        with database_connection() as connection:
            connection.execute(
                f"DELETE FROM rate_limit_states WHERE key_hash = {_placeholder()}",
                (key_hash,),
            )
