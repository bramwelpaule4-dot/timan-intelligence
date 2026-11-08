"""Allow completed subscription changes after scheduled downgrades are applied."""

from __future__ import annotations

from timan_intelligence.database.connection import get_database_type


VERSION = 12
NAME = "completed_subscription_changes"


def upgrade(connection) -> None:
    """Add a completed request state without losing historical requests."""
    if get_database_type() == "postgresql":
        connection.execute(
            """
            ALTER TABLE subscription_change_requests
            DROP CONSTRAINT subscription_change_requests_status_check
            """
        )
        connection.execute(
            """
            ALTER TABLE subscription_change_requests
            ADD CONSTRAINT subscription_change_requests_status_check
            CHECK (status IN (
                'pending', 'approved_pending_payment', 'scheduled',
                'rejected', 'canceled', 'completed'
            ))
            """
        )
        return

    connection.execute(
        """
        ALTER TABLE subscription_change_requests
        RENAME TO subscription_change_requests_v11
        """
    )
    connection.execute(
        """
        CREATE TABLE subscription_change_requests (
            id TEXT PRIMARY KEY,
            user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
            organisation_id TEXT REFERENCES organisations(id) ON DELETE CASCADE,
            requested_by TEXT NOT NULL REFERENCES users(id),
            current_plan_code TEXT NOT NULL,
            requested_plan_code TEXT NOT NULL,
            change_type TEXT NOT NULL
                CHECK (change_type IN ('upgrade', 'downgrade')),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN (
                    'pending', 'approved_pending_payment', 'scheduled',
                    'rejected', 'canceled', 'completed'
                )),
            effective_at TIMESTAMP,
            decision_notes TEXT,
            reviewed_by TEXT REFERENCES users(id),
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (
                (user_id IS NOT NULL AND organisation_id IS NULL)
                OR (user_id IS NULL AND organisation_id IS NOT NULL)
            ),
            CHECK (current_plan_code != requested_plan_code)
        )
        """
    )
    connection.execute(
        """
        INSERT INTO subscription_change_requests
        SELECT * FROM subscription_change_requests_v11
        """
    )
    connection.execute("DROP TABLE subscription_change_requests_v11")
    connection.execute(
        """
        CREATE INDEX idx_subscription_change_user_created
        ON subscription_change_requests(user_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_subscription_change_org_created
        ON subscription_change_requests(organisation_id, created_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_subscription_change_status_created
        ON subscription_change_requests(status, created_at)
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX uq_subscription_change_pending_user
        ON subscription_change_requests(user_id)
        WHERE user_id IS NOT NULL
          AND status IN ('pending', 'approved_pending_payment', 'scheduled')
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX uq_subscription_change_pending_org
        ON subscription_change_requests(organisation_id)
        WHERE organisation_id IS NOT NULL
          AND status IN ('pending', 'approved_pending_payment', 'scheduled')
        """
    )
