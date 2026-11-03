
"""Project and project membership services for TimanStat."""

from __future__ import annotations

import uuid
from typing import Any


from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


VALID_PROJECT_ROLES = {"project_admin", "project_member"}
VALID_PROJECT_STATUSES = {"active", "on_hold", "completed", "archived"}
VALID_MEMBERSHIP_STATUSES = {"active", "pending", "suspended"}


def _new_id() -> str:
    """Generate a unique record identifier."""
    return str(uuid.uuid4())


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""
    return "%s" if get_database_type() == "postgresql" else "?"


def _normalise_text(value: str, field_name: str) -> str:
    """Validate and normalise required text."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} is required.")

    return value


def _normalise_optional_text(
    value: str | None,
    field_name: str,
) -> str | None:
    """Validate and normalise optional text."""
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")

    value = value.strip()
    return value or None


def _validate_choice(
    value: str,
    allowed_values: set[str],
    field_name: str,
) -> str:
    """Validate and normalise a controlled value."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text.")

    value = value.strip().lower()

    if value not in allowed_values:
        raise ValueError(f"Invalid {field_name.lower()}.")

    return value


def _require_active_user(
    connection: Any,
    user_id: str,
) -> None:
    """Verify that an individual user account exists and is active."""
    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT id
        FROM users
        WHERE id = {p}
          AND is_active = TRUE
        """,
        (user_id,),
    ).fetchone()

    if result is None:
        raise ValueError("The individual user does not exist or is inactive.")


def _require_active_organisation(
    connection: Any,
    organisation_id: str,
) -> None:
    """Verify that an organisation exists and is active."""
    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT id
        FROM organisations
        WHERE id = {p}
          AND status = 'active'
        """,
        (organisation_id,),
    ).fetchone()

    if result is None:
        raise ValueError("Organisation does not exist or is inactive.")


def _require_active_organisation_member(
    connection: Any,
    organisation_id: str,
    user_id: str,
) -> None:
    """Verify that a user is an active member of an organisation."""
    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT id
        FROM organisation_memberships
        WHERE organisation_id = {p}
          AND user_id = {p}
          AND status = 'active'
        """,
        (organisation_id, user_id),
    ).fetchone()

    if result is None:
        raise PermissionError(
            "An active organisation membership is required."
        )


def _is_organisation_admin(
    connection: Any,
    organisation_id: str,
    user_id: str,
) -> bool:
    """Check whether a user is an active Organisation Admin."""
    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT id
        FROM organisation_memberships
        WHERE organisation_id = {p}
          AND user_id = {p}
          AND role = 'org_admin'
          AND status = 'active'
        """,
        (organisation_id, user_id),
    ).fetchone()

    return result is not None


def _require_organisation_admin(
    connection: Any,
    organisation_id: str,
    user_id: str,
) -> None:
    """Require active Organisation Admin authority."""
    if not _is_organisation_admin(
        connection, organisation_id, user_id
    ):
        raise PermissionError(
            "Only an active Organisation Admin can perform this action."
        )


def _get_project(
    connection: Any,
    project_id: str,
) -> dict[str, Any]:
    """Retrieve a project or raise an error."""
    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT
            id,
            organisation_id,
            name,
            description,
            status,
            created_by,
            created_at,
            updated_at
        FROM projects
        WHERE id = {p}
        """,
        (project_id,),
    ).fetchone()

    if result is None:
        raise ValueError("Project was not found.")

    return dict(result)


def _require_project_admin(
    connection: Any,
    project_id: str,
    user_id: str,
) -> None:
    """Require an active Project Admin or Organisation Admin."""
    project = _get_project(connection, project_id)
    organisation_id = project["organisation_id"]

    _require_active_organisation(connection, organisation_id)

    if _is_organisation_admin(connection, organisation_id, user_id):
        return

    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT id
        FROM project_memberships
        WHERE project_id = {p}
          AND user_id = {p}
          AND role = 'project_admin'
          AND status = 'active'
        """,
        (project_id, user_id),
    ).fetchone()

    if result is None:
        raise PermissionError(
            "Only an active Project Admin or Organisation Admin "
            "can perform this action."
        )


def _require_project_access(
    connection: Any,
    project_id: str,
    user_id: str,
) -> None:
    """Require active project membership or Organisation Admin authority."""
    project = _get_project(connection, project_id)
    organisation_id = project["organisation_id"]

    _require_active_organisation(connection, organisation_id)

    if _is_organisation_admin(connection, organisation_id, user_id):
        return

    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT id
        FROM project_memberships
        WHERE project_id = {p}
          AND user_id = {p}
          AND status = 'active'
        """,
        (project_id, user_id),
    ).fetchone()

    if result is None:
        raise PermissionError(
            "You do not have active membership in this project."
        )


def _count_active_project_admins(
    connection: Any,
    project_id: str,
) -> int:
    """Count active Project Admin memberships."""
    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM project_memberships
        WHERE project_id = {p}
          AND role = 'project_admin'
          AND status = 'active'
        """,
        (project_id,),
    ).fetchone()

    return int(result["total"])


def create_project(
    organisation_id: str,
    name: str,
    created_by: str,
    description: str | None = None,
) -> str:
    """
    Create a project and make its creator the first Project Admin.

    Only an active Organisation Admin can create a project.

    Returns:
        The new project ID.
    """
    organisation_id = _normalise_text(
        organisation_id, "Organisation ID"
    )
    name = _normalise_text(name, "Project name")
    created_by = _normalise_text(created_by, "Creator user ID")
    description = _normalise_optional_text(
        description, "Project description"
    )

    project_id = _new_id()
    membership_id = _new_id()
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, created_by)
        _require_active_organisation(connection, organisation_id)
        _require_organisation_admin(
            connection, organisation_id, created_by
        )

        connection.execute(
            f"""
            INSERT INTO projects (
                id,
                organisation_id,
                name,
                description,
                status,
                created_by
            )
            VALUES ({p}, {p}, {p}, {p}, 'active', {p})
            """,
            (
                project_id,
                organisation_id,
                name,
                description,
                created_by,
            ),
        )

        connection.execute(
            f"""
            INSERT INTO project_memberships (
                id,
                project_id,
                user_id,
                role,
                status
            )
            VALUES ({p}, {p}, {p}, 'project_admin', 'active')
            """,
            (membership_id, project_id, created_by),
        )

    return project_id


def list_user_projects(user_id: str) -> list[dict[str, Any]]:
    """List active projects accessible to a user."""
    user_id = _normalise_text(user_id, "User ID")
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, user_id)

        rows = connection.execute(
            f"""
            SELECT DISTINCT
                p.id AS project_id,
                p.organisation_id,
                o.name AS organisation_name,
                p.name AS project_name,
                p.description,
                p.status AS project_status,
                p.created_by,
                p.created_at,
                p.updated_at,
                pm.role AS membership_role
            FROM projects p
            INNER JOIN organisations o
                ON o.id = p.organisation_id
            LEFT JOIN project_memberships pm
                ON pm.project_id = p.id
               AND pm.user_id = {p}
               AND pm.status = 'active'
            LEFT JOIN organisation_memberships om
                ON om.organisation_id = p.organisation_id
               AND om.user_id = {p}
               AND om.role = 'org_admin'
               AND om.status = 'active'
            WHERE o.status = 'active'
              AND p.status != 'archived'
              AND (
                    pm.id IS NOT NULL
                    OR om.id IS NOT NULL
              )
            ORDER BY p.name
            """,
            (user_id, user_id),
        ).fetchall()

    return [dict(row) for row in rows]


def get_project(
    project_id: str,
    requested_by: str,
) -> dict[str, Any]:
    """Retrieve project details after checking access."""
    project_id = _normalise_text(project_id, "Project ID")
    requested_by = _normalise_text(
        requested_by, "Requesting user ID"
    )

    with database_connection() as connection:
        _require_active_user(connection, requested_by)
        _require_project_access(
            connection, project_id, requested_by
        )

        return _get_project(connection, project_id)


def update_project(
    project_id: str,
    updated_by: str,
    name: str | None = None,
    description: str | None = None,
    status: str | None = None,
) -> None:
    """
    Update project details.

    Active Project Admins and Organisation Admins may perform this action.
    """
    project_id = _normalise_text(project_id, "Project ID")
    updated_by = _normalise_text(updated_by, "Updating user ID")

    if name is None and description is None and status is None:
        raise ValueError("At least one project field must be provided.")

    if name is not None:
        name = _normalise_text(name, "Project name")

    if description is not None:
        description = _normalise_optional_text(
            description, "Project description"
        )

    if status is not None:
        status = _validate_choice(
            status, VALID_PROJECT_STATUSES, "Project status"
        )

    updates: list[str] = []
    values: list[Any] = []
    p = _placeholder()

    if name is not None:
        updates.append(f"name = {p}")
        values.append(name)

    if description is not None:
        updates.append(f"description = {p}")
        values.append(description)

    if status is not None:
        updates.append(f"status = {p}")
        values.append(status)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    values.append(project_id)

    with database_connection() as connection:
        _require_active_user(connection, updated_by)
        _require_project_admin(
            connection, project_id, updated_by
        )

        connection.execute(
            f"""
            UPDATE projects
            SET {", ".join(updates)}
            WHERE id = {p}
            """,
            tuple(values),
        )


def add_project_member(
    project_id: str,
    user_id: str,
    added_by: str,
    role: str = "project_member",
) -> str:
    """
    Add an active organisation member to a project.

    Active Project Admins and Organisation Admins may add members.

    Returns:
        The new project membership ID.
    """
    project_id = _normalise_text(project_id, "Project ID")
    user_id = _normalise_text(user_id, "User ID")
    added_by = _normalise_text(added_by, "Administrator user ID")
    role = _validate_choice(
        role, VALID_PROJECT_ROLES, "Project membership role"
    )

    membership_id = _new_id()
    p = _placeholder()

    with database_connection() as connection:
        project = _get_project(connection, project_id)
        organisation_id = project["organisation_id"]

        _require_active_user(connection, added_by)
        _require_active_user(connection, user_id)
        _require_project_admin(connection, project_id, added_by)
        _require_active_organisation(connection, organisation_id)
        _require_active_organisation_member(
            connection, organisation_id, user_id
        )

        existing = connection.execute(
            f"""
            SELECT id
            FROM project_memberships
            WHERE project_id = {p}
              AND user_id = {p}
            """,
            (project_id, user_id),
        ).fetchone()

        if existing is not None:
            raise ValueError(
                "This user already has a membership record in the project."
            )

        connection.execute(
            f"""
            INSERT INTO project_memberships (
                id,
                project_id,
                user_id,
                role,
                status
            )
            VALUES ({p}, {p}, {p}, {p}, 'active')
            """,
            (membership_id, project_id, user_id, role),
        )

    return membership_id


def list_project_members(
    project_id: str,
    requested_by: str,
) -> list[dict[str, Any]]:
    """List project members for an active project administrator."""
    project_id = _normalise_text(project_id, "Project ID")
    requested_by = _normalise_text(
        requested_by, "Requesting user ID"
    )
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, requested_by)
        _require_project_admin(
            connection, project_id, requested_by
        )

        rows = connection.execute(
            f"""
            SELECT
                u.id AS user_id,
                u.username,
                u.email,
                u.full_name,
                pm.id AS membership_id,
                pm.role AS membership_role,
                pm.status AS membership_status,
                pm.joined_at
            FROM project_memberships pm
            INNER JOIN users u
                ON u.id = pm.user_id
            WHERE pm.project_id = {p}
            ORDER BY u.full_name
            """,
            (project_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def change_project_membership_role(
    project_id: str,
    user_id: str,
    changed_by: str,
    new_role: str,
) -> None:
    """
    Change a project membership role.

    The last active Project Admin cannot be demoted.
    """
    project_id = _normalise_text(project_id, "Project ID")
    user_id = _normalise_text(user_id, "User ID")
    changed_by = _normalise_text(
        changed_by, "Administrator user ID"
    )
    new_role = _validate_choice(
        new_role, VALID_PROJECT_ROLES, "Project membership role"
    )
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, changed_by)
        _require_project_admin(
            connection, project_id, changed_by
        )

        membership = connection.execute(
            f"""
            SELECT id, role, status
            FROM project_memberships
            WHERE project_id = {p}
              AND user_id = {p}
            """,
            (project_id, user_id),
        ).fetchone()

        if membership is None:
            raise ValueError("Project membership record was not found.")

        if membership["status"] != "active":
            raise ValueError("Only active memberships can be changed.")

        if (
            membership["role"] == "project_admin"
            and new_role != "project_admin"
            and _count_active_project_admins(
                connection, project_id
            ) <= 1
        ):
            raise ValueError(
                "The last active Project Admin cannot be demoted."
            )

        connection.execute(
            f"""
            UPDATE project_memberships
            SET role = {p}
            WHERE project_id = {p}
              AND user_id = {p}
            """,
            (new_role, project_id, user_id),
        )


def change_project_membership_status(
    project_id: str,
    user_id: str,
    changed_by: str,
    new_status: str,
) -> None:
    """
    Change a project membership status.

    The last active Project Admin cannot be suspended or made inactive.
    """
    project_id = _normalise_text(project_id, "Project ID")
    user_id = _normalise_text(user_id, "User ID")
    changed_by = _normalise_text(
        changed_by, "Administrator user ID"
    )
    new_status = _validate_choice(
        new_status,
        VALID_MEMBERSHIP_STATUSES,
        "Project membership status",
    )
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, changed_by)
        _require_project_admin(
            connection, project_id, changed_by
        )

        membership = connection.execute(
            f"""
            SELECT role, status
            FROM project_memberships
            WHERE project_id = {p}
              AND user_id = {p}
            """,
            (project_id, user_id),
        ).fetchone()

        if membership is None:
            raise ValueError("Project membership record was not found.")

        if (
            membership["role"] == "project_admin"
            and membership["status"] == "active"
            and new_status != "active"
            and _count_active_project_admins(
                connection, project_id
            ) <= 1
        ):
            raise ValueError(
                "The last active Project Admin cannot be suspended "
                "or made inactive."
            )

        connection.execute(
            f"""
            UPDATE project_memberships
            SET status = {p}
            WHERE project_id = {p}
              AND user_id = {p}
            """,
            (new_status, project_id, user_id),
        )


def remove_project_member(
    project_id: str,
    user_id: str,
    removed_by: str,
) -> None:
    """
    Remove a user's project membership without deleting their account.

    The last active Project Admin cannot be removed.
    """
    project_id = _normalise_text(project_id, "Project ID")
    user_id = _normalise_text(user_id, "User ID")
    removed_by = _normalise_text(
        removed_by, "Administrator user ID"
    )
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, removed_by)
        _require_project_admin(
            connection, project_id, removed_by
        )

        membership = connection.execute(
            f"""
            SELECT role, status
            FROM project_memberships
            WHERE project_id = {p}
              AND user_id = {p}
            """,
            (project_id, user_id),
        ).fetchone()

        if membership is None:
            raise ValueError("Project membership record was not found.")

        if (
            membership["role"] == "project_admin"
            and membership["status"] == "active"
            and _count_active_project_admins(
                connection, project_id
            ) <= 1
        ):
            raise ValueError(
                "The last active Project Admin cannot be removed."
            )

        connection.execute(
            f"""
            DELETE FROM project_memberships
            WHERE project_id = {p}
              AND user_id = {p}
            """,
            (project_id, user_id),
        )
