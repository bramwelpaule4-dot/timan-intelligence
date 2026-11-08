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


def _utc_datetime(value: str) -> datetime:
    """Parse an ISO timestamp and normalize it to timezone-aware UTC.

    Naive timestamps are interpreted as UTC for compatibility with existing
    records created by earlier versions of this service.
    """
    if not isinstance(value, str) or not value.strip():
        raise SubscriptionError("Subscription period values must be ISO timestamps.")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise SubscriptionError("Subscription periods must be ISO timestamps.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _validate_period(
    current_period_start: str | None,
    current_period_end: str | None,
) -> tuple[str | None, str | None]:
    """Validate and canonicalize period timestamps to UTC ISO-8601."""
    start = (
        _utc_datetime(current_period_start)
        if current_period_start is not None
        else None
    )
    end = (
        _utc_datetime(current_period_end)
        if current_period_end is not None
        else None
    )
    if start is not None and end is not None and end <= start:
        raise SubscriptionError("Subscription period end must be after its start.")
    return (
        start.isoformat(timespec="seconds") if start is not None else None,
        end.isoformat(timespec="seconds") if end is not None else None,
    )


def _validate_status(status: str) -> str:
    if not isinstance(status, str):
        raise SubscriptionError("Subscription status must be text.")
    value = status.strip().lower()
    if value not in SUBSCRIPTION_STATUSES:
        raise SubscriptionError("Unrecognised subscription status.")
    return value


def _is_period_expired(record: dict[str, Any]) -> bool:
    """Return whether the recorded paid/trial period has ended."""
    period_end = record.get("current_period_end")
    if period_end is None:
        return False
    try:
        return _utc_datetime(str(period_end)) <= datetime.now(timezone.utc)
    except SubscriptionError:
        # Invalid persisted dates must never grant continued entitlement.
        return True


def _normalise_subscription_record(row: Any) -> dict[str, Any]:
    """Return database rows with stable Python types across SQLite/PostgreSQL."""
    record = dict(row)
    record["cancel_at_period_end"] = bool(record.get("cancel_at_period_end", False))
    return record


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
    if not isinstance(cancel_at_period_end, bool):
        raise SubscriptionError("cancel_at_period_end must be boolean.")
    period_start, period_end = _validate_period(
        current_period_start,
        current_period_end,
    )

    subscription_id = str(uuid.uuid4())
    p = _placeholder()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

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
    """Return a current, unexpired subscription for exactly one owner.

    A subscription scheduled to cancel at period end remains effective until
    that period ends. Expired records remain in history and are not deleted.
    """
    owner_column, owner_id = _owner(user_id, organisation_id)
    p = _placeholder()
    with database_connection() as connection:
        row = connection.execute(
            f"""
            SELECT *
            FROM subscriptions
            WHERE {owner_column} = {p}
              AND status IN ('trialing', 'active', 'past_due')
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (owner_id,),
        ).fetchone()
    if row is None:
        return None
    record = _normalise_subscription_record(row)
    if _is_period_expired(record):
        return None
    return record


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
    return [_normalise_subscription_record(row) for row in rows]


def change_subscription_status(
    subscription_id: str,
    status: str,
) -> bool:
    """Change a subscription status without deleting its historical record."""
    if not isinstance(subscription_id, str) or not subscription_id.strip():
        raise SubscriptionError("A valid subscription ID is required.")
    canonical_status = _validate_status(status)
    p = _placeholder()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
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
    """Resolve an active member's organisation plan, then user plan, then Free.

    Supplying an organisation ID requires an active membership for the user.
    This prevents callers from resolving an organisation's subscription by
    guessing or supplying an unrelated organisation identifier.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise SubscriptionError("A valid user ID is required.")

    if organisation_id is not None:
        if not isinstance(organisation_id, str) or not organisation_id.strip():
            raise SubscriptionError("A valid organisation ID is required.")
        p = _placeholder()
        with database_connection() as connection:
            membership = connection.execute(
                f"""
                SELECT id
                FROM organisation_memberships
                WHERE user_id = {p}
                  AND organisation_id = {p}
                  AND status = 'active'
                LIMIT 1
                """,
                (user_id.strip(), organisation_id.strip()),
            ).fetchone()
        if membership is None:
            raise SubscriptionError(
                "An active organisation membership is required."
            )
        organisation_subscription = get_subscription(
            organisation_id=organisation_id
        )
        if organisation_subscription is not None:
            try:
                return get_plan(organisation_subscription["plan_code"]).code
            except (TypeError, ValueError) as exc:
                raise SubscriptionError(
                    "Stored organisation subscription plan is invalid."
                ) from exc

    user_subscription = get_subscription(user_id=user_id)
    if user_subscription is not None:
        try:
            return get_plan(user_subscription["plan_code"]).code
        except (TypeError, ValueError) as exc:
            raise SubscriptionError(
                "Stored individual subscription plan is invalid."
            ) from exc
    return "free"


def process_due_subscriptions(
    *,
    as_of: datetime | str | None = None,
    batch_size: int = 500,
) -> dict[str, int]:
    """Finalize due trials and subscriptions without extending paid periods.

    Trial periods become expired. Paid subscriptions become canceled when
    cancellation was scheduled for period end; otherwise they become expired.
    A renewal must only be applied after a payment provider confirms payment.
    This operation is idempotent and safe to run on every application startup.
    """
    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise SubscriptionError("batch_size must be a positive integer.")
    if not 1 <= batch_size <= 5000:
        raise SubscriptionError("batch_size must be between 1 and 5000.")

    if as_of is None:
        effective_now = datetime.now(timezone.utc)
    elif isinstance(as_of, datetime):
        effective_now = as_of
        if effective_now.tzinfo is None:
            effective_now = effective_now.replace(tzinfo=timezone.utc)
        effective_now = effective_now.astimezone(timezone.utc)
    elif isinstance(as_of, str):
        effective_now = _utc_datetime(as_of)
    else:
        raise SubscriptionError("as_of must be an ISO timestamp or datetime.")

    now_text = effective_now.isoformat(timespec="seconds")
    p = _placeholder()
    counts = {"canceled": 0, "expired": 0}

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT id, status, current_period_end, cancel_at_period_end
            FROM subscriptions
            WHERE status IN ('trialing', 'active', 'past_due')
              AND current_period_end IS NOT NULL
            ORDER BY current_period_end, id
            LIMIT {p}
            """,
            (batch_size,),
        ).fetchall()

        for row in rows:
            record = dict(row)
            try:
                due = _utc_datetime(str(record["current_period_end"])) <= effective_now
            except SubscriptionError:
                # A malformed persisted period must not grant entitlement.
                due = True
            if not due:
                continue

            target_status = (
                "canceled"
                if bool(record.get("cancel_at_period_end"))
                else "expired"
            )
            canceled_at = now_text if target_status == "canceled" else None
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
                  AND status IN ('trialing', 'active', 'past_due')
                """,
                (
                    target_status,
                    target_status,
                    canceled_at,
                    now_text,
                    record["id"],
                ),
            )
            if result.rowcount == 1:
                counts[target_status] += 1

    return counts


_PLAN_LEVELS = {"free": 0, "professional": 1, "enterprise": 2}
_PLAN_CHANGE_STATUSES = frozenset(
    {"pending", "approved_pending_payment", "scheduled", "rejected", "canceled"}
)


def request_plan_change(
    *,
    requested_by: str,
    requested_plan_code: str,
    user_id: str | None = None,
    organisation_id: str | None = None,
) -> str:
    """Create a customer request without changing current entitlements.

    Organisation requests require the requester to be an active member.
    Paid upgrades remain pending payment after approval; downgrades are
    scheduled for the current period end when that date is available.
    """
    owner_column, owner_id = _owner(user_id, organisation_id)
    if not isinstance(requested_by, str) or not requested_by.strip():
        raise SubscriptionError("A valid requesting user is required.")
    actor_id = requested_by.strip()
    try:
        requested_plan = get_plan(requested_plan_code).code
    except (TypeError, ValueError) as exc:
        raise SubscriptionError("Unrecognised requested plan.") from exc

    if owner_column == "user_id":
        if owner_id != actor_id:
            raise SubscriptionError("Users may only request changes to their own account.")
        current_plan = get_effective_plan_code(user_id=actor_id)
        current_subscription = get_subscription(user_id=actor_id)
    else:
        current_plan = get_effective_plan_code(
            user_id=actor_id,
            organisation_id=owner_id,
        )
        current_subscription = (
            get_subscription(organisation_id=owner_id)
            or get_subscription(user_id=actor_id)
        )

    if requested_plan == current_plan:
        raise SubscriptionError("The requested plan is already in effect.")
    change_type = (
        "upgrade"
        if _PLAN_LEVELS[requested_plan] > _PLAN_LEVELS[current_plan]
        else "downgrade"
    )
    effective_at = (
        current_subscription.get("current_period_end")
        if current_subscription
        else None
    )
    request_id = str(uuid.uuid4())
    p = _placeholder()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        with database_connection() as connection:
            actor = connection.execute(
                f"SELECT id FROM users WHERE id = {p}",
                (actor_id,),
            ).fetchone()
            if actor is None:
                raise SubscriptionError("The requesting account does not exist.")
            connection.execute(
                f"""
                INSERT INTO subscription_change_requests (
                    id, {owner_column}, requested_by, current_plan_code,
                    requested_plan_code, change_type, status, effective_at,
                    created_at, updated_at
                )
                VALUES ({p}, {p}, {p}, {p}, {p}, {p}, 'pending', {p}, {p}, {p})
                """,
                (
                    request_id, owner_id, actor_id, current_plan,
                    requested_plan, change_type, effective_at, now, now,
                ),
            )
    except SubscriptionError:
        raise
    except Exception as exc:
        # The partial unique index also protects against concurrent requests.
        raise SubscriptionError(
            "A pending plan-change request already exists for this workspace, "
            "or the request could not be saved."
        ) from exc
    return request_id


def list_plan_change_requests(
    *,
    user_id: str | None = None,
    organisation_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List plan-change requests for one owner or across the platform."""
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise SubscriptionError("limit must be between 1 and 1000.")
    if user_id is not None or organisation_id is not None:
        owner_column, owner_id = _owner(user_id, organisation_id)
    else:
        owner_column, owner_id = None, None
    canonical_status = None
    if status is not None:
        if not isinstance(status, str) or status.strip().lower() not in _PLAN_CHANGE_STATUSES:
            raise SubscriptionError("Unrecognised plan-change request status.")
        canonical_status = status.strip().lower()

    p = _placeholder()
    clauses, params = [], []
    if owner_column:
        clauses.append(f"requests.{owner_column} = {p}")
        params.append(owner_id)
    if canonical_status:
        clauses.append(f"requests.status = {p}")
        params.append(canonical_status)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT requests.*, users.email AS requester_email,
                   users.full_name AS requester_name
            FROM subscription_change_requests AS requests
            JOIN users ON users.id = requests.requested_by
            {where}
            ORDER BY requests.created_at DESC, requests.id DESC
            LIMIT {p}
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def review_plan_change_request(
    request_id: str,
    *,
    reviewer_id: str,
    decision: str,
    notes: str,
) -> str:
    """Approve or reject a request without bypassing payment or period rules."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise SubscriptionError("A valid request ID is required.")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise SubscriptionError("A valid reviewer account is required.")
    if not isinstance(notes, str) or not notes.strip() or len(notes.strip()) > 500:
        raise SubscriptionError("Decision notes are required (maximum 500 characters).")
    if decision not in {"approve", "reject"}:
        raise SubscriptionError("Decision must be approve or reject.")

    p = _placeholder()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database_connection() as connection:
        record = connection.execute(
            f"SELECT * FROM subscription_change_requests WHERE id = {p}",
            (request_id.strip(),),
        ).fetchone()
        if record is None:
            raise SubscriptionError("The plan-change request was not found.")
        record = dict(record)
        if record["status"] != "pending":
            raise SubscriptionError("Only pending requests can be reviewed.")
        reviewer = connection.execute(
            f"SELECT id, role FROM users WHERE id = {p} AND is_active = TRUE",
            (reviewer_id.strip(),),
        ).fetchone()
        if reviewer is None or reviewer["role"] not in {"admin", "super_admin"}:
            raise SubscriptionError("Platform administrator permission is required.")

        if decision == "reject":
            new_status = "rejected"
        elif record["change_type"] == "upgrade":
            new_status = "approved_pending_payment"
        else:
            new_status = "scheduled"

        effective_at = record.get("effective_at")
        if new_status == "scheduled" and not effective_at:
            # A Free-to-paid transition is an upgrade, so a downgrade without
            # a recorded paid period is not expected; require manual review.
            new_status = "scheduled"

        result = connection.execute(
            f"""
            UPDATE subscription_change_requests
            SET status = {p}, decision_notes = {p}, reviewed_by = {p},
                reviewed_at = {p}, updated_at = {p}
            WHERE id = {p} AND status = 'pending'
            """,
            (
                new_status, notes.strip(), reviewer_id.strip(),
                now, now, request_id.strip(),
            ),
        )
        if result.rowcount != 1:
            raise SubscriptionError("The request changed while it was being reviewed.")
    return new_status


def cancel_plan_change_request(
    request_id: str,
    *,
    requested_by: str,
) -> bool:
    """Allow only the original requester to withdraw a pending request."""
    if not isinstance(request_id, str) or not request_id.strip():
        raise SubscriptionError("A valid request ID is required.")
    if not isinstance(requested_by, str) or not requested_by.strip():
        raise SubscriptionError("A valid requesting user is required.")
    p = _placeholder()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with database_connection() as connection:
        result = connection.execute(
            f"""
            UPDATE subscription_change_requests
            SET status = 'canceled', updated_at = {p}
            WHERE id = {p} AND requested_by = {p} AND status = 'pending'
            """,
            (now, request_id.strip(), requested_by.strip()),
        )
    return result.rowcount == 1
