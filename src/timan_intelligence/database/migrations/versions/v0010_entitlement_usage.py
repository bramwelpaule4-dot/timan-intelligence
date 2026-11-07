"""Persist period-scoped subscription usage counters."""

from __future__ import annotations


VERSION = 10
NAME = "entitlement_usage"


def upgrade(connection) -> None:
    """Create monthly usage counters for individual and organisation owners."""

    connection.execute(
        """
        CREATE TABLE entitlement_usage (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            organisation_id TEXT
                REFERENCES organisations(id) ON DELETE CASCADE,
            metric TEXT NOT NULL
                CHECK (metric IN ('monthly_analyses', 'monthly_exports')),
            period_start DATE NOT NULL,
            usage_count INTEGER NOT NULL DEFAULT 0
                CHECK (usage_count >= 0),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (
                (user_id IS NOT NULL AND organisation_id IS NULL)
                OR
                (user_id IS NULL AND organisation_id IS NOT NULL)
            ),
            UNIQUE (user_id, metric, period_start),
            UNIQUE (organisation_id, metric, period_start)
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_entitlement_usage_user_period
        ON entitlement_usage(user_id, period_start)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_entitlement_usage_organisation_period
        ON entitlement_usage(organisation_id, period_start)
        """
    )
