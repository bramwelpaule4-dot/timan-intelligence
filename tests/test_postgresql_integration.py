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


@pytest.fixture(scope="session")
def postgres_database():
    """Configure and initialise an isolated PostgreSQL test database."""

    database_url = os.getenv("TIMANSTAT_TEST_POSTGRES_URL", "").strip()

    if not database_url:
        pytest.skip(
            "PostgreSQL integration tests require "
            "TIMANSTAT_TEST_POSTGRES_URL."
        )

    if not database_url.startswith(
        ("postgresql://", "postgres://")
    ):
        pytest.fail(
            "TIMANSTAT_TEST_POSTGRES_URL must be a PostgreSQL URL."
        )

    os.environ["DATABASE_URL"] = database_url

    initialise_database()

    yield database_url


def test_postgresql_connection_is_available(postgres_database):
    """PostgreSQL should accept and execute database queries."""

    with database_connection() as connection:
        result = connection.execute("SELECT 1 AS value").fetchone()

    assert result["value"] == 1


def test_postgresql_initial_migration_is_recorded(postgres_database):
    """The initial schema migration should be recorded correctly."""

    with database_connection() as connection:
        history = connection.execute(
            """
            SELECT version, name
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()

    assert len(history) == 1
    assert history[0]["version"] == LATEST_SCHEMA_VERSION
    assert history[0]["name"] == "initial_schema"


def test_postgresql_schema_contains_required_tables(
    postgres_database,
):
    """All required application tables should exist."""

    expected_tables = {
        "users",
        "organisations",
        "organisation_memberships",
        "projects",
        "project_memberships",
        "audit_logs",
        "schema_migrations",
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

    actual_tables = {
        row["table_name"]
        for row in rows
    }

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

    assert len(history) == 1
    assert history[0]["version"] == LATEST_SCHEMA_VERSION


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


def test_postgresql_enforces_membership_foreign_keys(
    postgres_database,
):
    """PostgreSQL should reject membership references to missing users."""

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
