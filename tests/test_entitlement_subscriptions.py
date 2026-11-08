"""Tests for database-backed TimanStat subscriptions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.entitlements.subscriptions import (
    SubscriptionError,
    assign_subscription,
    change_subscription_status,
    get_effective_plan_code,
    get_subscription,
    get_subscription_history,
    process_due_subscriptions,
    request_plan_change,
    list_plan_change_requests,
    review_plan_change_request,
    cancel_plan_change_request,
)


@pytest.fixture
def subscription_database(tmp_path, monkeypatch):
    database_path = tmp_path / "subscriptions.db"
    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )
    initialise_database()
    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (id, username, email, full_name, password_hash)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("user-1", "user1", "user1@example.com", "User One", "hash"),
        )
        connection.execute(
            """
            INSERT INTO organisations (id, name)
            VALUES (?, ?)
            """,
            ("org-1", "Organisation One"),
        )
        connection.execute(
            """
            INSERT INTO organisation_memberships (
                id, organisation_id, user_id, role, status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            ("membership-1", "org-1", "user-1", "org_member", "active"),
        )
    return database_path


def test_user_without_subscription_defaults_to_free(subscription_database):
    assert get_subscription(user_id="user-1") is None
    assert get_effective_plan_code(user_id="user-1") == "free"


def test_assign_and_retrieve_individual_subscription(subscription_database):
    subscription_id = assign_subscription(
        user_id="user-1",
        plan_code="professional",
        status="active",
        current_period_start="2026-11-01T00:00:00",
        current_period_end="2026-12-01T00:00:00",
    )
    record = get_subscription(user_id="user-1")
    assert record is not None
    assert record["id"] == subscription_id
    assert record["plan_code"] == "professional"
    assert record["status"] == "active"
    assert get_effective_plan_code(user_id="user-1") == "professional"


def test_reassignment_preserves_history_and_only_one_current_record(
    subscription_database,
):
    first = assign_subscription(user_id="user-1", plan_code="professional")
    second = assign_subscription(user_id="user-1", plan_code="enterprise")
    history = get_subscription_history(user_id="user-1")
    assert len(history) == 2
    assert {row["id"] for row in history} == {first, second}
    assert get_subscription(user_id="user-1")["id"] == second
    assert sum(
        row["status"] in {"active", "trialing", "past_due"}
        for row in history
    ) == 1


def test_organisation_subscription_requires_active_membership(
    subscription_database,
):
    assign_subscription(organisation_id="org-1", plan_code="enterprise")
    assert get_effective_plan_code(
        user_id="user-1",
        organisation_id="org-1",
    ) == "enterprise"
    assert get_effective_plan_code(user_id="user-1") == "free"

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE organisation_memberships
            SET status = 'suspended'
            WHERE id = ?
            """,
            ("membership-1",),
        )
    with pytest.raises(SubscriptionError, match="active organisation membership"):
        get_effective_plan_code(user_id="user-1", organisation_id="org-1")


def test_canceled_subscription_falls_back_to_free(subscription_database):
    subscription_id = assign_subscription(
        user_id="user-1",
        plan_code="professional",
    )
    assert change_subscription_status(subscription_id, "canceled") is True
    assert get_subscription(user_id="user-1") is None
    assert get_effective_plan_code(user_id="user-1") == "free"
    assert len(get_subscription_history(user_id="user-1")) == 1


def test_expired_period_does_not_grant_entitlement(subscription_database):
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    earlier = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    assign_subscription(
        user_id="user-1",
        plan_code="professional",
        current_period_start=earlier,
        current_period_end=yesterday,
    )
    assert get_subscription(user_id="user-1") is None
    assert get_effective_plan_code(user_id="user-1") == "free"
    assert len(get_subscription_history(user_id="user-1")) == 1


def test_cancel_at_period_end_remains_effective_until_expiry(
    subscription_database,
):
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    start = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    assign_subscription(
        user_id="user-1",
        plan_code="professional",
        current_period_start=start,
        current_period_end=future,
        cancel_at_period_end=True,
    )
    record = get_subscription(user_id="user-1")
    assert record is not None
    assert record["cancel_at_period_end"] is True
    assert get_effective_plan_code(user_id="user-1") == "professional"


def test_mixed_timezone_periods_are_normalized_and_compared(
    subscription_database,
):
    subscription_id = assign_subscription(
        user_id="user-1",
        plan_code="professional",
        current_period_start="2026-11-01T00:00:00-05:00",
        current_period_end="2026-12-01T00:00:00Z",
    )
    record = get_subscription(user_id="user-1")
    assert record is not None
    assert record["id"] == subscription_id
    assert record["current_period_start"].endswith("+00:00")
    assert record["current_period_end"].endswith("+00:00")


def test_unknown_plan_and_invalid_owner_are_rejected(subscription_database):
    with pytest.raises(SubscriptionError):
        assign_subscription(user_id="user-1", plan_code="unlisted")
    with pytest.raises(SubscriptionError):
        assign_subscription(
            user_id="user-1",
            organisation_id="org-1",
            plan_code="free",
        )
    with pytest.raises(SubscriptionError):
        assign_subscription(plan_code="free")


def test_subscription_owner_and_period_constraints_are_enforced(
    subscription_database,
):
    with database_connection() as connection:
        with pytest.raises(Exception):
            connection.execute(
                """
                INSERT INTO subscriptions (
                    id, user_id, organisation_id, plan_code, status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                ("bad-owner", "user-1", "org-1", "free", "active"),
            )
    with pytest.raises(SubscriptionError):
        assign_subscription(
            user_id="user-1",
            plan_code="free",
            current_period_start="2026-12-01T00:00:00",
            current_period_end="2026-11-01T00:00:00",
        )



def test_due_trial_is_expired_and_history_is_preserved(subscription_database):
    now = datetime.now(timezone.utc)
    trial_id = assign_subscription(
        user_id="user-1",
        plan_code="professional",
        status="trialing",
        current_period_start=(now - timedelta(days=8)).isoformat(),
        current_period_end=(now - timedelta(days=1)).isoformat(),
    )
    assert process_due_subscriptions(as_of=now) == {"canceled": 0, "expired": 1}
    history = get_subscription_history(user_id="user-1")
    assert history[0]["id"] == trial_id
    assert history[0]["status"] == "expired"
    assert get_effective_plan_code(user_id="user-1") == "free"


def test_due_paid_subscription_obeys_period_end_cancellation(subscription_database):
    now = datetime.now(timezone.utc)
    assign_subscription(
        user_id="user-1",
        plan_code="professional",
        status="active",
        current_period_start=(now - timedelta(days=31)).isoformat(),
        current_period_end=(now - timedelta(seconds=1)).isoformat(),
        cancel_at_period_end=True,
    )
    assert process_due_subscriptions(as_of=now) == {"canceled": 1, "expired": 0}
    record = get_subscription_history(user_id="user-1")[0]
    assert record["status"] == "canceled"
    assert record["canceled_at"] is not None
    assert record["cancel_at_period_end"] is True


def test_due_paid_subscription_without_renewal_becomes_expired(subscription_database):
    now = datetime.now(timezone.utc)
    assign_subscription(
        user_id="user-1",
        plan_code="professional",
        status="active",
        current_period_start=(now - timedelta(days=31)).isoformat(),
        current_period_end=(now - timedelta(seconds=1)).isoformat(),
    )
    assert process_due_subscriptions(as_of=now) == {"canceled": 0, "expired": 1}
    record = get_subscription_history(user_id="user-1")[0]
    assert record["status"] == "expired"
    assert record["canceled_at"] is None


def test_lifecycle_processing_is_idempotent_and_leaves_future_periods_unchanged(
    subscription_database,
):
    now = datetime.now(timezone.utc)
    due_id = assign_subscription(
        user_id="user-1",
        plan_code="professional",
        current_period_end=(now - timedelta(seconds=1)).isoformat(),
    )
    future_id = assign_subscription(
        organisation_id="org-1",
        plan_code="enterprise",
        current_period_end=(now + timedelta(days=5)).isoformat(),
    )
    assert process_due_subscriptions(as_of=now) == {"canceled": 0, "expired": 1}
    assert process_due_subscriptions(as_of=now) == {"canceled": 0, "expired": 0}
    due_record = get_subscription_history(user_id="user-1")[0]
    assert due_record["id"] == due_id
    assert due_record["status"] == "expired"
    assert get_subscription(organisation_id="org-1")["id"] == future_id


@pytest.mark.parametrize("batch_size", [0, -1, 5001, True, 1.5])
def test_lifecycle_rejects_invalid_batch_size(subscription_database, batch_size):
    with pytest.raises(SubscriptionError):
        process_due_subscriptions(batch_size=batch_size)


def test_customer_upgrade_request_does_not_change_entitlements(subscription_database):
    request_id = request_plan_change(
        requested_by="user-1",
        requested_plan_code="professional",
        user_id="user-1",
    )
    request = list_plan_change_requests(user_id="user-1")[0]
    assert request["id"] == request_id
    assert request["change_type"] == "upgrade"
    assert request["status"] == "pending"
    assert get_effective_plan_code(user_id="user-1") == "free"


def test_only_one_pending_plan_change_per_owner(subscription_database):
    request_plan_change(
        requested_by="user-1",
        requested_plan_code="professional",
        user_id="user-1",
    )
    with pytest.raises(SubscriptionError, match="pending plan-change"):
        request_plan_change(
            requested_by="user-1",
            requested_plan_code="enterprise",
            user_id="user-1",
        )


def test_approved_upgrade_waits_for_payment_and_preserves_free_access(
    subscription_database,
):
    request_id = request_plan_change(
        requested_by="user-1",
        requested_plan_code="professional",
        user_id="user-1",
    )
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users SET role = 'admin' WHERE id = ?
            """,
            ("user-1",),
        )
    status = review_plan_change_request(
        request_id,
        reviewer_id="user-1",
        decision="approve",
        notes="Approved subject to successful payment.",
    )
    assert status == "approved_pending_payment"
    assert get_effective_plan_code(user_id="user-1") == "free"
    assert list_plan_change_requests(user_id="user-1")[0]["status"] == status


def test_approved_downgrade_is_scheduled_at_current_period_end(
    subscription_database,
):
    now = datetime.now(timezone.utc)
    period_end = (now + timedelta(days=10)).replace(microsecond=0)
    assign_subscription(
        user_id="user-1",
        plan_code="professional",
        status="active",
        current_period_start=(now - timedelta(days=20)).isoformat(),
        current_period_end=period_end.isoformat(),
    )
    request_id = request_plan_change(
        requested_by="user-1",
        requested_plan_code="free",
        user_id="user-1",
    )
    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET role = 'admin' WHERE id = ?",
            ("user-1",),
        )
    status = review_plan_change_request(
        request_id,
        reviewer_id="user-1",
        decision="approve",
        notes="Downgrade approved for period end.",
    )
    assert status == "scheduled"
    request = list_plan_change_requests(user_id="user-1")[0]
    assert request["effective_at"] == period_end.isoformat()
    assert get_effective_plan_code(user_id="user-1") == "professional"


def test_rejected_and_withdrawn_requests_are_retained(subscription_database):
    rejected_id = request_plan_change(
        requested_by="user-1",
        requested_plan_code="professional",
        user_id="user-1",
    )
    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET role = 'admin' WHERE id = ?",
            ("user-1",),
        )
    assert review_plan_change_request(
        rejected_id,
        reviewer_id="user-1",
        decision="reject",
        notes="Request requires further information.",
    ) == "rejected"
    next_id = request_plan_change(
        requested_by="user-1",
        requested_plan_code="enterprise",
        user_id="user-1",
    )
    assert cancel_plan_change_request(next_id, requested_by="user-1") is True
    assert cancel_plan_change_request(next_id, requested_by="user-1") is False
    assert {row["status"] for row in list_plan_change_requests(user_id="user-1")} == {
        "rejected", "canceled"
    }


def test_organisation_plan_change_requires_active_membership(subscription_database):
    with database_connection() as connection:
        connection.execute(
            "UPDATE organisation_memberships SET status = 'suspended' WHERE id = ?",
            ("membership-1",),
        )
    with pytest.raises(SubscriptionError, match="active organisation membership"):
        request_plan_change(
            requested_by="user-1",
            requested_plan_code="professional",
            organisation_id="org-1",
        )
    with database_connection() as connection:
        connection.execute(
            "UPDATE organisation_memberships SET status = 'active' WHERE id = ?",
            ("membership-1",),
        )
    request_id = request_plan_change(
        requested_by="user-1",
        requested_plan_code="professional",
        organisation_id="org-1",
    )
    request = list_plan_change_requests(organisation_id="org-1")[0]
    assert request["id"] == request_id
    assert request["change_type"] == "upgrade"
