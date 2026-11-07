"""Tests for server-side feature and monthly usage enforcement."""

from __future__ import annotations

from datetime import date

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.entitlements.service import (
    DatasetLimitExceeded,
    FeatureAccessDenied,
    UsageLimitExceeded,
    consume_monthly_usage,
    get_monthly_usage,
    require_feature,
    validate_dataset_limits,
)
from timan_intelligence.entitlements.subscriptions import assign_subscription


@pytest.fixture
def entitlement_database(tmp_path, monkeypatch):
    path = tmp_path / "entitlements.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{path.as_posix()}")
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
            "INSERT INTO organisations (id, name) VALUES (?, ?)",
            ("org-1", "Organisation One"),
        )
        connection.execute(
            """
            INSERT INTO organisation_memberships (
                id, organisation_id, user_id, role, status
            ) VALUES (?, ?, ?, ?, ?)
            """,
            ("membership-1", "org-1", "user-1", "org_admin", "active"),
        )
    return path


def test_free_plan_allows_common_features_but_denies_professional_features(
    entitlement_database,
):
    assert require_feature("descriptive_statistics", user_id="user-1") == "free"
    with pytest.raises(FeatureAccessDenied):
        require_feature("hypothesis_testing", user_id="user-1")


def test_professional_subscription_grants_inferential_features(
    entitlement_database,
):
    assign_subscription(user_id="user-1", plan_code="professional")
    assert require_feature("hypothesis_testing", user_id="user-1") == "professional"


def test_monthly_analysis_quota_is_enforced_at_boundary(entitlement_database):
    for _ in range(100):
        consume_monthly_usage(
            "monthly_analyses",
            user_id="user-1",
            period_start=date(2026, 11, 1),
        )
    assert get_monthly_usage(
        "monthly_analyses",
        user_id="user-1",
        period_start="2026-11-21",
    ) == 100
    with pytest.raises(UsageLimitExceeded):
        consume_monthly_usage(
            "monthly_analyses",
            user_id="user-1",
            period_start=date(2026, 11, 1),
        )


def test_single_usage_request_cannot_exceed_empty_monthly_quota(entitlement_database):
    with pytest.raises(UsageLimitExceeded, match="single request"):
        consume_monthly_usage(
            "monthly_analyses",
            user_id="user-1",
            amount=101,
            period_start="2026-11-01",
        )

    assert get_monthly_usage(
        "monthly_analyses",
        user_id="user-1",
        period_start="2026-11-01",
    ) == 0


def test_usage_is_separated_by_calendar_month(entitlement_database):
    consume_monthly_usage(
        "monthly_exports",
        user_id="user-1",
        amount=3,
        period_start="2026-11-01",
    )
    assert get_monthly_usage(
        "monthly_exports",
        user_id="user-1",
        period_start="2026-11-30",
    ) == 3
    assert get_monthly_usage(
        "monthly_exports",
        user_id="user-1",
        period_start="2026-12-01",
    ) == 0


def test_organisation_subscription_usage_is_shared_by_members(
    entitlement_database,
):
    assign_subscription(organisation_id="org-1", plan_code="professional")
    assert consume_monthly_usage(
        "monthly_analyses",
        user_id="user-1",
        organisation_id="org-1",
        amount=2,
        period_start="2026-11-01",
    ) == 2
    assert get_monthly_usage(
        "monthly_analyses",
        organisation_id="org-1",
        period_start="2026-11-01",
    ) == 2


def test_enterprise_usage_is_unlimited(entitlement_database):
    assign_subscription(user_id="user-1", plan_code="enterprise")
    assert consume_monthly_usage(
        "monthly_analyses",
        user_id="user-1",
        amount=100_000,
        period_start="2026-11-01",
    ) == 100_000


def test_invalid_metric_and_amount_are_rejected(entitlement_database):
    with pytest.raises(ValueError):
        consume_monthly_usage("unknown_metric", user_id="user-1")
    with pytest.raises(ValueError):
        consume_monthly_usage("monthly_analyses", user_id="user-1", amount=0)


def test_free_dataset_upload_and_row_limits(entitlement_database):
    limits = validate_dataset_limits(
        user_id="user-1", file_size_bytes=25 * 1024 * 1024,
        row_count=10_000,
    )
    assert limits == {"max_upload_size_mb": 25, "max_dataset_rows": 10_000}
    with pytest.raises(DatasetLimitExceeded):
        validate_dataset_limits(
            user_id="user-1", file_size_bytes=25 * 1024 * 1024 + 1
        )
    with pytest.raises(DatasetLimitExceeded):
        validate_dataset_limits(user_id="user-1", row_count=10_001)


def test_professional_dataset_limits(entitlement_database):
    assign_subscription(user_id="user-1", plan_code="professional")
    validate_dataset_limits(
        user_id="user-1", file_size_bytes=250 * 1024 * 1024,
        row_count=250_000,
    )
    with pytest.raises(DatasetLimitExceeded):
        validate_dataset_limits(user_id="user-1", row_count=250_001)


def test_organisation_subscription_controls_dataset_limits(entitlement_database):
    assign_subscription(organisation_id="org-1", plan_code="professional")
    validate_dataset_limits(
        user_id="user-1",
        organisation_id="org-1",
        row_count=250_000,
        file_size_bytes=250 * 1024 * 1024,
    )
    with pytest.raises(DatasetLimitExceeded):
        validate_dataset_limits(
            user_id="user-1",
            organisation_id="org-1",
            row_count=250_001,
        )


def test_dataset_limits_reject_inactive_organisation_membership(entitlement_database):
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE organisation_memberships
            SET status = 'suspended'
            WHERE organisation_id = ? AND user_id = ?
            """,
            ("org-1", "user-1"),
        )
    with pytest.raises(Exception, match="active organisation membership"):
        validate_dataset_limits(
            user_id="user-1",
            organisation_id="org-1",
            row_count=1,
        )


def test_enterprise_dataset_limits_are_unlimited(entitlement_database):
    assign_subscription(user_id="user-1", plan_code="enterprise")
    validate_dataset_limits(
        user_id="user-1", file_size_bytes=500 * 1024 * 1024,
        row_count=1_000_000,
    )
