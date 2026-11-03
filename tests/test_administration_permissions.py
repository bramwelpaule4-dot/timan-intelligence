
"""Tests for TimanStat platform role permissions and access control."""

import pytest

from timan_intelligence.administration.permissions import (
    PLATFORM_ROLES,
    PERMISSIONS,
    ROLE_PERMISSIONS,
    normalise_role,
    get_role_permissions,
    has_permission,
    require_permission,
    require_any_permission,
    can_manage_platform_role,
)


def test_supported_platform_roles():
    """All four platform roles should be recognised."""

    assert PLATFORM_ROLES == {
        "super_admin",
        "admin",
        "developer",
        "user",
    }


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        ("SUPER_ADMIN", "super_admin"),
        ("Admin", "admin"),
        ("Developer", "developer"),
        ("USER", "user"),
        ("  admin  ", "admin"),
    ],
)
def test_role_normalisation(role, expected):
    assert normalise_role(role) == expected


@pytest.mark.parametrize(
    "invalid_role",
    ["unknown_role", "", None, 123],
)
def test_invalid_role_is_rejected(invalid_role):
    with pytest.raises(ValueError):
        normalise_role(invalid_role)


def test_super_admin_has_all_permissions():
    """Super Admin should have every registered platform permission."""

    assert get_role_permissions("super_admin") == PERMISSIONS


def test_admin_has_expected_permissions():
    assert get_role_permissions("admin") == {
        "manage_users",
        "view_platform_audit_logs",
        "view_system_health",
    }


def test_developer_has_expected_permissions():
    assert get_role_permissions("developer") == {
        "view_system_health",
        "use_developer_tools",
    }


def test_user_has_expected_permissions():
    assert get_role_permissions("user") == {
        "manage_own_workspace",
        "manage_own_projects",
        "run_statistical_analysis",
        "manage_own_datasets",
    }


def test_get_role_permissions_returns_independent_set():
    """Changing a returned set must not alter the role definitions."""

    permissions = get_role_permissions("user")
    permissions.add("manage_platform_settings")

    assert (
        "manage_platform_settings"
        not in ROLE_PERMISSIONS["user"]
    )


@pytest.mark.parametrize(
    "permission",
    [
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
    ],
)
def test_super_admin_has_each_registered_permission(permission):
    assert has_permission("super_admin", permission) is True


def test_admin_can_manage_users():
    assert has_permission("admin", "manage_users") is True


def test_admin_cannot_manage_platform_settings():
    assert has_permission("admin", "manage_platform_settings") is False


def test_developer_can_use_developer_tools():
    assert has_permission("developer", "use_developer_tools") is True


def test_developer_cannot_manage_users():
    assert has_permission("developer", "manage_users") is False


def test_user_can_run_statistical_analysis():
    assert has_permission("user", "run_statistical_analysis") is True


def test_user_cannot_manage_platform_roles():
    assert has_permission("user", "manage_roles") is False


def test_unknown_permission_is_not_granted():
    assert has_permission(
        "user",
        "permission_that_does_not_exist",
    ) is False


def test_non_text_permission_is_not_granted():
    assert has_permission("user", None) is False


def test_require_permission_allows_authorised_role():
    require_permission(
        "super_admin",
        "manage_platform_settings",
    )


def test_require_permission_rejects_unauthorised_role():
    with pytest.raises(PermissionError):
        require_permission(
            "user",
            "manage_platform_settings",
        )


def test_require_any_permission_allows_matching_permission():
    require_any_permission(
        "admin",
        [
            "manage_users",
            "manage_platform_settings",
        ],
    )


def test_require_any_permission_rejects_no_matching_permission():
    with pytest.raises(PermissionError):
        require_any_permission(
            "user",
            [
                "manage_users",
                "manage_platform_settings",
            ],
        )


def test_super_admin_can_assign_admin_role():
    assert can_manage_platform_role(
        actor_role="super_admin",
        target_role="user",
        new_role="admin",
    ) is True


def test_super_admin_can_assign_developer_role():
    assert can_manage_platform_role(
        actor_role="super_admin",
        target_role="user",
        new_role="developer",
    ) is True


def test_admin_cannot_assign_super_admin_role():
    assert can_manage_platform_role(
        actor_role="admin",
        target_role="user",
        new_role="super_admin",
    ) is False


def test_developer_cannot_assign_platform_roles():
    assert can_manage_platform_role(
        actor_role="developer",
        target_role="user",
        new_role="admin",
    ) is False


def test_user_cannot_assign_platform_roles():
    assert can_manage_platform_role(
        actor_role="user",
        target_role="user",
        new_role="admin",
    ) is False


def test_super_admin_cannot_demote_another_super_admin():
    assert can_manage_platform_role(
        actor_role="super_admin",
        target_role="super_admin",
        new_role="admin",
    ) is False


def test_super_admin_can_retain_another_super_admin_role():
    assert can_manage_platform_role(
        actor_role="super_admin",
        target_role="super_admin",
        new_role="super_admin",
    ) is True
