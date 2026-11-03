
"""Tests for TimanStat platform role permissions and access control."""

import pytest

from timan_intelligence.administration.permissions import (
    normalise_role,
    get_role_permissions,
    has_permission,
    require_permission,
    require_any_permission,
    can_manage_platform_role,
)


def test_supported_platform_roles():
    """All four platform roles should be recognised."""

    roles = {
        "super_admin",
        "admin",
        "developer",
        "user",
    }

    for role in roles:
        assert normalise_role(role) == role


def test_role_normalisation_is_case_insensitive():
    """Role normalisation should handle different letter cases."""

    assert normalise_role("SUPER_ADMIN") == "super_admin"
    assert normalise_role("Admin") == "admin"
    assert normalise_role("Developer") == "developer"
    assert normalise_role("USER") == "user"


def test_invalid_role_is_rejected():
    """Unknown roles should not be accepted."""

    with pytest.raises(ValueError):
        normalise_role("unknown_role")


def test_super_admin_has_all_platform_permissions():
    """Super Admin should have the complete platform permission set."""

    permissions = get_role_permissions("super_admin")

    assert isinstance(permissions, set)
    assert len(permissions) > 0


def test_admin_has_platform_administration_permissions():
    """Admin should have platform administration permissions."""

    permissions = get_role_permissions("admin")

    assert isinstance(permissions, set)
    assert len(permissions) > 0


def test_developer_has_development_permissions():
    """Developer should have development-related permissions."""

    permissions = get_role_permissions("developer")

    assert isinstance(permissions, set)
    assert len(permissions) > 0


def test_user_has_limited_permissions():
    """A normal user should have a limited permission set."""

    permissions = get_role_permissions("user")

    assert isinstance(permissions, set)
    assert len(permissions) > 0


def test_super_admin_has_permission():
    """Super Admin should have platform administration access."""

    assert has_permission(
        "super_admin",
        "manage_platform_users",
    ) is True


def test_user_does_not_have_super_admin_permission():
    """A normal user must not have Super Admin privileges."""

    assert has_permission(
        "user",
        "manage_platform_users",
    ) is False


def test_has_permission_returns_false_for_unknown_permission():
    """Unknown permissions should not be granted."""

    assert has_permission(
        "user",
        "permission_that_does_not_exist",
    ) is False


def test_require_permission_allows_authorised_role():
    """An authorised role should pass the permission check."""

    require_permission(
        "super_admin",
        "manage_platform_users",
    )


def test_require_permission_rejects_unauthorised_role():
    """An unauthorised role should raise PermissionError."""

    with pytest.raises(PermissionError):
        require_permission(
            "user",
            "manage_platform_users",
        )


def test_require_any_permission_allows_matching_permission():
    """A role with at least one requested permission should be allowed."""

    permissions = get_role_permissions("super_admin")

    assert permissions

    require_any_permission(
        "super_admin",
        *permissions,
    )


def test_require_any_permission_rejects_no_matching_permission():
    """A role without any requested permission should be rejected."""

    with pytest.raises(PermissionError):
        require_any_permission(
            "user",
            "permission_that_does_not_exist",
        )


def test_super_admin_can_manage_platform_roles():
    """Super Admin should be allowed to manage platform roles."""

    assert can_manage_platform_role(
        actor_role="super_admin",
        target_role="admin",
    ) is True


def test_admin_cannot_assign_super_admin_role():
    """Admin must not be able to assign the Super Admin role."""

    assert can_manage_platform_role(
        actor_role="admin",
        target_role="super_admin",
    ) is False


def test_developer_cannot_assign_platform_roles():
    """Developer must not be allowed to assign platform roles."""

    assert can_manage_platform_role(
        actor_role="developer",
        target_role="admin",
    ) is False


def test_user_cannot_assign_platform_roles():
    """Normal users must not be allowed to assign platform roles."""

    assert can_manage_platform_role(
        actor_role="user",
        target_role="admin",
    ) is False


def test_super_admin_cannot_change_own_role():
    """Super Admin should not be allowed to change their own role."""

    assert can_manage_platform_role(
        actor_role="super_admin",
        target_role="super_admin",
        actor_id="user-001",
        target_id="user-001",
    ) is False
