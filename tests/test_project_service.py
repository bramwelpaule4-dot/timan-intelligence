
"""Tests for TimanStat project and project membership services."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.organisations.service import (
    create_organisation,
    add_organisation_member,
)
from timan_intelligence.projects.service import (
    create_project,
    list_user_projects,
    get_project,
    update_project,
    add_project_member,
    list_project_members,
    change_project_membership_role,
    change_project_membership_status,
    remove_project_member,
)


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""
    database_file = tmp_path / "test_timanstat.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    initialise_database()
    return database_file


@pytest.fixture
def test_users(test_database):
    """Create user accounts for project tests."""
    users = {}

    user_details = [
        ("projectadmin", "projectadmin@example.com", "Project Admin"),
        ("member", "member@example.com", "Project Member"),
        ("secondmember", "second@example.com", "Second Member"),
        ("outsider", "outsider@example.com", "Organisation Outsider"),
        ("inactive", "inactive@example.com", "Inactive User"),
    ]

    for username, email, full_name in user_details:
        users[username] = register_user(
            username=username,
            email=email,
            full_name=full_name,
            password="SecureTestPassword123!",
        )

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (False, users["inactive"]),
        )

    return users


@pytest.fixture
def test_organisation(test_users):
    """Create an organisation with an Organisation Admin."""
    return create_organisation(
        name="TimanStat Project Test Organisation",
        created_by=test_users["projectadmin"],
    )


@pytest.fixture
def test_project(test_users, test_organisation):
    """Create a project within the test organisation."""
    return create_project(
        organisation_id=test_organisation,
        name="Test Project",
        created_by=test_users["projectadmin"],
        description="A project for testing.",
    )


@pytest.fixture
def organisation_members(test_users, test_organisation):
    """Add users who can be assigned to projects."""
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["secondmember"],
        added_by=test_users["projectadmin"],
    )

    return test_organisation


def test_create_project(test_database, test_users, test_organisation):
    project_id = create_project(
        organisation_id=test_organisation,
        name="New Project",
        created_by=test_users["projectadmin"],
    )

    assert isinstance(project_id, str)
    assert project_id

    with database_connection() as connection:
        project = connection.execute(
            "SELECT * FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    assert project is not None
    assert project["name"] == "New Project"
    assert project["organisation_id"] == test_organisation
    assert project["status"] == "active"
    assert project["created_by"] == test_users["projectadmin"]


def test_create_project_creates_project_admin_membership(
    test_database,
    test_users,
    test_organisation,
):
    project_id = create_project(
        organisation_id=test_organisation,
        name="Membership Project",
        created_by=test_users["projectadmin"],
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT *
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (project_id, test_users["projectadmin"]),
        ).fetchone()

    assert membership is not None
    assert membership["role"] == "project_admin"
    assert membership["status"] == "active"


def test_create_project_normalises_name(
    test_database,
    test_users,
    test_organisation,
):
    project_id = create_project(
        organisation_id=test_organisation,
        name="  Water Access Project  ",
        created_by=test_users["projectadmin"],
    )

    with database_connection() as connection:
        project = connection.execute(
            "SELECT name FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    assert project["name"] == "Water Access Project"


@pytest.mark.parametrize(
    "invalid_name",
    ["", "   ", None, 123],
)
def test_create_project_rejects_invalid_name(
    test_database,
    test_users,
    test_organisation,
    invalid_name,
):
    with pytest.raises(ValueError):
        create_project(
            organisation_id=test_organisation,
            name=invalid_name,
            created_by=test_users["projectadmin"],
        )


def test_create_project_rejects_empty_creator(
    test_database,
    test_organisation,
):
    with pytest.raises(ValueError):
        create_project(
            organisation_id=test_organisation,
            name="Test Project",
            created_by=" ",
        )


def test_create_project_rejects_inactive_creator(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        create_project(
            organisation_id=test_organisation,
            name="Test Project",
            created_by=test_users["inactive"],
        )


def test_create_project_rejects_non_admin(
    test_database,
    test_users,
    test_organisation,
    organisation_members,
):
    with pytest.raises(PermissionError):
        create_project(
            organisation_id=test_organisation,
            name="Unauthorised Project",
            created_by=test_users["member"],
        )


def test_create_project_rejects_unknown_organisation(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        create_project(
            organisation_id="unknown-organisation",
            name="Test Project",
            created_by=test_users["projectadmin"],
        )


def test_create_project_rejects_inactive_organisation(
    test_database,
    test_users,
    test_organisation,
):
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE organisations
            SET status = 'suspended'
            WHERE id = ?
            """,
            (test_organisation,),
        )

    with pytest.raises(ValueError):
        create_project(
            organisation_id=test_organisation,
            name="Test Project",
            created_by=test_users["projectadmin"],
        )


def test_create_project_normalises_optional_description(
    test_database,
    test_users,
    test_organisation,
):
    project_id = create_project(
        organisation_id=test_organisation,
        name="Description Project",
        created_by=test_users["projectadmin"],
        description="  Project description  ",
    )

    with database_connection() as connection:
        project = connection.execute(
            "SELECT description FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()

    assert project["description"] == "Project description"


def test_list_user_projects_includes_project_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    projects = list_user_projects(test_users["member"])

    assert len(projects) == 1
    assert projects[0]["project_id"] == test_project
    assert projects[0]["project_name"] == "Test Project"
    assert projects[0]["membership_role"] == "project_member"


def test_list_user_projects_excludes_unassigned_organisation_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    projects = list_user_projects(test_users["secondmember"])

    assert projects == []


def test_list_user_projects_includes_organisation_admin(
    test_database,
    test_users,
    test_project,
):
    projects = list_user_projects(test_users["projectadmin"])

    assert len(projects) == 1
    assert projects[0]["project_id"] == test_project


def test_list_user_projects_excludes_suspended_membership(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE project_memberships
            SET status = 'suspended'
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        )

    projects = list_user_projects(test_users["member"])

    assert projects == []


def test_list_user_projects_rejects_inactive_user(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        list_user_projects(test_users["inactive"])


def test_get_project(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    project = get_project(
        project_id=test_project,
        requested_by=test_users["member"],
    )

    assert project["id"] == test_project
    assert project["name"] == "Test Project"
    assert project["description"] == "A project for testing."
    assert project["status"] == "active"


def test_get_project_rejects_unassigned_organisation_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    with pytest.raises(PermissionError):
        get_project(
            project_id=test_project,
            requested_by=test_users["secondmember"],
        )


def test_get_project_rejects_unknown_project(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        get_project(
            project_id="unknown-project",
            requested_by=test_users["projectadmin"],
        )


def test_update_project(
    test_database,
    test_users,
    test_project,
):
    update_project(
        project_id=test_project,
        updated_by=test_users["projectadmin"],
        name="Updated Project",
        description="Updated description.",
        status="on_hold",
    )

    with database_connection() as connection:
        project = connection.execute(
            "SELECT * FROM projects WHERE id = ?",
            (test_project,),
        ).fetchone()

    assert project["name"] == "Updated Project"
    assert project["description"] == "Updated description."
    assert project["status"] == "on_hold"


@pytest.mark.parametrize(
    "status",
    ["active", "on_hold", "completed", "archived"],
)
def test_update_project_accepts_valid_statuses(
    test_database,
    test_users,
    test_project,
    status,
):
    update_project(
        project_id=test_project,
        updated_by=test_users["projectadmin"],
        status=status,
    )

    with database_connection() as connection:
        project = connection.execute(
            "SELECT status FROM projects WHERE id = ?",
            (test_project,),
        ).fetchone()

    assert project["status"] == status


def test_update_project_rejects_invalid_status(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        update_project(
            project_id=test_project,
            updated_by=test_users["projectadmin"],
            status="deleted",
        )


def test_update_project_requires_at_least_one_field(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        update_project(
            project_id=test_project,
            updated_by=test_users["projectadmin"],
        )


def test_project_member_cannot_update_project(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(PermissionError):
        update_project(
            project_id=test_project,
            updated_by=test_users["member"],
            name="Unauthorised Update",
        )


def test_add_project_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    membership_id = add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    assert isinstance(membership_id, str)
    assert membership_id

    with database_connection() as connection:
        membership = connection.execute(
            "SELECT * FROM project_memberships WHERE id = ?",
            (membership_id,),
        ).fetchone()

    assert membership is not None
    assert membership["project_id"] == test_project
    assert membership["user_id"] == test_users["member"]
    assert membership["role"] == "project_member"
    assert membership["status"] == "active"


def test_add_project_admin(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    membership_id = add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
        role="project_admin",
    )

    with database_connection() as connection:
        membership = connection.execute(
            "SELECT role FROM project_memberships WHERE id = ?",
            (membership_id,),
        ).fetchone()

    assert membership["role"] == "project_admin"


def test_add_project_member_normalises_role(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    membership_id = add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
        role="  PROJECT_MEMBER ",
    )

    with database_connection() as connection:
        membership = connection.execute(
            "SELECT role FROM project_memberships WHERE id = ?",
            (membership_id,),
        ).fetchone()

    assert membership["role"] == "project_member"


def test_non_admin_cannot_add_project_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(PermissionError):
        add_project_member(
            project_id=test_project,
            user_id=test_users["secondmember"],
            added_by=test_users["member"],
        )


def test_project_admin_can_add_project_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
        role="project_admin",
    )

    membership_id = add_project_member(
        project_id=test_project,
        user_id=test_users["secondmember"],
        added_by=test_users["member"],
    )

    assert membership_id


def test_add_project_member_rejects_invalid_role(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    with pytest.raises(ValueError):
        add_project_member(
            project_id=test_project,
            user_id=test_users["member"],
            added_by=test_users["projectadmin"],
            role="super_admin",
        )


def test_add_project_member_rejects_non_organisation_member(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(PermissionError):
        add_project_member(
            project_id=test_project,
            user_id=test_users["outsider"],
            added_by=test_users["projectadmin"],
        )


def test_add_project_member_rejects_inactive_user(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        add_project_member(
            project_id=test_project,
            user_id=test_users["inactive"],
            added_by=test_users["projectadmin"],
        )


def test_add_project_member_rejects_duplicate_membership(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(ValueError):
        add_project_member(
            project_id=test_project,
            user_id=test_users["member"],
            added_by=test_users["projectadmin"],
        )


def test_list_project_members(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    members = list_project_members(
        project_id=test_project,
        requested_by=test_users["projectadmin"],
    )

    member_ids = {member["user_id"] for member in members}

    assert len(members) == 2
    assert test_users["projectadmin"] in member_ids
    assert test_users["member"] in member_ids


def test_list_project_members_includes_user_details(
    test_database,
    test_users,
    test_project,
):
    members = list_project_members(
        project_id=test_project,
        requested_by=test_users["projectadmin"],
    )

    admin = next(
        member
        for member in members
        if member["user_id"] == test_users["projectadmin"]
    )

    assert admin["username"] == "projectadmin"
    assert admin["email"] == "projectadmin@example.com"
    assert admin["full_name"] == "Project Admin"
    assert admin["membership_role"] == "project_admin"


def test_project_member_cannot_list_project_members(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(PermissionError):
        list_project_members(
            project_id=test_project,
            requested_by=test_users["member"],
        )


def test_project_admin_can_list_project_members(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
        role="project_admin",
    )

    members = list_project_members(
        project_id=test_project,
        requested_by=test_users["member"],
    )

    assert len(members) == 2


def test_change_project_membership_role(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    change_project_membership_role(
        project_id=test_project,
        user_id=test_users["member"],
        changed_by=test_users["projectadmin"],
        new_role="project_admin",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        ).fetchone()

    assert membership["role"] == "project_admin"


def test_non_admin_cannot_change_project_membership_role(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(PermissionError):
        change_project_membership_role(
            project_id=test_project,
            user_id=test_users["member"],
            changed_by=test_users["member"],
            new_role="project_admin",
        )


def test_change_project_membership_role_rejects_invalid_role(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    with pytest.raises(ValueError):
        change_project_membership_role(
            project_id=test_project,
            user_id=test_users["projectadmin"],
            changed_by=test_users["projectadmin"],
            new_role="super_admin",
        )


def test_change_project_membership_role_rejects_unknown_membership(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        change_project_membership_role(
            project_id=test_project,
            user_id="unknown-user",
            changed_by=test_users["projectadmin"],
            new_role="project_member",
        )


def test_last_active_project_admin_cannot_be_demoted(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        change_project_membership_role(
            project_id=test_project,
            user_id=test_users["projectadmin"],
            changed_by=test_users["projectadmin"],
            new_role="project_member",
        )


def test_another_project_admin_can_be_demoted_when_one_remains(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
        role="project_admin",
    )

    change_project_membership_role(
        project_id=test_project,
        user_id=test_users["member"],
        changed_by=test_users["projectadmin"],
        new_role="project_member",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        ).fetchone()

    assert membership["role"] == "project_member"


def test_change_project_membership_status(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    change_project_membership_status(
        project_id=test_project,
        user_id=test_users["member"],
        changed_by=test_users["projectadmin"],
        new_status="suspended",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT status
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        ).fetchone()

    assert membership["status"] == "suspended"


@pytest.mark.parametrize(
    "status",
    ["active", "pending", "suspended"],
)
def test_change_project_membership_status_accepts_valid_statuses(
    test_database,
    test_users,
    test_project,
    organisation_members,
    status,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    change_project_membership_status(
        project_id=test_project,
        user_id=test_users["member"],
        changed_by=test_users["projectadmin"],
        new_status=status,
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT status
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        ).fetchone()

    assert membership["status"] == status


def test_change_project_membership_status_rejects_invalid_status(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        change_project_membership_status(
            project_id=test_project,
            user_id=test_users["projectadmin"],
            changed_by=test_users["projectadmin"],
            new_status="deleted",
        )


def test_non_admin_cannot_change_project_membership_status(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(PermissionError):
        change_project_membership_status(
            project_id=test_project,
            user_id=test_users["member"],
            changed_by=test_users["member"],
            new_status="suspended",
        )


def test_last_active_project_admin_cannot_be_suspended(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        change_project_membership_status(
            project_id=test_project,
            user_id=test_users["projectadmin"],
            changed_by=test_users["projectadmin"],
            new_status="suspended",
        )


def test_another_project_admin_can_be_suspended_when_one_remains(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
        role="project_admin",
    )

    change_project_membership_status(
        project_id=test_project,
        user_id=test_users["member"],
        changed_by=test_users["projectadmin"],
        new_status="suspended",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT status
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        ).fetchone()

    assert membership["status"] == "suspended"


def test_remove_project_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    remove_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        removed_by=test_users["projectadmin"],
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT id
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        ).fetchone()

        user = connection.execute(
            "SELECT id FROM users WHERE id = ?",
            (test_users["member"],),
        ).fetchone()

    assert membership is None
    assert user is not None


def test_non_admin_cannot_remove_project_member(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(PermissionError):
        remove_project_member(
            project_id=test_project,
            user_id=test_users["member"],
            removed_by=test_users["member"],
        )


def test_last_active_project_admin_cannot_be_removed(
    test_database,
    test_users,
    test_project,
):
    with pytest.raises(ValueError):
        remove_project_member(
            project_id=test_project,
            user_id=test_users["projectadmin"],
            removed_by=test_users["projectadmin"],
        )


def test_another_project_admin_can_be_removed_when_one_remains(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
        role="project_admin",
    )

    remove_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        removed_by=test_users["projectadmin"],
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT id
            FROM project_memberships
            WHERE project_id = ?
              AND user_id = ?
            """,
            (test_project, test_users["member"]),
        ).fetchone()

    assert membership is None


def test_organisation_admin_can_manage_project_members(
    test_database,
    test_users,
    test_project,
    organisation_members,
):
    membership_id = add_project_member(
        project_id=test_project,
        user_id=test_users["secondmember"],
        added_by=test_users["projectadmin"],
    )

    assert membership_id


def test_project_member_cannot_access_another_project(
    test_database,
    test_users,
    test_project,
    test_organisation,
    organisation_members,
):
    other_project_id = create_project(
        organisation_id=test_organisation,
        name="Another Project",
        created_by=test_users["projectadmin"],
    )

    add_project_member(
        project_id=test_project,
        user_id=test_users["member"],
        added_by=test_users["projectadmin"],
    )

    with pytest.raises(PermissionError):
        get_project(
            project_id=other_project_id,
            requested_by=test_users["member"],
        )
