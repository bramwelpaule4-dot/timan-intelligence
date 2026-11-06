
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
    incorrect_user_role_check: bool = False,
    incorrect_index_columns: bool = False,
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

            if (
                incorrect_user_role_check
                and "CREATE TABLE IF NOT EXISTS users"
                in statement
            ):
                statement = statement.replace(
                    "('super_admin', 'admin', 'developer', 'user')",
                    "('super_admin', 'admin', 'analyst', 'user')",
                )

            if (
                incorrect_index_columns
                and "CREATE INDEX IF NOT EXISTS idx_memberships_user"
                in statement
            ):
                statement = statement.replace(
                    "ON organisation_memberships(user_id)",
                    "ON organisation_memberships(organisation_id)",
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


def assert_totp_schema():
    """Verify that the TOTP migration added all expected user columns."""

    expected_columns = {
        "totp_enabled",
        "totp_secret_encrypted",
        "totp_pending_secret_encrypted",
        "totp_last_accepted_counter",
        "totp_enrolled_at",
        "totp_pending_created_at",
    }

    with database_connection() as connection:
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(users)"
            ).fetchall()
        }

    assert expected_columns.issubset(columns)


def test_fresh_database_applies_all_migrations(migration_database):
    """A fresh database should receive every registered migration."""

    initialise_database()

    history = get_migration_history()

    assert [(row["version"], row["name"]) for row in history] == [
        (1, "initial_schema"),
        (2, "totp_enrolment"),
        (3, "email_verification"),
    ]

    assert_totp_schema()

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

        user_columns = {
            row["name"]: row
            for row in connection.execute(
                "PRAGMA table_info(users)"
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
        "email_verification_tokens",
    }

    assert expected_tables.issubset(tables)
    assert user_columns["totp_enabled"]["dflt_value"] in (
        "FALSE",
        "0",
    )


def test_repeated_initialisation_does_not_repeat_migration(
    migration_database,
):
    """Initialising an already migrated database should be safe."""

    initialise_database()
    initialise_database()
    initialise_database()

    history = get_migration_history()

    assert [(row["version"], row["name"]) for row in history] == [
        (1, "initial_schema"),
        (2, "totp_enrolment"),
        (3, "email_verification"),
    ]


def test_existing_unversioned_database_is_baselined_and_upgraded(
    migration_database,
):
    """A valid legacy schema should be baselined and upgraded safely."""

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

    assert [(row["version"], row["name"]) for row in history] == [
        (1, "initial_schema"),
        (2, "totp_enrolment"),
        (3, "email_verification"),
    ]

    assert_totp_schema()

    with database_connection() as connection:
        user = connection.execute(
            """
            SELECT
                id,
                username,
                totp_enabled,
                totp_secret_encrypted,
                totp_pending_secret_encrypted,
                totp_last_accepted_counter
            FROM users
            WHERE id = ?
            """,
            ("existing-user",),
        ).fetchone()

    assert user is not None
    assert user["username"] == "existing"
    assert user["totp_enabled"] in (0, False)
    assert user["totp_secret_encrypted"] is None
    assert user["totp_pending_secret_encrypted"] is None
    assert user["totp_last_accepted_counter"] is None


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
            (2, "totp_enrolment"),
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


def test_incorrect_user_role_check_constraint_is_rejected(
    migration_database,
):
    """An incorrect allowed-value list must prevent baselining."""

    create_legacy_schema(incorrect_user_role_check=True)

    with pytest.raises(
        MigrationError,
        match="incorrect CHECK constraint",
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


def test_index_on_incorrect_column_is_rejected(
    migration_database,
):
    """An index with the correct name but wrong column must be rejected."""

    create_legacy_schema(incorrect_index_columns=True)

    with pytest.raises(
        MigrationError,
        match="incorrect definition",
    ):
        initialise_database()
