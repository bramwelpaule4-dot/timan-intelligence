"""Tests for database-backed TimanStat subscriptions."""

from __future__ import annotations

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
    assert sum(row["status"] in {"active", "trialing", "past_due"} for row in history) == 1


def test_organisation_subscription_is_separate_from_user_role(
    subscription_database,
):
    assign_subscription(organisation_id="org-1", plan_code="enterprise")
    assert get_effective_plan_code(
        user_id="user-1",
        organisation_id="org-1",
    ) == "enterprise"
    assert get_effective_plan_code(user_id="user-1") == "free"


def test_canceled_subscription_falls_back_to_free(subscription_database):
    subscription_id = assign_subscription(
        user_id="user-1",
        plan_code="professional",
    )
    assert change_subscription_status(subscription_id, "canceled") is True
    assert get_subscription(user_id="user-1") is None
    assert get_effective_plan_code(user_id="user-1") == "free"
    assert len(get_subscription_history(user_id="user-1")) == 1


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
