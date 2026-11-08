"""Regression tests for privileged platform-role authentication."""

from timan_intelligence.security.auth import VALID_ROLES
from timan_intelligence.security.session import (
    VALID_SESSION_ROLES,
    SessionManager,
)


def test_super_admin_is_an_authentication_role():
    assert "super_admin" in VALID_ROLES


def test_super_admin_is_a_valid_session_role():
    assert "super_admin" in VALID_SESSION_ROLES


def test_super_admin_can_establish_a_versioned_session():
    state = {}
    manager = SessionManager(
        require_versioned_sessions=True,
        session_version_loader=lambda user_id: 0,
    )

    manager.create_session(
        state,
        username="platform-owner",
        role="super_admin",
        user_id="user-super-admin",
    )

    assert state["authenticated"] is True
    assert state["role"] == "super_admin"
    assert manager.is_valid(state) is True
