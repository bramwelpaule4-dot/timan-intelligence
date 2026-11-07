
"""Organisation and membership services for TimanStat."""

from __future__ import annotations

import re
import uuid
from typing import Any

from timan_intelligence.entitlements.plans import get_limit
from timan_intelligence.entitlements.subscriptions import get_effective_plan_code

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


VALID_ORGANISATION_ROLES = {"org_admin", "org_member"}
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


def _validate_email(email: str | None) -> str | None:
    """Validate and normalise an optional email address."""
    if email is None or not email.strip():
        return None

    email = email.strip().lower()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid organisation contact email.")

    return email


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
        raise ValueError(
            "The individual user account does not exist or is inactive."
        )


def _require_organisation_admin(
    connection: Any,
    organisation_id: str,
    user_id: str,
) -> None:
    """Verify that a user is an active administrator of an organisation."""

    try:
        _require_active_user(connection, user_id)
    except ValueError as exc:
        raise PermissionError(
            "Only an active Organisation Admin can perform this action."
        ) from exc

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

    if result is None:
        raise PermissionError(
            "Only an active Organisation Admin can perform this action."
        )


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


def _count_active_organisation_admins(
    connection: Any,
    organisation_id: str,
) -> int:
    """Count active Organisation Admin memberships."""

    p = _placeholder()

    result = connection.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM organisation_memberships
        WHERE organisation_id = {p}
          AND role = 'org_admin'
          AND status = 'active'
        """,
        (organisation_id,),
    ).fetchone()

    return int(result["total"])


def create_organisation(
    name: str,
    created_by: str,
    organisation_type: str | None = None,
    registration_number: str | None = None,
    contact_email: str | None = None,
    country: str | None = None,
) -> str:
    """
    Create an organisation and make its creator the first Organisation Admin.

    The creator must already have an active individual user account.

    Returns:
        The new organisation ID.
    """

    name = _normalise_text(name, "Organisation name")
    created_by = _normalise_text(created_by, "Creator user ID")
    contact_email = _validate_email(contact_email)

    organisation_id = _new_id()
    membership_id = _new_id()
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, created_by)

        connection.execute(
            f"""
            INSERT INTO organisations (
                id,
                name,
                organisation_type,
                registration_number,
                contact_email,
                country,
                status,
                created_by
            )
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, 'active', {p})
            """,
            (
                organisation_id,
                name,
                organisation_type,
                registration_number,
                contact_email,
                country,
                created_by,
            ),
        )

        connection.execute(
            f"""
            INSERT INTO organisation_memberships (
                id,
                organisation_id,
                user_id,
                role,
                status
            )
            VALUES ({p}, {p}, {p}, 'org_admin', 'active')
            """,
            (
                membership_id,
                organisation_id,
                created_by,
            ),
        )

    return organisation_id


def add_organisation_member(
    organisation_id: str,
    user_id: str,
    added_by: str,
    role: str = "org_member",
) -> str:
    """
    Add an existing individual user to an organisation.

    Only an active Organisation Admin can add members.

    Returns:
        The new membership ID.
    """

    organisation_id = _normalise_text(
        organisation_id, "Organisation ID"
    )
    user_id = _normalise_text(user_id, "User ID")
    added_by = _normalise_text(added_by, "Administrator user ID")

    if not isinstance(role, str):
        raise ValueError("Membership role must be text.")

    role = role.strip().lower()

    if role not in VALID_ORGANISATION_ROLES:
        raise ValueError("Invalid organisation membership role.")

    membership_id = _new_id()
    p = _placeholder()

    with database_connection() as connection:
        _require_organisation_admin(connection, organisation_id, added_by)
        _require_active_organisation(connection, organisation_id)
        _require_active_user(connection, user_id)

        existing = connection.execute(
            f"""
            SELECT id
            FROM organisation_memberships
            WHERE organisation_id = {p}
              AND user_id = {p}
            """,
            (organisation_id, user_id),
        ).fetchone()

        if existing is not None:
            raise ValueError(
                "This user already has a membership record in the organisation."
            )

        plan_code = get_effective_plan_code(
            user_id=added_by, organisation_id=organisation_id
        )
        member_limit = get_limit(plan_code, "max_team_members")
        if member_limit is not None:
            active_members = connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM organisation_memberships
                WHERE organisation_id = {p} AND status = 'active'
                """,
                (organisation_id,),
            ).fetchone()
            current_members = int(active_members["total"])
            if current_members >= member_limit:
                raise ValueError(
                    f"The {plan_code.title()} plan allows {member_limit} active "
                    f"team member(s); this organisation already has {current_members}. "
                    "Upgrade the organisation plan to add more members."
                )

        connection.execute(
            f"""
            INSERT INTO organisation_memberships (
                id,
                organisation_id,
                user_id,
                role,
                status
            )
            VALUES ({p}, {p}, {p}, {p}, 'active')
            """,
            (
                membership_id,
                organisation_id,
                user_id,
                role,
            ),
        )

    return membership_id


def list_user_organisations(user_id: str) -> list[dict[str, Any]]:
    """Return all active organisations associated with an active user."""

    user_id = _normalise_text(user_id, "User ID")
    p = _placeholder()

    with database_connection() as connection:
        _require_active_user(connection, user_id)

        rows = connection.execute(
            f"""
            SELECT
                o.id AS organisation_id,
                o.name AS organisation_name,
                o.organisation_type,
                o.country,
                m.role AS membership_role,
                m.status AS membership_status,
                m.joined_at
            FROM organisations o
            INNER JOIN organisation_memberships m
                ON o.id = m.organisation_id
            WHERE m.user_id = {p}
              AND m.status = 'active'
              AND o.status = 'active'
            ORDER BY o.name
            """,
            (user_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def list_organisation_members(
    organisation_id: str,
    requested_by: str,
) -> list[dict[str, Any]]:
    """
    List members of an organisation.

    Only an active Organisation Admin can view the membership list.
    """

    organisation_id = _normalise_text(
        organisation_id, "Organisation ID"
    )
    requested_by = _normalise_text(
        requested_by, "Requesting user ID"
    )
    p = _placeholder()

    with database_connection() as connection:
        _require_organisation_admin(
            connection, organisation_id, requested_by
        )
        _require_active_organisation(connection, organisation_id)

        rows = connection.execute(
            f"""
            SELECT
                u.id AS user_id,
                u.username,
                u.email,
                u.full_name,
                m.id AS membership_id,
                m.role AS membership_role,
                m.status AS membership_status,
                m.joined_at
            FROM organisation_memberships m
            INNER JOIN users u ON u.id = m.user_id
            WHERE m.organisation_id = {p}
            ORDER BY u.full_name
            """,
            (organisation_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def change_membership_role(
    organisation_id: str,
    user_id: str,
    changed_by: str,
    new_role: str,
) -> None:
    """
    Change a user's role within an organisation.

    Only an active Organisation Admin can perform this action.
    The last active Organisation Admin cannot be demoted.
    """

    organisation_id = _normalise_text(
        organisation_id, "Organisation ID"
    )
    user_id = _normalise_text(user_id, "User ID")
    changed_by = _normalise_text(changed_by, "Administrator user ID")

    if not isinstance(new_role, str):
        raise ValueError("Membership role must be text.")

    new_role = new_role.strip().lower()

    if new_role not in VALID_ORGANISATION_ROLES:
        raise ValueError("Invalid organisation membership role.")

    p = _placeholder()

    with database_connection() as connection:
        _require_organisation_admin(connection, organisation_id, changed_by)
        _require_active_organisation(connection, organisation_id)

        membership = connection.execute(
            f"""
            SELECT id, role, status
            FROM organisation_memberships
            WHERE organisation_id = {p}
              AND user_id = {p}
            """,
            (organisation_id, user_id),
        ).fetchone()

        if membership is None:
            raise ValueError("Membership record was not found.")

        if membership["status"] != "active":
            raise ValueError("Only active memberships can be changed.")

        if (
            membership["role"] == "org_admin"
            and new_role != "org_admin"
            and _count_active_organisation_admins(
                connection, organisation_id
            ) <= 1
        ):
            raise ValueError(
                "The last active Organisation Admin cannot be demoted."
            )

        connection.execute(
            f"""
            UPDATE organisation_memberships
            SET role = {p}
            WHERE organisation_id = {p}
              AND user_id = {p}
            """,
            (new_role, organisation_id, user_id),
        )


def change_membership_status(
    organisation_id: str,
    user_id: str,
    changed_by: str,
    new_status: str,
) -> None:
    """
    Change a membership's status.

    Supported statuses: active, pending and suspended.
    The last active Organisation Admin cannot be suspended.
    """

    organisation_id = _normalise_text(
        organisation_id, "Organisation ID"
    )
    user_id = _normalise_text(user_id, "User ID")
    changed_by = _normalise_text(changed_by, "Administrator user ID")

    if not isinstance(new_status, str):
        raise ValueError("Membership status must be text.")

    new_status = new_status.strip().lower()

    if new_status not in VALID_MEMBERSHIP_STATUSES:
        raise ValueError("Invalid membership status.")

    p = _placeholder()

    with database_connection() as connection:
        _require_organisation_admin(connection, organisation_id, changed_by)
        _require_active_organisation(connection, organisation_id)

        membership = connection.execute(
            f"""
            SELECT role, status
            FROM organisation_memberships
            WHERE organisation_id = {p}
              AND user_id = {p}
            """,
            (organisation_id, user_id),
        ).fetchone()

        if membership is None:
            raise ValueError("Membership record was not found.")

        if (
            membership["role"] == "org_admin"
            and membership["status"] == "active"
            and new_status != "active"
            and _count_active_organisation_admins(
                connection, organisation_id
            ) <= 1
        ):
            raise ValueError(
                "The last active Organisation Admin cannot be suspended "
                "or made inactive."
            )

        connection.execute(
            f"""
            UPDATE organisation_memberships
            SET status = {p}
            WHERE organisation_id = {p}
              AND user_id = {p}
            """,
            (new_status, organisation_id, user_id),
        )


def remove_organisation_member(
    organisation_id: str,
    user_id: str,
    removed_by: str,
) -> None:
    """
    Remove a user's membership from an organisation.

    This does not delete the individual's TimanStat account.
    The last active Organisation Admin cannot be removed.
    """

    organisation_id = _normalise_text(
        organisation_id, "Organisation ID"
    )
    user_id = _normalise_text(user_id, "User ID")
    removed_by = _normalise_text(removed_by, "Administrator user ID")

    p = _placeholder()

    with database_connection() as connection:
        _require_organisation_admin(connection, organisation_id, removed_by)
        _require_active_organisation(connection, organisation_id)

        membership = connection.execute(
            f"""
            SELECT role, status
            FROM organisation_memberships
            WHERE organisation_id = {p}
              AND user_id = {p}
            """,
            (organisation_id, user_id),
        ).fetchone()

        if membership is None:
            raise ValueError("Membership record was not found.")

        if (
            membership["role"] == "org_admin"
            and membership["status"] == "active"
            and _count_active_organisation_admins(
                connection, organisation_id
            ) <= 1
        ):
            raise ValueError(
                "The last active Organisation Admin cannot be removed."
            )

        connection.execute(
            f"""
            DELETE FROM organisation_memberships
            WHERE organisation_id = {p}
              AND user_id = {p}
            """,
            (organisation_id, user_id),
        )
