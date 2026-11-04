
"""Tests for TimanStat database integrity and constraints."""

import sqlite3

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database


@pytest.fixture
def initialised_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""

    database_file = tmp_path / "test_timanstat.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    initialise_database()

    return database_file


def create_user(
    connection,
    user_id="user-1",
    username="user1",
    email="user1@example.com",
):
    """Insert a valid user record."""

    connection.execute(
        """
        INSERT INTO users (
            id, username, email, full_name, password_hash
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            user_id,
            username,
            email,
            "Test User",
            "test-password-hash",
        ),
    )


def create_organisation(
    connection,
    organisation_id="org-1",
    created_by=None,
):
    """Insert a valid organisation record."""

    connection.execute(
        """
        INSERT INTO organisations (
            id, name, created_by
        )
        VALUES (?, ?, ?)
        """,
        (
            organisation_id,
            "Test Organisation",
            created_by,
        ),
    )


def create_project(
    connection,
    project_id="project-1",
    organisation_id="org-1",
    created_by="user-1",
):
    """Insert a valid project record."""

    connection.execute(
        """
        INSERT INTO projects (
            id, organisation_id, name, created_by
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            project_id,
            organisation_id,
            "Test Project",
            created_by,
        ),
    )


def test_users_reject_duplicate_usernames(initialised_database):
    """Usernames must be unique."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)

            create_user(
                connection,
                user_id="user-2",
                username="user1",
                email="another@example.com",
            )


def test_users_reject_duplicate_emails(initialised_database):
    """Email addresses must be unique."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)

            create_user(
                connection,
                user_id="user-2",
                username="user2",
                email="user1@example.com",
            )


def test_organisation_memberships_reject_duplicates(
    initialised_database,
):
    """A user cannot have duplicate membership records in one organisation."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)
            create_organisation(connection)

            connection.execute(
                """
                INSERT INTO organisation_memberships (
                    id, organisation_id, user_id
                )
                VALUES (?, ?, ?)
                """,
                ("membership-1", "org-1", "user-1"),
            )

            connection.execute(
                """
                INSERT INTO organisation_memberships (
                    id, organisation_id, user_id
                )
                VALUES (?, ?, ?)
                """,
                ("membership-2", "org-1", "user-1"),
            )


def test_project_memberships_reject_duplicates(
    initialised_database,
):
    """A user cannot have duplicate membership records in one project."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)
            create_organisation(connection)
            create_project(connection)

            connection.execute(
                """
                INSERT INTO project_memberships (
                    id, project_id, user_id
                )
                VALUES (?, ?, ?)
                """,
                ("membership-1", "project-1", "user-1"),
            )

            connection.execute(
                """
                INSERT INTO project_memberships (
                    id, project_id, user_id
                )
                VALUES (?, ?, ?)
                """,
                ("membership-2", "project-1", "user-1"),
            )


@pytest.mark.parametrize(
    ("table_name", "column_name", "invalid_value"),
    [
        ("users", "role", "invalid_role"),
        ("organisations", "status", "invalid_status"),
        ("organisation_memberships", "role", "invalid_role"),
        ("organisation_memberships", "status", "invalid_status"),
        ("projects", "status", "invalid_status"),
        ("project_memberships", "role", "invalid_role"),
        ("project_memberships", "status", "invalid_status"),
    ],
)
def test_database_rejects_invalid_role_and_status_values(
    initialised_database,
    table_name,
    column_name,
    invalid_value,
):
    """CHECK constraints should reject unsupported roles and statuses."""

    insert_statements = {
        "users": (
            """
            INSERT INTO users (
                id, username, email, full_name, password_hash, role
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "user-1",
                "user1",
                "user1@example.com",
                "Test User",
                "test-hash",
                invalid_value,
            ),
        ),
        "organisations": (
            """
            INSERT INTO organisations (id, name, status)
            VALUES (?, ?, ?)
            """,
            ("org-1", "Test Organisation", invalid_value),
        ),
        "organisation_memberships": (
            """
            INSERT INTO organisation_memberships (
                id, organisation_id, user_id, role, status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "membership-1",
                "org-1",
                "user-1",
                invalid_value if column_name == "role" else "org_member",
                invalid_value if column_name == "status" else "active",
            ),
        ),
        "projects": (
            """
            INSERT INTO projects (
                id, organisation_id, name, status
            )
            VALUES (?, ?, ?, ?)
            """,
            ("project-1", "org-1", "Test Project", invalid_value),
        ),
        "project_memberships": (
            """
            INSERT INTO project_memberships (
                id, project_id, user_id, role, status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "membership-1",
                "project-1",
                "user-1",
                invalid_value if column_name == "role" else "project_member",
                invalid_value if column_name == "status" else "active",
            ),
        ),
    }

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)
            create_organisation(connection)
            create_project(connection)

            statement, parameters = insert_statements[table_name]

            connection.execute(statement, parameters)


def test_organisation_rejects_nonexistent_creator(
    initialised_database,
):
    """An organisation cannot reference a nonexistent creator."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_organisation(
                connection,
                created_by="missing-user",
            )


def test_organisation_rejects_nonexistent_creator_reference(
    initialised_database,
):
    """Organisation creator references must point to existing users."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_organisation(
                connection,
                created_by="missing-user",
            )


def test_deleting_organisation_creator_is_restricted(
    initialised_database,
):
    """An organisation creator cannot be deleted while referenced."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)
            create_organisation(
                connection,
                created_by="user-1",
            )

            connection.execute(
                "DELETE FROM users WHERE id = ?",
                ("user-1",),
            )


def test_project_rejects_nonexistent_organisation(
    initialised_database,
):
    """A project cannot reference a nonexistent organisation."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)

            create_project(
                connection,
                organisation_id="missing-org",
            )


def test_organisation_membership_rejects_nonexistent_user(
    initialised_database,
):
    """An organisation membership cannot reference a nonexistent user."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_organisation(connection)

            connection.execute(
                """
                INSERT INTO organisation_memberships (
                    id, organisation_id, user_id
                )
                VALUES (?, ?, ?)
                """,
                ("membership-1", "org-1", "missing-user"),
            )


def test_project_membership_rejects_nonexistent_project(
    initialised_database,
):
    """A project membership cannot reference a nonexistent project."""

    with pytest.raises(sqlite3.IntegrityError):
        with database_connection() as connection:
            create_user(connection)

            connection.execute(
                """
                INSERT INTO project_memberships (
                    id, project_id, user_id
                )
                VALUES (?, ?, ?)
                """,
                ("membership-1", "missing-project", "user-1"),
            )


def test_deleting_user_cascades_organisation_memberships(
    initialised_database,
):
    """Deleting a user should delete their organisation memberships."""

    with database_connection() as connection:
        create_user(connection)
        create_organisation(connection)

        connection.execute(
            """
            INSERT INTO organisation_memberships (
                id, organisation_id, user_id
            )
            VALUES (?, ?, ?)
            """,
            ("membership-1", "org-1", "user-1"),
        )

        connection.execute(
            "DELETE FROM users WHERE id = ?",
            ("user-1",),
        )

        result = connection.execute(
            "SELECT COUNT(*) AS total FROM organisation_memberships"
        ).fetchone()

    assert result["total"] == 0


def test_deleting_organisation_cascades_projects_and_memberships(
    initialised_database,
):
    """Deleting an organisation should delete its projects and memberships."""

    with database_connection() as connection:
        create_user(connection)
        create_organisation(connection)
        create_project(connection)

        connection.execute(
            """
            INSERT INTO organisation_memberships (
                id, organisation_id, user_id
            )
            VALUES (?, ?, ?)
            """,
            ("org-membership-1", "org-1", "user-1"),
        )

        connection.execute(
            """
            INSERT INTO project_memberships (
                id, project_id, user_id
            )
            VALUES (?, ?, ?)
            """,
            ("project-membership-1", "project-1", "user-1"),
        )

        connection.execute(
            "DELETE FROM organisations WHERE id = ?",
            ("org-1",),
        )

        project_count = connection.execute(
            "SELECT COUNT(*) AS total FROM projects"
        ).fetchone()["total"]

        organisation_membership_count = connection.execute(
            "SELECT COUNT(*) AS total FROM organisation_memberships"
        ).fetchone()["total"]

        project_membership_count = connection.execute(
            "SELECT COUNT(*) AS total FROM project_memberships"
        ).fetchone()["total"]

    assert project_count == 0
    assert organisation_membership_count == 0
    assert project_membership_count == 0


def test_deleting_project_cascades_project_memberships(
    initialised_database,
):
    """Deleting a project should delete its project memberships."""

    with database_connection() as connection:
        create_user(connection)
        create_organisation(connection)
        create_project(connection)

        connection.execute(
            """
            INSERT INTO project_memberships (
                id, project_id, user_id
            )
            VALUES (?, ?, ?)
            """,
            ("membership-1", "project-1", "user-1"),
        )

        connection.execute(
            "DELETE FROM projects WHERE id = ?",
            ("project-1",),
        )

        result = connection.execute(
            "SELECT COUNT(*) AS total FROM project_memberships"
        ).fetchone()

    assert result["total"] == 0


def test_deleting_user_sets_audit_user_reference_to_null(
    initialised_database,
):
    """Audit records should remain when their user is deleted."""

    with database_connection() as connection:
        create_user(connection)

        connection.execute(
            """
            INSERT INTO audit_logs (
                id, user_id, action
            )
            VALUES (?, ?, ?)
            """,
            ("audit-1", "user-1", "test_action"),
        )

        connection.execute(
            "DELETE FROM users WHERE id = ?",
            ("user-1",),
        )

        result = connection.execute(
            "SELECT user_id FROM audit_logs WHERE id = ?",
            ("audit-1",),
        ).fetchone()

    assert result is not None
    assert result["user_id"] is None


def test_deleting_organisation_sets_audit_organisation_reference_to_null(
    initialised_database,
):
    """Audit records should remain when their organisation is deleted."""

    with database_connection() as connection:
        create_organisation(connection)

        connection.execute(
            """
            INSERT INTO audit_logs (
                id, organisation_id, action
            )
            VALUES (?, ?, ?)
            """,
            ("audit-1", "org-1", "test_action"),
        )

        connection.execute(
            "DELETE FROM organisations WHERE id = ?",
            ("org-1",),
        )

        result = connection.execute(
            "SELECT organisation_id FROM audit_logs WHERE id = ?",
            ("audit-1",),
        ).fetchone()

    assert result is not None
    assert result["organisation_id"] is None


def test_deleting_project_creator_sets_reference_to_null(
    initialised_database,
):
    """Deleting a project creator should not delete the project."""

    with database_connection() as connection:
        create_user(connection)

        # The organisation has no creator reference to this user.
        create_organisation(connection)

        create_project(connection)

        connection.execute(
            "DELETE FROM users WHERE id = ?",
            ("user-1",),
        )

        result = connection.execute(
            """
            SELECT created_by
            FROM projects
            WHERE id = ?
            """,
            ("project-1",),
        ).fetchone()

    assert result is not None
    assert result["created_by"] is None
