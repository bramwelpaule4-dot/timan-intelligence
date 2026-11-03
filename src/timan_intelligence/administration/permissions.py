
"""Platform permission definitions and access-control helpers for TimanStat."""

from __future__ import annotations

from typing import Iterable


PLATFORM_ROLES = {
    "super_admin",
    "admin",
    "developer",
    "user",
}

PERMISSIONS = {
    "manage_platform_settings",
    "manage_platform_admins",
    "manage_users",
    "manage_roles",
    "view_platform_audit_logs",
    "view_system_health",
    "use_developer_tools",
    "manage_own_workspace",
    "manage_own_projects",
    "run_statistical_analysis",
    "manage_own_datasets",
}


ROLE_PERMISSIONS = {
    "super_admin": PERMISSIONS.copy(),

    "admin": {
        "manage_users",
        "view_platform_audit_logs",
        "view_system_health",
    },

    "developer": {
        "view_system_health",
        "use_developer_tools",
    },

    "user": {
        "manage_own_workspace",
        "manage_own_projects",
        "run_statistical_analysis",
        "manage_own_datasets",
    },
}


def normalise_role(role: str) -> str:
    """Validate and normalise a platform role."""

    if not isinstance(role, str):
        raise ValueError("Platform role must be text.")

    role = role.strip().lower()

    if role not in PLATFORM_ROLES:
        raise ValueError("Unrecognised platform role.")

    return role


def get_role_permissions(role: str) -> set[str]:
    """Return the permissions assigned to a platform role."""

    role = normalise_role(role)
    return set(ROLE_PERMISSIONS[role])


def has_permission(role: str, permission: str) -> bool:
    """Check whether a platform role has a specified permission."""

    role = normalise_role(role)

    if not isinstance(permission, str):
        return False

    return permission in ROLE_PERMISSIONS[role]


def require_permission(role: str, permission: str) -> None:
    """Raise an exception when a role lacks a required permission."""

    if not has_permission(role, permission):
        raise PermissionError(
            "You do not have permission to perform this action."
        )


def require_any_permission(
    role: str,
    permissions: Iterable[str],
) -> None:
    """Require at least one permission from a supplied collection."""

    role = normalise_role(role)

    if not any(
        has_permission(role, permission)
        for permission in permissions
    ):
        raise PermissionError(
            "You do not have permission to perform this action."
        )


def can_manage_platform_role(
    actor_role: str,
    target_role: str,
    new_role: str,
) -> bool:
    """
    Determine whether an actor may assign a platform role.

    Only Super Admins may assign or change platform-level roles.
    Super Admins cannot use this function to change their own role.
    """

    actor_role = normalise_role(actor_role)
    target_role = normalise_role(target_role)
    new_role = normalise_role(new_role)

    if actor_role != "super_admin":
        return False

    if target_role == "super_admin" and new_role != "super_admin":
        return False

    return True
