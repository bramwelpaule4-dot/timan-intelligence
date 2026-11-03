
"""Platform user administration services for TimanStat."""

from __future__ import annotations

from typing import Any

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)
from timan_intelligence.administration.permissions import (
    normalise_role,
)


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""
    return "%s" if get_database_type() == "postgresql" else "?"


def _require_super_admin(actor_role: str) -> None:
    """Restrict sensitive platform administration to Super Admins."""

    if normalise_role(actor_role) != "super_admin":
        raise PermissionError(
            "Only a Super Admin can perform this action."
        )


def list_users(
    actor_role: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List platform users without exposing password hashes."""

    if normalise_role(actor_role) not in {"super_admin", "admin"}:
        raise PermissionError(
            "You do not have permission to view platform users."
        )

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("Limit must be an integer.")

    if limit < 1 or limit > 1000:
        raise ValueError("Limit must be between 1 and 1000.")

    p = _placeholder()

    with database_connection() as connection:
        rows = connection.execute(
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
                updated_at,
                last_login_at
            FROM users
            ORDER BY created_at DESC
            LIMIT {p}
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_user_details(
    actor_role: str,
    user_id: str,
) -> dict[str, Any] | None:
    """Retrieve a user's administrative account details."""

    if normalise_role(actor_role) not in {"super_admin", "admin"}:
        raise PermissionError(
            "You do not have permission to view user details."
        )

    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("User ID is required.")

    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
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
                updated_at,
                last_login_at
            FROM users
            WHERE id = {p}
            """,
            (user_id.strip(),),
        ).fetchone()

    return dict(user) if user is not None else None


def change_user_role(
    actor_role: str,
    actor_user_id: str,
    target_user_id: str,
    new_role: str,
) -> None:
    """Change a user's platform role under Super Admin authority."""

    _require_super_admin(actor_role)

    if not actor_user_id or not actor_user_id.strip():
        raise ValueError("Acting administrator ID is required.")

    if not target_user_id or not target_user_id.strip():
        raise ValueError("Target user ID is required.")

    new_role = normalise_role(new_role)

    if (
        actor_user_id.strip() == target_user_id.strip()
        and new_role != "super_admin"
    ):
        raise ValueError(
            "A Super Admin cannot change their own role."
        )

    p = _placeholder()

    with database_connection() as connection:
        target = connection.execute(
            f"""
            SELECT id, role, is_active
            FROM users
            WHERE id = {p}
            """,
            (target_user_id.strip(),),
        ).fetchone()

        if target is None:
            raise ValueError("Target user account was not found.")

        if (
            target["role"] == "super_admin"
            and target["is_active"]
            and new_role != "super_admin"
        ):
            count = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM users
                WHERE role = 'super_admin'
                  AND is_active = TRUE
                """
            ).fetchone()["total"]

            if int(count) <= 1:
                raise ValueError(
                    "The last active Super Admin cannot be demoted."
                )

        connection.execute(
            f"""
            UPDATE users
            SET role = {p},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
            """,
            (new_role, target_user_id.strip()),
        )


def set_user_active_status(
    actor_role: str,
    actor_user_id: str,
    target_user_id: str,
    is_active: bool,
) -> None:
    """Activate or deactivate a user account."""

    _require_super_admin(actor_role)

    if not isinstance(is_active, bool):
        raise ValueError("Account status must be True or False.")

    if not actor_user_id or not actor_user_id.strip():
        raise ValueError("Acting administrator ID is required.")

    if not target_user_id or not target_user_id.strip():
        raise ValueError("Target user ID is required.")

    p = _placeholder()

    with database_connection() as connection:
        target = connection.execute(
            f"""
            SELECT id, role, is_active
            FROM users
            WHERE id = {p}
            """,
            (target_user_id.strip(),),
        ).fetchone()

        if target is None:
            raise ValueError("Target user account was not found.")

        if (
            not is_active
            and target["role"] == "super_admin"
            and target["is_active"]
        ):
            count = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM users
                WHERE role = 'super_admin'
                  AND is_active = TRUE
                """
            ).fetchone()["total"]

            if int(count) <= 1:
                raise ValueError(
                    "The last active Super Admin cannot be deactivated."
                )

        connection.execute(
            f"""
            UPDATE users
            SET is_active = {p},
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
            """,
            (is_active, target_user_id.strip()),
        )
