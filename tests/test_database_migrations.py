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


def create_legacy_schema(
    *,
    omit_index: str | None = None,
    missing_membership_foreign_key: bool = False,
    incorrect_membership_delete_rule: bool = False,
    missing_membership_unique_constraint: bool = False,
    missing_user_check_constraint: bool = False,
) -> None:
    """Create a legacy database with optional structural defects."""

    with database_connection() as connection:
        for original_statement in SCHEMA_STATEMENTS:
            statement = original_statement

            if (
                missing_membership_foreign_key
                and "CREATE TABLE IF NOT EXISTS organisation_memberships"
                in statement
            ):
                statement = statement.replace(
                    "REFERENCES organisations(id) ON DELETE CASCADE",
                    "REFERENCES organisations(id) ON DELETE NO ACTION",
                )

            if (
                incorrect_membership_delete_rule
                and "CREATE TABLE IF NOT EXISTS organisation_memberships"
                in statement
            ):
                statement = statement.replace(
                    "REFERENCES organisations(id) ON DELETE CASCADE",
                    "REFERENCES organisations(id) ON DELETE NO ACTION",
                )

            if (
                missing_membership_unique_constraint
                and "CREATE TABLE IF NOT EXISTS organisation_memberships"
                in statement
            ):
                statement = statement.replace(
                    "joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
                    "        UNIQUE (organisation_id, user_id)",
                    "joined_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
                )

            if (
                missing_user_check_constraint
                and "CREATE TABLE IF NOT EXISTS users"
                in statement
            ):
                statement = statement.replace(
                    "role TEXT NOT NULL DEFAULT 'user'\n"
                    "            CHECK (role IN "
                    "('super_admin', 'admin', 'developer', 'user'))",
                    "role TEXT NOT NULL DEFAULT 'user'",
                )

            if omit_index and omit_index in statement:
                continue

            connection.execute(statement)


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

    create_legacy_schema()

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


def test_missing_membership_foreign_key_is_rejected(
    migration_database,
):
    """A membership foreign key with the wrong delete rule is rejected."""

    create_legacy_schema(missing_membership_foreign_key=True)

    with pytest.raises(MigrationError, match="missing required foreign keys"):
        initialise_database()


def test_incorrect_membership_delete_rule_is_rejected(
    migration_database,
):
    """An incorrect foreign-key deletion rule must prevent baselining."""

    create_legacy_schema(incorrect_membership_delete_rule=True)

    with pytest.raises(MigrationError, match="missing required foreign keys"):
        initialise_database()


def test_missing_membership_unique_constraint_is_rejected(
    migration_database,
):
    """A missing organisation membership uniqueness rule is rejected."""

    create_legacy_schema(missing_membership_unique_constraint=True)

    with pytest.raises(
        MigrationError,
        match="missing required unique constraints",
    ):
        initialise_database()


def test_missing_user_check_constraint_is_rejected(
    migration_database,
):
    """A missing user role check constraint must prevent baselining."""

    create_legacy_schema(missing_user_check_constraint=True)

    with pytest.raises(
        MigrationError,
        match="missing the required CHECK constraint",
    ):
        initialise_database()


def test_missing_required_index_is_rejected(
    migration_database,
):
    """A missing required index must prevent baselining."""

    create_legacy_schema(omit_index="idx_memberships_user")

    with pytest.raises(
        MigrationError,
        match="missing required index",
    ):
        initialise_database()
