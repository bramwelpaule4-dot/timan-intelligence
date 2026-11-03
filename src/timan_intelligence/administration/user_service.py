"""Platform user administration services."""

from datetime import datetime, timezone
from typing import Any

from timan_intelligence.administration.permissions import normalise_role
from timan_intelligence.database.connection import database_connection


def _placeholder() -> str:
    """Return the database-specific SQL placeholder."""
    with database_connection() as connection:
        if connection.__class__.__module__.startswith("psycopg"):
            return "%s"
    return "?"


def _require_super_admin(actor_role: str) -> None:
    """Require the super_admin platform role."""
    try:
        role = normalise_role(actor_role)
    except ValueError as exc:
        raise PermissionError(
            "Only a super administrator can perform this action."
        ) from exc

    if role != "super_admin":
        raise PermissionError(
            "Only a super administrator can perform this action."
        )


def _require_user_admin(actor_role: str) -> None:
    """Require an admin or super_admin platform role."""
    try:
        role = normalise_role(actor_role)
    except ValueError as exc:
        raise PermissionError(
            "You do not have permission to view platform users."
        ) from exc

    if role not in {"super_admin", "admin"}:
        raise PermissionError(
            "You do not have permission to view platform users."
        )


def list_users(
    actor_role: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List platform users without exposing password hashes."""
    _require_user_admin(actor_role)

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("Limit must be an integer.")

    if not 1 <= limit <= 1000:
        raise ValueError("Limit must be between 1 and 1000.")

    placeholder = _placeholder()

    with database_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                id,
                username,
                email,
                full_name,
                role,
                is_active,
                email_verified,
                created_at,
                updated_at
            FROM users
            ORDER BY created_at DESC
            LIMIT {placeholder}
            """,
            (limit,),
        )

        return [dict(row) for row in cursor.fetchall()]


def get_user_details(
    actor_role: str,
    user_id: str,
) -> dict[str, Any] | None:
    """Retrieve one platform user's details without password hashes."""
    _require_user_admin(actor_role)

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("User ID is required.")

    placeholder = _placeholder()

    with database_connection() as connection:
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                id,
                username,
                email,
                full_name,
                role,
                is_active,
                email_verified,
                created_at,
                updated_at
            FROM users
            WHERE id = {placeholder}
            """,
            (user_id,),
        )

        row = cursor.fetchone()

    return dict(row) if row else None


def change_user_role(
    actor_role: str,
    actor_user_id: str,
    target_user_id: str,
    new_role: str,
) -> None:
    """Change a platform user's role."""
    _require_super_admin(actor_role)

    if not isinstance(actor_user_id, str) or not actor_user_id.strip():
        raise ValueError("Actor user ID is required.")

    if not isinstance(target_user_id, str) or not target_user_id.strip():
        raise ValueError("Target user ID is required.")

    validated_role = normalise_role(new_role)

    if actor_user_id == target_user_id and validated_role != "super_admin":
        raise ValueError("A super administrator cannot demote their own account.")

    placeholder = _placeholder()

    with database_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            f"""
            SELECT id, role, is_active
            FROM users
            WHERE id = {placeholder}
            """,
            (target_user_id,),
        )

        target = cursor.fetchone()

        if not target:
            raise ValueError("Target user does not exist.")

        if (
            target["role"] == "super_admin"
            and validated_role != "super_admin"
            and bool(target["is_active"])
        ):
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM users
                WHERE role = 'super_admin'
                  AND is_active = TRUE
                """
            )

            result = cursor.fetchone()

            if result["total"] <= 1:
                raise ValueError(
                    "The last active super administrator cannot be demoted."
                )

        cursor.execute(
            f"""
            UPDATE users
            SET role = {placeholder},
                updated_at = {placeholder}
            WHERE id = {placeholder}
            """,
            (
                validated_role,
                datetime.now(timezone.utc).isoformat(),
                target_user_id,
            ),
        )


def set_user_active_status(
    actor_role: str,
    actor_user_id: str,
    target_user_id: str,
    is_active: bool,
) -> None:
    """Activate or deactivate a platform user."""
    _require_super_admin(actor_role)

    if not isinstance(actor_user_id, str) or not actor_user_id.strip():
        raise ValueError("Actor user ID is required.")

    if not isinstance(target_user_id, str) or not target_user_id.strip():
        raise ValueError("Target user ID is required.")

    if not isinstance(is_active, bool):
        raise ValueError("Active status must be a boolean.")

    placeholder = _placeholder()

    with database_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
            f"""
            SELECT id, role, is_active
            FROM users
            WHERE id = {placeholder}
            """,
            (target_user_id,),
        )

        target = cursor.fetchone()

        if not target:
            raise ValueError("Target user does not exist.")

        if (
            target["role"] == "super_admin"
            and bool(target["is_active"])
            and not is_active
        ):
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM users
                WHERE role = 'super_admin'
                  AND is_active = TRUE
                """
            )

            result = cursor.fetchone()

            if result["total"] <= 1:
                raise ValueError(
                    "The last active super administrator cannot be deactivated."
                )

        cursor.execute(
            f"""
            UPDATE users
            SET is_active = {placeholder},
                updated_at = {placeholder}
            WHERE id = {placeholder}
            """,
            (
                is_active,
                datetime.now(timezone.utc).isoformat(),
                target_user_id,
            ),
        )
