"""Database-backed subscription assignment and lookup services.

Subscription entitlements are independent of authentication and RBAC roles.
No payment-provider integration or client-controlled plan assignment is
performed by this module.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.entitlements.plans import get_plan


SUBSCRIPTION_STATUSES = frozenset(
    {"trialing", "active", "past_due", "canceled", "expired"}
)
CURRENT_STATUSES = ("trialing", "active", "past_due")


class SubscriptionError(ValueError):
    """Raised when a subscription operation is invalid."""


def _placeholder() -> str:
    return "%s" if get_database_type() == "postgresql" else "?"


def _owner(user_id: str | None, organisation_id: str | None) -> tuple[str, str]:
    """Require exactly one valid subscription owner."""
    has_user = isinstance(user_id, str) and bool(user_id.strip())
    has_organisation = (
        isinstance(organisation_id, str) and bool(organisation_id.strip())
    )
    if has_user == has_organisation:
        raise SubscriptionError(
            "Provide exactly one user ID or organisation ID."
        )
    if has_user:
        return "user_id", user_id.strip()
    return "organisation_id", organisation_id.strip()


def _validate_status(status: str) -> str:
    if not isinstance(status, str):
        raise SubscriptionError("Subscription status must be text.")
    value = status.strip().lower()
    if value not in SUBSCRIPTION_STATUSES:
        raise SubscriptionError("Unrecognised subscription status.")
    return value


def _validate_period(
    current_period_start: str | None,
    current_period_end: str | None,
) -> tuple[str | None, str | None]:
    for value in (current_period_start, current_period_end):
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise SubscriptionError("Subscription period values must be ISO timestamps.")
            try:
                datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            except ValueError as exc:
                raise SubscriptionError("Subscription periods must be ISO timestamps.") from exc
    if current_period_start and current_period_end:
        start = datetime.fromisoformat(current_period_start.replace("Z", "+00:00"))
        end = datetime.fromisoformat(current_period_end.replace("Z", "+00:00"))
        if end <= start:
            raise SubscriptionError("Subscription period end must be after its start.")
    return current_period_start, current_period_end


def assign_subscription(
    *,
    plan_code: str,
    user_id: str | None = None,
    organisation_id: str | None = None,
    status: str = "active",
    current_period_start: str | None = None,
    current_period_end: str | None = None,
    cancel_at_period_end: bool = False,
) -> str:
    """Assign a plan and retain any previous subscription as history.

    This is an internal service operation. Callers must enforce administrative
    authorization before exposing paid-plan assignment through an interface.
    """
    owner_column, owner_id = _owner(user_id, organisation_id)
    try:
        canonical_plan = get_plan(plan_code).code
    except (TypeError, ValueError) as exc:
        raise SubscriptionError("Unrecognised subscription plan.") from exc

    canonical_status = _validate_status(status)
    if isinstance(cancel_at_period_end, bool) is False:
        raise SubscriptionError("cancel_at_period_end must be boolean.")
    period_start, period_end = _validate_period(
        current_period_start,
        current_period_end,
    )

    subscription_id = str(uuid.uuid4())
    p = _placeholder()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
        timespec="seconds"
    )

    with database_connection() as connection:
        owner_table = "users" if owner_column == "user_id" else "organisations"
        owner = connection.execute(
            f"SELECT id FROM {owner_table} WHERE id = {p}",
            (owner_id,),
        ).fetchone()
        if owner is None:
            raise SubscriptionError("Subscription owner does not exist.")

        connection.execute(
            f"""
            UPDATE subscriptions
            SET status = 'canceled',
                canceled_at = {p},
                updated_at = {p}
            WHERE {owner_column} = {p}
              AND status IN ('trialing', 'active', 'past_due')
            """,
            (now, now, owner_id),
        )
        connection.execute(
            f"""
            INSERT INTO subscriptions (
                id, {owner_column}, plan_code, status,
                started_at, current_period_start, current_period_end,
                cancel_at_period_end
            )
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
            """,
            (
                subscription_id,
                owner_id,
                canonical_plan,
                canonical_status,
                now,
                period_start,
                period_end,
                cancel_at_period_end,
            ),
        )

    return subscription_id


def get_subscription(
    *,
    user_id: str | None = None,
    organisation_id: str | None = None,
) -> dict[str, Any] | None:
    """Return the current subscription for exactly one owner, if present."""
    owner_column, owner_id = _owner(user_id, organisation_id)
    p = _placeholder()
    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT *
            FROM subscriptions
            WHERE {owner_column} = {p}
              AND status IN ('trialing', 'active', 'past_due')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (owner_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def get_subscription_history(
    *,
    user_id: str | None = None,
    organisation_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return all subscription records for one owner, newest first."""
    owner_column, owner_id = _owner(user_id, organisation_id)
    p = _placeholder()
    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM subscriptions
            WHERE {owner_column} = {p}
            ORDER BY created_at DESC, id DESC
            """,
            (owner_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def change_subscription_status(
    subscription_id: str,
    status: str,
) -> bool:
    """Change a subscription status without deleting its historical record."""
    if not isinstance(subscription_id, str) or not subscription_id.strip():
        raise SubscriptionError("A valid subscription ID is required.")
    canonical_status = _validate_status(status)
    p = _placeholder()
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
        timespec="seconds"
    )
    canceled_at = now if canonical_status == "canceled" else None
    with database_connection() as connection:
        result = connection.execute(
            f"""
            UPDATE subscriptions
            SET status = {p},
                canceled_at = CASE
                    WHEN {p} = 'canceled' THEN {p}
                    ELSE canceled_at
                END,
                updated_at = {p}
            WHERE id = {p}
            """,
            (
                canonical_status,
                canonical_status,
                canceled_at,
                now,
                subscription_id.strip(),
            ),
        )
    return result.rowcount == 1


def get_effective_plan_code(
    *,
    user_id: str,
    organisation_id: str | None = None,
) -> str:
    """Resolve organisation plan first, then user plan, then safe Free default."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise SubscriptionError("A valid user ID is required.")
    if organisation_id is not None:
        organisation_subscription = get_subscription(
            organisation_id=organisation_id
        )
        if organisation_subscription is not None:
            return get_plan(organisation_subscription["plan_code"]).code
    user_subscription = get_subscription(user_id=user_id)
    if user_subscription is not None:
        return get_plan(user_subscription["plan_code"]).code
    return "free"
