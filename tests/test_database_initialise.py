
"""Tests for TimanStat database schema initialisation."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import (
    initialise_database,
    check_database_connection,
)


@pytest.fixture
def initialised_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database with the TimanStat schema."""

    database_file = tmp_path / "test_timanstat.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    initialise_database()

    return database_file


def test_initialise_database_creates_core_tables(initialised_database):
    """Initialisation should create all core application tables."""

    expected_tables = {
        "users",
        "organisations",
        "organisation_memberships",
        "projects",
        "project_memberships",
        "audit_logs",
    }

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    actual_tables = {row["name"] for row in rows}

    assert expected_tables.issubset(actual_tables)


def test_initialise_database_can_run_multiple_times(
    initialised_database,
):
    """Repeated initialisation should not fail or duplicate tables."""

    initialise_database()
    initialise_database()

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()

    table_names = [row["name"] for row in rows]

    assert table_names.count("users") == 1
    assert table_names.count("organisations") == 1
    assert table_names.count("projects") == 1


def test_users_table_has_required_columns(initialised_database):
    """The users table should contain essential identity fields."""

    expected_columns = {
        "id",
        "username",
        "email",
        "full_name",
        "password_hash",
        "role",
        "is_active",
        "email_verified",
        "created_at",
        "updated_at",
        "last_login_at",
    }

    with database_connection() as connection:
        rows = connection.execute(
            "PRAGMA table_info(users)"
        ).fetchall()

    actual_columns = {row["name"] for row in rows}

    assert expected_columns.issubset(actual_columns)


def test_organisations_table_has_required_columns(
    initialised_database,
):
    """The organisations table should contain essential fields."""

    expected_columns = {
        "id",
        "name",
        "organisation_type",
        "registration_number",
        "contact_email",
        "country",
        "status",
        "created_by",
        "created_at",
        "updated_at",
    }

    with database_connection() as connection:
        rows = connection.execute(
            "PRAGMA table_info(organisations)"
        ).fetchall()

    actual_columns = {row["name"] for row in rows}

    assert expected_columns.issubset(actual_columns)


def test_projects_table_has_organisation_relationship(
    initialised_database,
):
    """Projects should be linked to their parent organisation."""

    with database_connection() as connection:
        rows = connection.execute(
            "PRAGMA foreign_key_list(projects)"
        ).fetchall()

    relationships = {
        (row["from"], row["table"], row["to"])
        for row in rows
    }

    assert (
        "organisation_id",
        "organisations",
        "id",
    ) in relationships


@pytest.mark.parametrize(
    ("table_name", "expected_relationships"),
    [
        (
            "organisation_memberships",
            {
                ("organisation_id", "organisations", "id"),
                ("user_id", "users", "id"),
            },
        ),
        (
            "project_memberships",
            {
                ("project_id", "projects", "id"),
                ("user_id", "users", "id"),
            },
        ),
    ],
)
def test_membership_tables_have_required_relationships(
    initialised_database,
    table_name,
    expected_relationships,
):
    """Membership records should reference their parent records."""

    with database_connection() as connection:
        rows = connection.execute(
            f"PRAGMA foreign_key_list({table_name})"
        ).fetchall()

    actual_relationships = {
        (row["from"], row["table"], row["to"])
        for row in rows
    }

    assert expected_relationships.issubset(actual_relationships)


@pytest.mark.parametrize(
    ("table_name", "expected_columns"),
    [
        (
            "organisation_memberships",
            {"organisation_id", "user_id"},
        ),
        (
            "project_memberships",
            {"project_id", "user_id"},
        ),
    ],
)
def test_membership_tables_enforce_unique_membership(
    initialised_database,
    table_name,
    expected_columns,
):
    """Membership tables should enforce unique user-parent pairs."""

    with database_connection() as connection:
        indexes = connection.execute(
            f"PRAGMA index_list({table_name})"
        ).fetchall()

        unique_indexes = [
            row["name"]
            for row in indexes
            if row["unique"] == 1
        ]

        indexed_column_sets = []

        for index_name in unique_indexes:
            rows = connection.execute(
                f"PRAGMA index_info('{index_name}')"
            ).fetchall()

            indexed_column_sets.append(
                {row["name"] for row in rows}
            )

    assert expected_columns in indexed_column_sets


def test_initialise_database_creates_expected_indexes(
    initialised_database,
):
    """Initialisation should create all declared lookup indexes."""

    expected_indexes = {
        "idx_memberships_user",
        "idx_memberships_organisation",
        "idx_projects_organisation",
        "idx_project_memberships_user",
        "idx_project_memberships_project",
        "idx_audit_user",
        "idx_audit_created",
    }

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
            """
        ).fetchall()

    actual_indexes = {row["name"] for row in rows}

    assert expected_indexes.issubset(actual_indexes)


def test_check_database_connection_returns_true(
    initialised_database,
):
    """The database health check should succeed for a valid database."""

    assert check_database_connection() is True
