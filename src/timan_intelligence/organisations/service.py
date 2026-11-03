
"""Organisation and membership services for TimanStat."""

from __future__ import annotations

import re
import uuid
from typing import Any

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


VALID_ORGANISATION_ROLES = {"org_admin", "org_member"}


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


def _require_organisation_admin(
    connection: Any,
    organisation_id: str,
    user_id: str,
) -> None:
    """Verify that a user is an active administrator of an organisation."""

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

    if contact_email:
        contact_email = contact_email.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", contact_email):
            raise ValueError("Enter a valid organisation contact email.")

    organisation_id = _new_id()
    membership_id = _new_id()
    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT id, is_active
            FROM users
            WHERE id = {p}
            """,
            (created_by,),
        ).fetchone()

        if user is None or not user["is_active"]:
            raise PermissionError(
                "An active individual account is required to register an organisation."
            )

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
    Returns the membership ID.
    """

    organisation_id = _normalise_text(
        organisation_id, "Organisation ID"
    )
    user_id = _normalise_text(user_id, "User ID")
    added_by = _normalise_text(added_by, "Administrator user ID")

    role = role.strip().lower()

    if role not in VALID_ORGANISATION_ROLES:
        raise ValueError("Invalid organisation membership role.")

    membership_id = _new_id()
    p = _placeholder()

    with database_connection() as connection:
        _require_organisation_admin(
            connection,
            organisation_id,
            added_by,
        )

        organisation = connection.execute(
            f"""
            SELECT id
            FROM organisations
            WHERE id = {p}
              AND status = 'active'
            """,
            (organisation_id,),
        ).fetchone()

        if organisation is None:
            raise ValueError("Organisation does not exist or is inactive.")

        user = connection.execute(
            f"""
            SELECT id
            FROM users
            WHERE id = {p}
              AND is_active = TRUE
            """,
            (user_id,),
        ).fetchone()

        if user is None:
            raise ValueError("The individual user does not exist or is inactive.")

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
    """Return all active organisations associated with an individual user."""

    user_id = _normalise_text(user_id, "User ID")
    p = _placeholder()

    with database_connection() as connection:
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
