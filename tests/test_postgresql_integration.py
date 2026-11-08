"""PostgreSQL integration tests for TimanStat."""

from __future__ import annotations

import os

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.database.migrations.runner import (
    LATEST_SCHEMA_VERSION,
    _validate_existing_schema,
)


EXPECTED_MIGRATION_HISTORY = [
    (1, "initial_schema"),
    (2, "totp_enrolment"),
    (3, "email_verification"),
    (4, "password_reset"),
    (5, "session_version"),
    (6, "totp_recovery_codes"),
    (7, "distributed_rate_limits"),
    (8, "rate_limit_timestamp_precision"),
    (9, "subscriptions"),
    (10, "entitlement_usage"),
    (11, "subscription_change_requests"),
    (12, "completed_subscription_changes"),
    (13, "billing_records"),
    (14, "billing_invoice_item_order"),
]


@pytest.fixture(scope="session")
def postgres_database():
    """Configure and initialise an isolated PostgreSQL test database."""

    database_url = os.getenv("TIMANSTAT_TEST_POSTGRES_URL", "").strip()

    if not database_url:
        pytest.skip(
            "PostgreSQL integration tests require "
            "TIMANSTAT_TEST_POSTGRES_URL."
        )

    if not database_url.startswith(("postgresql://", "postgres://")):
        pytest.fail(
            "TIMANSTAT_TEST_POSTGRES_URL must be a PostgreSQL URL."
        )

    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault(
        "TIMANSTAT_RATE_LIMIT_HMAC_KEY",
        "test-only-timanstat-rate-limit-hmac-key-32-bytes-minimum",
    )

    initialise_database()

    yield database_url


def test_postgresql_connection_is_available(postgres_database):
    """PostgreSQL should accept and execute database queries."""

    with database_connection() as connection:
        result = connection.execute("SELECT 1 AS value").fetchone()

    assert result["value"] == 1


def test_postgresql_migrations_are_recorded(postgres_database):
    """All registered schema migrations should be recorded correctly."""

    with database_connection() as connection:
        history = connection.execute(
            """
            SELECT version, name
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()

    assert [
        (row["version"], row["name"])
        for row in history
    ] == EXPECTED_MIGRATION_HISTORY

    assert history[-1]["version"] == LATEST_SCHEMA_VERSION

    with database_connection() as connection:
        columns = connection.execute(
            """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'users'
            """
        ).fetchall()

        verification_table = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = 'email_verification_tokens'
              AND table_type = 'BASE TABLE'
            """
        ).fetchone()

    actual_columns = {
        row["column_name"]: row
        for row in columns
    }

    expected_totp_columns = {
        "totp_enabled",
        "totp_secret_encrypted",
        "totp_pending_secret_encrypted",
        "totp_last_accepted_counter",
        "totp_enrolled_at",
        "totp_pending_created_at",
    }

    assert expected_totp_columns.issubset(actual_columns)
    assert "session_version" in actual_columns

    session_version_column = actual_columns["session_version"]

    assert session_version_column["data_type"] == "integer"
    assert session_version_column["is_nullable"] == "NO"
    assert session_version_column["column_default"] == "0"

    assert verification_table is not None

    with database_connection() as connection:
        rate_limit_timestamp_columns = connection.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'rate_limit_states'
              AND column_name IN ('window_started_at', 'locked_until')
            """
        ).fetchall()
    assert {row["column_name"]: row["data_type"] for row in rate_limit_timestamp_columns} == {
        "window_started_at": "double precision",
        "locked_until": "double precision",
    }

    with database_connection() as connection:
        recovery_table = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_name = 'totp_recovery_codes'
              AND table_type = 'BASE TABLE'
            """
        ).fetchone()

    assert recovery_table is not None


def test_postgresql_schema_contains_required_tables(postgres_database):
    """All required application tables should exist."""

    expected_tables = {
        "users",
        "organisations",
        "organisation_memberships",
        "projects",
        "project_memberships",
        "audit_logs",
        "schema_migrations",
        "email_verification_tokens",
        "password_reset_tokens",
        "totp_recovery_codes",
        "rate_limit_states",
        "subscriptions",
        "entitlement_usage",
        "subscription_change_requests",
        "billing_invoices",
        "billing_invoice_items",
        "payment_transactions",
        "billing_events",
    }

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_type = 'BASE TABLE'
            """
        ).fetchall()

    actual_tables = {row["table_name"] for row in rows}

    assert expected_tables.issubset(actual_tables)


def test_postgresql_existing_schema_passes_structural_validation(
    postgres_database,
):
    """The PostgreSQL schema should pass all migration validations."""

    with database_connection() as connection:
        _validate_existing_schema(connection)


def test_postgresql_migration_is_idempotent(postgres_database):
    """Repeated initialisation must not duplicate migrations."""

    initialise_database()
    initialise_database()

    with database_connection() as connection:
        history = connection.execute(
            """
            SELECT version, name
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()

    assert [
        (row["version"], row["name"])
        for row in history
    ] == EXPECTED_MIGRATION_HISTORY

    assert history[-1]["version"] == LATEST_SCHEMA_VERSION


def test_postgresql_enforces_user_role_check_constraint(
    postgres_database,
):
    """PostgreSQL should reject user roles outside the allowed values."""

    from psycopg.errors import CheckViolation

    with pytest.raises(CheckViolation):
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    id,
                    username,
                    email,
                    full_name,
                    password_hash,
                    role
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    "postgres-invalid-role-test",
                    "postgres_invalid_role",
                    "postgres_invalid_role@example.com",
                    "Invalid Role Test",
                    "test-hash",
                    "invalid_role",
                ),
            )


def test_postgresql_enforces_membership_foreign_keys(postgres_database):
    """PostgreSQL should reject membership references to missing records."""

    from psycopg.errors import ForeignKeyViolation

    with pytest.raises(ForeignKeyViolation):
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO organisation_memberships (
                    id,
                    organisation_id,
                    user_id
                )
                VALUES (%s, %s, %s)
                """,
                (
                    "postgres-invalid-membership-test",
                    "missing-organisation",
                    "missing-user",
                ),
            )


def test_postgresql_enforces_organisation_membership_uniqueness(
    postgres_database,
):
    """A user cannot have duplicate memberships in one organisation."""

    from psycopg.errors import UniqueViolation

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                id, username, email, full_name, password_hash
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                "pg-unique-org-user",
                "pg_unique_org_user",
                "pg_unique_org_user@example.com",
                "PostgreSQL Unique Test",
                "test-hash",
            ),
        )

        connection.execute(
            """
            INSERT INTO organisations (id, name)
            VALUES (%s, %s)
            """,
            (
                "pg-unique-org",
                "PostgreSQL Unique Test Organisation",
            ),
        )

        connection.execute(
            """
            INSERT INTO organisation_memberships (
                id, organisation_id, user_id
            )
            VALUES (%s, %s, %s)
            """,
            (
                "pg-unique-org-membership-1",
                "pg-unique-org",
                "pg-unique-org-user",
            ),
        )

    with pytest.raises(UniqueViolation):
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO organisation_memberships (
                    id, organisation_id, user_id
                )
                VALUES (%s, %s, %s)
                """,
                (
                    "pg-unique-org-membership-2",
                    "pg-unique-org",
                    "pg-unique-org-user",
                ),
            )


def test_postgresql_enforces_project_membership_uniqueness(
    postgres_database,
):
    """A user cannot have duplicate memberships in one project."""

    from psycopg.errors import UniqueViolation

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                id, username, email, full_name, password_hash
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                "pg-unique-project-user",
                "pg_unique_project_user",
                "pg_unique_project_user@example.com",
                "PostgreSQL Project Test",
                "test-hash",
            ),
        )

        connection.execute(
            """
            INSERT INTO organisations (id, name)
            VALUES (%s, %s)
            """,
            (
                "pg-unique-project-org",
                "PostgreSQL Project Test Organisation",
            ),
        )

        connection.execute(
            """
            INSERT INTO projects (
                id, organisation_id, name
            )
            VALUES (%s, %s, %s)
            """,
            (
                "pg-unique-project",
                "pg-unique-project-org",
                "PostgreSQL Unique Test Project",
            ),
        )

        connection.execute(
            """
            INSERT INTO project_memberships (
                id, project_id, user_id
            )
            VALUES (%s, %s, %s)
            """,
            (
                "pg-unique-project-membership-1",
                "pg-unique-project",
                "pg-unique-project-user",
            ),
        )

    with pytest.raises(UniqueViolation):
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO project_memberships (
                    id, project_id, user_id
                )
                VALUES (%s, %s, %s)
                """,
                (
                    "pg-unique-project-membership-2",
                    "pg-unique-project",
                    "pg-unique-project-user",
                ),
            )


def test_postgresql_enforces_foreign_key_delete_behaviour(
    postgres_database,
):
    """PostgreSQL should enforce CASCADE and SET NULL delete actions."""

    with database_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                id, username, email, full_name, password_hash
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                "pg-delete-test-user",
                "pg_delete_test_user",
                "pg_delete_test_user@example.com",
                "PostgreSQL Delete Test",
                "test-hash",
            ),
        )

        connection.execute(
            """
            INSERT INTO organisations (id, name)
            VALUES (%s, %s)
            """,
            (
                "pg-delete-test-org",
                "PostgreSQL Delete Test Organisation",
            ),
        )

        connection.execute(
            """
            INSERT INTO organisation_memberships (
                id, organisation_id, user_id
            )
            VALUES (%s, %s, %s)
            """,
            (
                "pg-delete-test-org-membership",
                "pg-delete-test-org",
                "pg-delete-test-user",
            ),
        )

        connection.execute(
            """
            INSERT INTO projects (
                id, organisation_id, name, created_by
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                "pg-delete-test-project",
                "pg-delete-test-org",
                "PostgreSQL Delete Test Project",
                "pg-delete-test-user",
            ),
        )

        connection.execute(
            """
            INSERT INTO project_memberships (
                id, project_id, user_id
            )
            VALUES (%s, %s, %s)
            """,
            (
                "pg-delete-test-project-membership",
                "pg-delete-test-project",
                "pg-delete-test-user",
            ),
        )

        connection.execute(
            """
            INSERT INTO audit_logs (
                id, user_id, organisation_id, action
            )
            VALUES (%s, %s, %s, %s)
            """,
            (
                "pg-delete-test-audit",
                "pg-delete-test-user",
                "pg-delete-test-org",
                "delete_test",
            ),
        )

    with database_connection() as connection:
        connection.execute(
            "DELETE FROM users WHERE id = %s",
            ("pg-delete-test-user",),
        )

        org_membership = connection.execute(
            """
            SELECT id FROM organisation_memberships WHERE id = %s
            """,
            ("pg-delete-test-org-membership",),
        ).fetchone()

        project_membership = connection.execute(
            """
            SELECT id FROM project_memberships WHERE id = %s
            """,
            ("pg-delete-test-project-membership",),
        ).fetchone()

        project = connection.execute(
            """
            SELECT created_by FROM projects WHERE id = %s
            """,
            ("pg-delete-test-project",),
        ).fetchone()

        audit = connection.execute(
            """
            SELECT user_id, organisation_id
            FROM audit_logs
            WHERE id = %s
            """,
            ("pg-delete-test-audit",),
        ).fetchone()

    assert org_membership is None
    assert project_membership is None
    assert project["created_by"] is None
    assert audit["user_id"] is None
    assert audit["organisation_id"] == "pg-delete-test-org"

    with database_connection() as connection:
        connection.execute(
            "DELETE FROM organisations WHERE id = %s",
            ("pg-delete-test-org",),
        )

        project = connection.execute(
            """
            SELECT id FROM projects WHERE id = %s
            """,
            ("pg-delete-test-project",),
        ).fetchone()

        audit = connection.execute(
            """
            SELECT organisation_id
            FROM audit_logs
            WHERE id = %s
            """,
            ("pg-delete-test-audit",),
        ).fetchone()

    assert project is None
    assert audit["organisation_id"] is None


def test_postgresql_transaction_rolls_back_all_changes_on_failure(
    postgres_database,
):
    """A failed operation must roll back earlier writes in its transaction."""

    from psycopg.errors import UniqueViolation

    test_user_id = "pg-rollback-test-user"

    with pytest.raises(UniqueViolation):
        with database_connection() as connection:
            connection.execute(
                """
                INSERT INTO users (
                    id,
                    username,
                    email,
                    full_name,
                    password_hash
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    test_user_id,
                    "pg_rollback_test_user",
                    "pg_rollback_test_user@example.com",
                    "PostgreSQL Rollback Test",
                    "test-hash",
                ),
            )

            connection.execute(
                """
                INSERT INTO users (
                    id,
                    username,
                    email,
                    full_name,
                    password_hash
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    "pg-rollback-duplicate-user",
                    "pg_rollback_test_user",
                    "pg_rollback_duplicate@example.com",
                    "Duplicate User",
                    "test-hash",
                ),
            )

    with database_connection() as connection:
        result = connection.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
            """,
            (test_user_id,),
        ).fetchone()

    assert result is None


def test_postgresql_rate_limiter_shares_state_between_instances(
    postgres_database,
):
    """Independent application workers should share PostgreSQL limits."""

    import uuid

    from timan_intelligence.security.distributed_rate_limit import (
        DatabaseRateLimiter,
    )

    scope = f"postgres-integration-{uuid.uuid4()}"
    first = DatabaseRateLimiter(
        scope=scope,
        max_failed_attempts=1,
        window_seconds=60,
        lockout_seconds=60,
    )
    second = DatabaseRateLimiter(
        scope=scope,
        max_failed_attempts=1,
        window_seconds=60,
        lockout_seconds=60,
    )

    assert first.consume_attempt("worker-test@example.com") is True
    assert second.consume_attempt("worker-test@example.com") is False

    failure_scope = f"postgres-failure-{uuid.uuid4()}"
    failure_limiter = DatabaseRateLimiter(
        scope=failure_scope,
        max_failed_attempts=5,
        window_seconds=900,
        lockout_seconds=900,
    )
    for _ in range(4):
        assert failure_limiter.record_failure("failed-login-user") is False
    assert failure_limiter.record_failure("failed-login-user") is True
    assert first.is_locked("worker-test@example.com") is True
    assert failure_limiter.is_locked("failed-login-user") is True


def test_postgresql_request_throttle_is_atomic_under_concurrency(
    postgres_database,
):
    """Concurrent workers must not exceed the configured request allowance."""

    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4

    from timan_intelligence.security.distributed_rate_limit import (
        DatabaseRateLimiter,
    )

    scope = f"postgres-concurrent-request-{uuid4()}"
    identifier = f"{uuid4()}@example.com"
    worker_count = 20
    allowed_attempts = 4
    barrier = Barrier(worker_count)

    def consume_from_independent_worker():
        limiter = DatabaseRateLimiter(
            scope=scope,
            max_failed_attempts=allowed_attempts,
            window_seconds=120,
            lockout_seconds=120,
        )
        barrier.wait(timeout=15)
        return limiter.consume_attempt(identifier)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(
            executor.map(
                lambda _: consume_from_independent_worker(),
                range(worker_count),
            )
        )

    assert sum(results) == allowed_attempts

    limiter = DatabaseRateLimiter(
        scope=scope,
        max_failed_attempts=allowed_attempts,
        window_seconds=120,
        lockout_seconds=120,
    )
    assert limiter.consume_attempt(identifier) is False


def test_postgresql_failed_login_counter_is_atomic_under_concurrency(
    postgres_database,
):
    """Concurrent failed logins must produce one consistent lockout state."""

    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from uuid import uuid4
    import time

    from timan_intelligence.security.distributed_rate_limit import (
        DatabaseRateLimiter,
    )

    scope = f"postgres-concurrent-login-{uuid4()}"
    identifier = f"concurrent-user-{uuid4()}"
    worker_count = 20
    failure_threshold = 5
    barrier = Barrier(worker_count)

    def record_from_independent_worker():
        limiter = DatabaseRateLimiter(
            scope=scope,
            max_failed_attempts=failure_threshold,
            window_seconds=120,
            lockout_seconds=120,
        )
        barrier.wait(timeout=15)
        return limiter.record_failure(identifier)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = list(
            executor.map(
                lambda _: record_from_independent_worker(),
                range(worker_count),
            )
        )

    limiter = DatabaseRateLimiter(
        scope=scope,
        max_failed_attempts=failure_threshold,
        window_seconds=120,
        lockout_seconds=120,
    )
    assert limiter.is_locked(identifier) is True

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT failure_count, locked_until
            FROM rate_limit_states
            WHERE key_hash = %s
            """,
            (limiter._key_hash(identifier),),
        ).fetchone()

    assert row is not None
    assert row["failure_count"] == failure_threshold
    assert row["locked_until"] is not None
    assert float(row["locked_until"]) > time.time()
    assert any(results)
