
"""Tests for TimanStat platform user administration services."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.administration.user_service import (
    list_users,
    get_user_details,
    change_user_role,
    set_user_active_status,
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
    """Create test accounts and assign one account Super Admin authority."""

    super_admin_id = register_user(
        username="superadmin",
        email="superadmin@example.com",
        full_name="Super Administrator",
        password="SecureTestPassword123!",
    )

    admin_id = register_user(
        username="platformadmin",
        email="admin@example.com",
        full_name="Platform Administrator",
        password="SecureTestPassword123!",
    )

    developer_id = register_user(
        username="developer",
        email="developer@example.com",
        full_name="Platform Developer",
        password="SecureTestPassword123!",
    )

    user_id = register_user(
        username="normaluser",
        email="user@example.com",
        full_name="Normal User",
        password="SecureTestPassword123!",
    )

    # Promote the first test account to Super Admin.
    # This is test setup, not a public registration capability.
    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            ("super_admin", super_admin_id),
        )

        connection.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            ("admin", admin_id),
        )

        connection.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            ("developer", developer_id),
        )

    return {
        "super_admin": super_admin_id,
        "admin": admin_id,
        "developer": developer_id,
        "user": user_id,
    }


def test_super_admin_can_list_users(test_database, test_users):
    users = list_users(actor_role="super_admin")

    assert len(users) == 4


def test_admin_can_list_users(test_database, test_users):
    users = list_users(actor_role="admin")

    assert len(users) == 4


@pytest.mark.parametrize(
    "role",
    ["developer", "user", "unknown"],
)
def test_unauthorised_roles_cannot_list_users(
    test_database,
    test_users,
    role,
):
    with pytest.raises(PermissionError):
        list_users(actor_role=role)


def test_list_users_does_not_expose_password_hashes(
    test_database,
    test_users,
):
    users = list_users(actor_role="super_admin")

    assert users

    for user in users:
        assert "password_hash" not in user


def test_list_users_respects_limit(test_database, test_users):
    users = list_users(
        actor_role="admin",
        limit=2,
    )

    assert len(users) == 2


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, 1001, 1.5, True, "10"],
)
def test_list_users_rejects_invalid_limit(
    test_database,
    test_users,
    invalid_limit,
):
    with pytest.raises(ValueError):
        list_users(
            actor_role="admin",
            limit=invalid_limit,
        )


def test_super_admin_can_get_user_details(test_database, test_users):
    user_id = test_users["user"]

    details = get_user_details(
        actor_role="super_admin",
        user_id=user_id,
    )

    assert details is not None
    assert details["id"] == user_id
    assert details["username"] == "normaluser"
    assert details["role"] == "user"
    assert "password_hash" not in details


def test_admin_can_get_user_details(test_database, test_users):
    user_id = test_users["user"]

    details = get_user_details(
        actor_role="admin",
        user_id=user_id,
    )

    assert details is not None
    assert details["id"] == user_id


@pytest.mark.parametrize(
    "role",
    ["developer", "user", "unknown"],
)
def test_unauthorised_roles_cannot_get_user_details(
    test_database,
    test_users,
    role,
):
    with pytest.raises(PermissionError):
        get_user_details(
            actor_role=role,
            user_id=test_users["user"],
        )


def test_get_user_details_returns_none_for_unknown_user(
    test_database,
    test_users,
):
    details = get_user_details(
        actor_role="admin",
        user_id="nonexistent-user-id",
    )

    assert details is None


def test_get_user_details_rejects_empty_user_id(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        get_user_details(
            actor_role="admin",
            user_id=" ",
        )


def test_super_admin_can_change_user_role(test_database, test_users):
    change_user_role(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=test_users["user"],
        new_role="developer",
    )

    details = get_user_details(
        actor_role="super_admin",
        user_id=test_users["user"],
    )

    assert details["role"] == "developer"


def test_non_super_admin_cannot_change_user_role(
    test_database,
    test_users,
):
    with pytest.raises(PermissionError):
        change_user_role(
            actor_role="admin",
            actor_user_id=test_users["admin"],
            target_user_id=test_users["user"],
            new_role="developer",
        )


def test_super_admin_cannot_demote_themselves(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        change_user_role(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id=test_users["super_admin"],
            new_role="admin",
        )


def test_super_admin_cannot_demote_last_active_super_admin(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        change_user_role(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id=test_users["super_admin"],
            new_role="admin",
        )


def test_super_admin_can_demote_another_super_admin_when_another_remains(
    test_database,
    test_users,
):
    second_super_admin_id = test_users["admin"]

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            ("super_admin", second_super_admin_id),
        )

    change_user_role(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=second_super_admin_id,
        new_role="admin",
    )

    details = get_user_details(
        actor_role="super_admin",
        user_id=second_super_admin_id,
    )

    assert details["role"] == "admin"


def test_change_user_role_rejects_unknown_target(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        change_user_role(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id="nonexistent-user-id",
            new_role="admin",
        )


def test_change_user_role_rejects_invalid_new_role(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        change_user_role(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id=test_users["user"],
            new_role="invalid_role",
        )


def test_super_admin_can_deactivate_user(test_database, test_users):
    target_id = test_users["user"]

    set_user_active_status(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=target_id,
        is_active=False,
    )

    details = get_user_details(
        actor_role="super_admin",
        user_id=target_id,
    )

    assert bool(details["is_active"]) is False


def test_super_admin_can_reactivate_user(test_database, test_users):
    target_id = test_users["user"]

    set_user_active_status(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=target_id,
        is_active=False,
    )

    set_user_active_status(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=target_id,
        is_active=True,
    )

    details = get_user_details(
        actor_role="super_admin",
        user_id=target_id,
    )

    assert bool(details["is_active"]) is True


def test_non_super_admin_cannot_change_account_status(
    test_database,
    test_users,
):
    with pytest.raises(PermissionError):
        set_user_active_status(
            actor_role="admin",
            actor_user_id=test_users["admin"],
            target_user_id=test_users["user"],
            is_active=False,
        )


def test_last_active_super_admin_cannot_be_deactivated(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        set_user_active_status(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id=test_users["super_admin"],
            is_active=False,
        )


def test_super_admin_can_deactivate_another_super_admin_when_one_remains(
    test_database,
    test_users,
):
    second_super_admin_id = test_users["admin"]

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET role = ? WHERE id = ?",
            ("super_admin", second_super_admin_id),
        )

    set_user_active_status(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=second_super_admin_id,
        is_active=False,
    )

    details = get_user_details(
        actor_role="super_admin",
        user_id=second_super_admin_id,
    )

    assert bool(details["is_active"]) is False


def test_set_user_active_status_rejects_non_boolean_value(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        set_user_active_status(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id=test_users["user"],
            is_active=1,
        )


def test_set_user_active_status_rejects_unknown_target(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        set_user_active_status(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id="nonexistent-user-id",
            is_active=False,
        )


def test_role_change_revokes_sessions_and_records_audit_event(
    test_database,
    test_users,
):
    target_id = test_users["user"]
    with database_connection() as connection:
        before = connection.execute(
            "SELECT session_version FROM users WHERE id = ?",
            (target_id,),
        ).fetchone()["session_version"]

    change_user_role(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=target_id,
        new_role="developer",
    )

    with database_connection() as connection:
        after = connection.execute(
            "SELECT session_version FROM users WHERE id = ?",
            (target_id,),
        ).fetchone()["session_version"]
        event = connection.execute(
            """
            SELECT user_id, action, resource_type, resource_id, details
            FROM audit_logs
            WHERE action = 'user_role_changed'
              AND resource_id = ?
            """,
            (target_id,),
        ).fetchone()

    assert after == before + 1
    assert event is not None
    assert event["user_id"] == test_users["super_admin"]
    assert event["resource_type"] == "user"


def test_status_change_revokes_sessions_and_records_audit_event(
    test_database,
    test_users,
):
    target_id = test_users["user"]
    with database_connection() as connection:
        before = connection.execute(
            "SELECT session_version FROM users WHERE id = ?",
            (target_id,),
        ).fetchone()["session_version"]

    set_user_active_status(
        actor_role="super_admin",
        actor_user_id=test_users["super_admin"],
        target_user_id=target_id,
        is_active=False,
    )

    with database_connection() as connection:
        after = connection.execute(
            "SELECT session_version FROM users WHERE id = ?",
            (target_id,),
        ).fetchone()["session_version"]
        event = connection.execute(
            """
            SELECT user_id, action, resource_type, resource_id
            FROM audit_logs
            WHERE action = 'user_deactivated'
              AND resource_id = ?
            """,
            (target_id,),
        ).fetchone()

    assert after == before + 1
    assert event is not None
    assert event["user_id"] == test_users["super_admin"]
    assert event["resource_type"] == "user"


def test_super_admin_cannot_deactivate_their_own_account(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        set_user_active_status(
            actor_role="super_admin",
            actor_user_id=test_users["super_admin"],
            target_user_id=test_users["super_admin"],
            is_active=False,
        )
