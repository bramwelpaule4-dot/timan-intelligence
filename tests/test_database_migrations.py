
"""Tests for TimanStat's versioned database migration system."""

from __future__ import annotations

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.database.migrations.runner import MigrationError
from timan_intelligence.database.models import SCHEMA_STATEMENTS


@pytest.fixture
def migration_database(tmp_path, monkeypatch):
    """Configure an isolated SQLite database for migration tests."""

    database_path = tmp_path / "migration_test.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_path.as_posix()}",
    )

    return database_path


def get_migration_history():
    """Return the recorded migration history."""

    with database_connection() as connection:
        return connection.execute(
            """
            SELECT version, name
            FROM schema_migrations
            ORDER BY version
            """
        ).fetchall()


def test_fresh_database_applies_initial_migration(migration_database):
    """A fresh database should receive the initial schema and migration."""

    initialise_database()

    history = get_migration_history()

    assert len(history) == 1
    assert history[0]["version"] == 1
    assert history[0]["name"] == "initial_schema"

    with database_connection() as connection:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

    expected_tables = {
        "users",
        "organisations",
        "organisation_memberships",
        "projects",
        "project_memberships",
        "audit_logs",
        "schema_migrations",
    }

    assert expected_tables.issubset(tables)


def test_repeated_initialisation_does_not_repeat_migration(
    migration_database,
):
    """Initialising an already migrated database should be safe."""

    initialise_database()
    initialise_database()
    initialise_database()

    history = get_migration_history()

    assert len(history) == 1
    assert history[0]["version"] == 1


def test_existing_unversioned_database_is_baselined(
    migration_database,
):
    """A valid existing schema should be baselined without recreation."""

    with database_connection() as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)

        connection.execute(
            """
            INSERT INTO users (
                id,
                username,
                email,
                full_name,
                password_hash
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "existing-user",
                "existing",
                "existing@example.com",
                "Existing User",
                "test-hash",
            ),
        )

    initialise_database()

    history = get_migration_history()

    assert len(history) == 1
    assert history[0]["version"] == 1
    assert history[0]["name"] == "initial_schema"

    with database_connection() as connection:
        user = connection.execute(
            "SELECT id, username FROM users WHERE id = ?",
            ("existing-user",),
        ).fetchone()

    assert user is not None
    assert user["username"] == "existing"


def test_incomplete_existing_database_is_rejected(
    migration_database,
):
    """An incomplete existing database must not be baselined."""

    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY
            )
            """
        )

    with pytest.raises(MigrationError, match="Missing tables"):
        initialise_database()


def test_unknown_migration_version_is_rejected(
    migration_database,
):
    """A database with an unknown migration version must be rejected."""

    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            INSERT INTO schema_migrations (version, name)
            VALUES (?, ?)
            """,
            (99, "unknown_migration"),
        )

    with pytest.raises(MigrationError, match="unknown migration version"):
        initialise_database()


def test_migration_name_mismatch_is_rejected(
    migration_database,
):
    """A migration version recorded under the wrong name must be rejected."""

    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            INSERT INTO schema_migrations (version, name)
            VALUES (?, ?)
            """,
            (1, "incorrect_name"),
        )

    with pytest.raises(MigrationError, match="Migration name mismatch"):
        initialise_database()


def test_migration_history_with_missing_versions_is_rejected(
    migration_database,
):
    """Migration history must not contain gaps."""

    with database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            INSERT INTO schema_migrations (version, name)
            VALUES (?, ?)
            """,
            (2, "future_migration"),
        )

    with pytest.raises(MigrationError):
        initialise_database()
