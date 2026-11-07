"""Persist individual and organisation subscription records."""

from __future__ import annotations


VERSION = 9
NAME = "subscriptions"


def upgrade(connection) -> None:
    """Create subscription history and enforce a single current record per owner."""

    connection.execute(
        """
        CREATE TABLE subscriptions (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            organisation_id TEXT
                REFERENCES organisations(id) ON DELETE CASCADE,
            plan_code TEXT NOT NULL
                CHECK (plan_code IN ('free', 'professional', 'enterprise')),
            status TEXT NOT NULL
                CHECK (status IN (
                    'trialing', 'active', 'past_due', 'canceled', 'expired'
                )),
            started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            current_period_start TIMESTAMP,
            current_period_end TIMESTAMP,
            cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
            canceled_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (
                (user_id IS NOT NULL AND organisation_id IS NULL)
                OR
                (user_id IS NULL AND organisation_id IS NOT NULL)
            ),
            CHECK (
                current_period_end IS NULL
                OR current_period_start IS NULL
                OR current_period_end > current_period_start
            )
        )
        """
    )

    connection.execute(
        """
        CREATE INDEX idx_subscriptions_user_history
        ON subscriptions(user_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_subscriptions_organisation_history
        ON subscriptions(organisation_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_subscriptions_status_period_end
        ON subscriptions(status, current_period_end)
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX uq_subscriptions_current_user
        ON subscriptions(user_id)
        WHERE user_id IS NOT NULL
          AND status IN ('trialing', 'active', 'past_due')
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX uq_subscriptions_current_organisation
        ON subscriptions(organisation_id)
        WHERE organisation_id IS NOT NULL
          AND status IN ('trialing', 'active', 'past_due')
        """
    )
