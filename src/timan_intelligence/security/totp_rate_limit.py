
"""Rate limiting for TimanStat TOTP operations."""

from __future__ import annotations

from timan_intelligence.security.rate_limit import LoginRateLimiter


# TOTP uses a separate limiter from password login attempts.
# Enrolment confirmation and normal verification use separate keys.
TOTP_MAX_FAILED_ATTEMPTS = 5
TOTP_ATTEMPT_WINDOW_SECONDS = 15 * 60
TOTP_LOCKOUT_SECONDS = 15 * 60


class TOTPAttemptRateLimiter:
    """Rate-limit TOTP attempts independently by user and operation."""

    def __init__(
        self,
        max_failed_attempts: int = TOTP_MAX_FAILED_ATTEMPTS,
        window_seconds: float = TOTP_ATTEMPT_WINDOW_SECONDS,
        lockout_seconds: float = TOTP_LOCKOUT_SECONDS,
        clock=None,
    ) -> None:
        kwargs = {
            "max_failed_attempts": max_failed_attempts,
            "window_seconds": window_seconds,
            "lockout_seconds": lockout_seconds,
        }

        if clock is not None:
            kwargs["clock"] = clock

        self._limiter = LoginRateLimiter(**kwargs)

    @staticmethod
    def _key(user_id: str, operation: str) -> str:
        """Build a namespaced key for a TOTP operation."""

        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("A valid user ID is required.")

        if operation not in {"enrolment", "verification"}:
            raise ValueError("Unsupported TOTP operation.")

        return f"totp:{operation}:{user_id.strip()}"

    def is_locked(self, user_id: str, operation: str) -> bool:
        """Check whether an operation is currently locked."""

        return self._limiter.is_locked(self._key(user_id, operation))

    def record_failure(self, user_id: str, operation: str) -> bool:
        """Record a failed attempt and return whether it caused lockout."""

        return self._limiter.record_failure(self._key(user_id, operation))

    def record_success(self, user_id: str, operation: str) -> None:
        """Clear the failed-attempt history after successful verification."""

        self._limiter.record_success(self._key(user_id, operation))


# Shared application-process limiter.
totp_attempt_limiter = TOTPAttemptRateLimiter()
