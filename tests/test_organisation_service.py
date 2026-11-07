"""Tests for TimanStat organisation and membership services."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.entitlements.subscriptions import assign_subscription
from timan_intelligence.organisations.service import (
    create_organisation,
    add_organisation_member,
    list_user_organisations,
    list_organisation_members,
    change_membership_role,
    change_membership_status,
    remove_organisation_member,
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
    """Create individual user accounts for organisation tests."""

    admin_id = register_user(
        username="orgadmin",
        email="orgadmin@example.com",
        full_name="Organisation Administrator",
        password="SecureTestPassword123!",
    )

    member_id = register_user(
        username="orgmember",
        email="orgmember@example.com",
        full_name="Organisation Member",
        password="SecureTestPassword123!",
    )

    second_member_id = register_user(
        username="secondmember",
        email="secondmember@example.com",
        full_name="Second Member",
        password="SecureTestPassword123!",
    )

    inactive_id = register_user(
        username="inactiveuser",
        email="inactive@example.com",
        full_name="Inactive User",
        password="SecureTestPassword123!",
    )

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (False, inactive_id),
        )

    return {
        "admin": admin_id,
        "member": member_id,
        "second_member": second_member_id,
        "inactive": inactive_id,
    }


@pytest.fixture
def test_organisation(test_users):
    """Create an organisation with its creator as the first admin."""

    organisation_id = create_organisation(
        name="TimanStat Test Organisation",
        created_by=test_users["admin"],
        organisation_type="NGO",
        registration_number="TEST-001",
        contact_email="contact@example.com",
        country="Kenya",
    )

    assign_subscription(organisation_id=organisation_id, plan_code="enterprise")
    return organisation_id


def test_create_organisation(test_database, test_users):
    organisation_id = create_organisation(
        name="Test Organisation",
        created_by=test_users["admin"],
    )

    assert isinstance(organisation_id, str)
    assert organisation_id

    with database_connection() as connection:
        organisation = connection.execute(
            "SELECT * FROM organisations WHERE id = ?",
            (organisation_id,),
        ).fetchone()

    assert organisation is not None
    assert organisation["name"] == "Test Organisation"
    assert organisation["status"] == "active"
    assert organisation["created_by"] == test_users["admin"]


def test_create_organisation_creates_admin_membership(
    test_database,
    test_users,
):
    organisation_id = create_organisation(
        name="Membership Test Organisation",
        created_by=test_users["admin"],
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT *
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (organisation_id, test_users["admin"]),
        ).fetchone()

    assert membership is not None
    assert membership["role"] == "org_admin"
    assert membership["status"] == "active"


def test_create_organisation_normalises_name(
    test_database,
    test_users,
):
    organisation_id = create_organisation(
        name="  TimanStat Organisation  ",
        created_by=test_users["admin"],
    )

    with database_connection() as connection:
        organisation = connection.execute(
            "SELECT name FROM organisations WHERE id = ?",
            (organisation_id,),
        ).fetchone()

    assert organisation["name"] == "TimanStat Organisation"


@pytest.mark.parametrize(
    "invalid_name",
    ["", "   ", None, 123],
)
def test_create_organisation_rejects_invalid_name(
    test_database,
    test_users,
    invalid_name,
):
    with pytest.raises(ValueError):
        create_organisation(
            name=invalid_name,
            created_by=test_users["admin"],
        )


def test_create_organisation_rejects_empty_creator(
    test_database,
):
    with pytest.raises(ValueError):
        create_organisation(
            name="Test Organisation",
            created_by=" ",
        )


def test_create_organisation_rejects_inactive_creator(
    test_database,
    test_users,
):
    with pytest.raises(ValueError):
        create_organisation(
            name="Test Organisation",
            created_by=test_users["inactive"],
        )


def test_create_organisation_normalises_contact_email(
    test_database,
    test_users,
):
    organisation_id = create_organisation(
        name="Email Test Organisation",
        created_by=test_users["admin"],
        contact_email="  CONTACT@EXAMPLE.COM ",
    )

    with database_connection() as connection:
        organisation = connection.execute(
            "SELECT contact_email FROM organisations WHERE id = ?",
            (organisation_id,),
        ).fetchone()

    assert organisation["contact_email"] == "contact@example.com"


@pytest.mark.parametrize(
    "invalid_email",
    [
        "invalid-email",
        "missing-domain@",
        "@missing-name.com",
        "two@@example.com",
    ],
)
def test_create_organisation_rejects_invalid_contact_email(
    test_database,
    test_users,
    invalid_email,
):
    with pytest.raises(ValueError):
        create_organisation(
            name="Invalid Email Organisation",
            created_by=test_users["admin"],
            contact_email=invalid_email,
        )


def test_create_organisation_accepts_empty_optional_email(
    test_database,
    test_users,
):
    organisation_id = create_organisation(
        name="No Contact Email Organisation",
        created_by=test_users["admin"],
        contact_email=" ",
    )

    with database_connection() as connection:
        organisation = connection.execute(
            "SELECT contact_email FROM organisations WHERE id = ?",
            (organisation_id,),
        ).fetchone()

    assert organisation["contact_email"] is None


def test_add_organisation_member(
    test_database,
    test_users,
    test_organisation,
):
    membership_id = add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    assert isinstance(membership_id, str)
    assert membership_id

    with database_connection() as connection:
        membership = connection.execute(
            "SELECT * FROM organisation_memberships WHERE id = ?",
            (membership_id,),
        ).fetchone()

    assert membership is not None
    assert membership["organisation_id"] == test_organisation
    assert membership["user_id"] == test_users["member"]
    assert membership["role"] == "org_member"
    assert membership["status"] == "active"


def test_add_organisation_member_as_admin(
    test_database,
    test_users,
    test_organisation,
):
    membership_id = add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
        role="org_admin",
    )

    with database_connection() as connection:
        membership = connection.execute(
            "SELECT role FROM organisation_memberships WHERE id = ?",
            (membership_id,),
        ).fetchone()

    assert membership["role"] == "org_admin"


def test_add_organisation_member_normalises_role(
    test_database,
    test_users,
    test_organisation,
):
    membership_id = add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
        role="  ORG_MEMBER ",
    )

    with database_connection() as connection:
        membership = connection.execute(
            "SELECT role FROM organisation_memberships WHERE id = ?",
            (membership_id,),
        ).fetchone()

    assert membership["role"] == "org_member"


def test_non_admin_cannot_add_organisation_member(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(PermissionError):
        add_organisation_member(
            organisation_id=test_organisation,
            user_id=test_users["second_member"],
            added_by=test_users["member"],
        )


def test_add_member_rejects_invalid_role(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        add_organisation_member(
            organisation_id=test_organisation,
            user_id=test_users["member"],
            added_by=test_users["admin"],
            role="super_admin",
        )


def test_add_member_rejects_inactive_user(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        add_organisation_member(
            organisation_id=test_organisation,
            user_id=test_users["inactive"],
            added_by=test_users["admin"],
        )


def test_add_member_rejects_duplicate_membership(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    with pytest.raises(ValueError):
        add_organisation_member(
            organisation_id=test_organisation,
            user_id=test_users["member"],
            added_by=test_users["admin"],
        )


def test_add_member_rejects_unknown_organisation(
    test_database,
    test_users,
):
    with pytest.raises(PermissionError):
        add_organisation_member(
            organisation_id="unknown-organisation",
            user_id=test_users["member"],
            added_by=test_users["admin"],
        )


def test_list_user_organisations(
    test_database,
    test_users,
    test_organisation,
):
    organisations = list_user_organisations(test_users["admin"])

    assert len(organisations) == 1
    assert organisations[0]["organisation_id"] == test_organisation
    assert organisations[0]["organisation_name"] == (
        "TimanStat Test Organisation"
    )
    assert organisations[0]["membership_role"] == "org_admin"
    assert organisations[0]["membership_status"] == "active"


def test_list_user_organisations_excludes_inactive_memberships(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE organisation_memberships
            SET status = ?
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            ("suspended", test_organisation, test_users["member"]),
        )

    organisations = list_user_organisations(test_users["member"])

    assert organisations == []


def test_list_user_organisations_rejects_empty_user_id(
    test_database,
):
    with pytest.raises(ValueError):
        list_user_organisations(" ")


def test_list_organisation_members(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    members = list_organisation_members(
        organisation_id=test_organisation,
        requested_by=test_users["admin"],
    )

    assert len(members) == 2

    member_ids = {member["user_id"] for member in members}

    assert test_users["admin"] in member_ids
    assert test_users["member"] in member_ids


def test_list_organisation_members_includes_user_details(
    test_database,
    test_users,
    test_organisation,
):
    members = list_organisation_members(
        organisation_id=test_organisation,
        requested_by=test_users["admin"],
    )

    admin = next(
        member
        for member in members
        if member["user_id"] == test_users["admin"]
    )

    assert admin["username"] == "orgadmin"
    assert admin["email"] == "orgadmin@example.com"
    assert admin["full_name"] == "Organisation Administrator"
    assert admin["membership_role"] == "org_admin"


def test_non_admin_cannot_list_organisation_members(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(PermissionError):
        list_organisation_members(
            organisation_id=test_organisation,
            requested_by=test_users["member"],
        )


def test_list_members_rejects_unknown_organisation(
    test_database,
    test_users,
):
    with pytest.raises(PermissionError):
        list_organisation_members(
            organisation_id="unknown-organisation",
            requested_by=test_users["admin"],
        )


def test_change_membership_role(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    change_membership_role(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        changed_by=test_users["admin"],
        new_role="org_admin",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership["role"] == "org_admin"


def test_change_membership_role_normalises_role(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    change_membership_role(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        changed_by=test_users["admin"],
        new_role="  ORG_ADMIN ",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership["role"] == "org_admin"


def test_non_admin_cannot_change_membership_role(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    with pytest.raises(PermissionError):
        change_membership_role(
            organisation_id=test_organisation,
            user_id=test_users["member"],
            changed_by=test_users["member"],
            new_role="org_admin",
        )


def test_change_membership_role_rejects_invalid_role(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        change_membership_role(
            organisation_id=test_organisation,
            user_id=test_users["admin"],
            changed_by=test_users["admin"],
            new_role="super_admin",
        )


def test_change_membership_role_rejects_unknown_membership(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        change_membership_role(
            organisation_id=test_organisation,
            user_id="unknown-user",
            changed_by=test_users["admin"],
            new_role="org_member",
        )


def test_last_active_organisation_admin_cannot_be_demoted(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        change_membership_role(
            organisation_id=test_organisation,
            user_id=test_users["admin"],
            changed_by=test_users["admin"],
            new_role="org_member",
        )


def test_another_organisation_admin_can_be_demoted_when_one_remains(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
        role="org_admin",
    )

    change_membership_role(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        changed_by=test_users["admin"],
        new_role="org_member",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT role
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership["role"] == "org_member"


def test_change_membership_status(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    change_membership_status(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        changed_by=test_users["admin"],
        new_status="suspended",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT status
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership["status"] == "suspended"


@pytest.mark.parametrize(
    "status",
    ["active", "pending", "suspended"],
)
def test_change_membership_status_accepts_supported_statuses(
    test_database,
    test_users,
    test_organisation,
    status,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    change_membership_status(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        changed_by=test_users["admin"],
        new_status=status,
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT status
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership["status"] == status


def test_change_membership_status_rejects_invalid_status(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        change_membership_status(
            organisation_id=test_organisation,
            user_id=test_users["admin"],
            changed_by=test_users["admin"],
            new_status="deleted",
        )


def test_non_admin_cannot_change_membership_status(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    with pytest.raises(PermissionError):
        change_membership_status(
            organisation_id=test_organisation,
            user_id=test_users["member"],
            changed_by=test_users["member"],
            new_status="suspended",
        )


def test_last_active_organisation_admin_cannot_be_suspended(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        change_membership_status(
            organisation_id=test_organisation,
            user_id=test_users["admin"],
            changed_by=test_users["admin"],
            new_status="suspended",
        )


def test_another_organisation_admin_can_be_suspended_when_one_remains(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
        role="org_admin",
    )

    change_membership_status(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        changed_by=test_users["admin"],
        new_status="suspended",
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT status
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership["status"] == "suspended"


def test_remove_organisation_member(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
    )

    remove_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        removed_by=test_users["admin"],
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT id
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership is None

    # Removing an organisation membership must not delete the user account.
    with database_connection() as connection:
        user = connection.execute(
            "SELECT id FROM users WHERE id = ?",
            (test_users["member"],),
        ).fetchone()

    assert user is not None


def test_non_admin_cannot_remove_organisation_member(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["second_member"],
        added_by=test_users["admin"],
    )

    with pytest.raises(PermissionError):
        remove_organisation_member(
            organisation_id=test_organisation,
            user_id=test_users["second_member"],
            removed_by=test_users["member"],
        )


def test_last_active_organisation_admin_cannot_be_removed(
    test_database,
    test_users,
    test_organisation,
):
    with pytest.raises(ValueError):
        remove_organisation_member(
            organisation_id=test_organisation,
            user_id=test_users["admin"],
            removed_by=test_users["admin"],
        )


def test_another_organisation_admin_can_be_removed_when_one_remains(
    test_database,
    test_users,
    test_organisation,
):
    add_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        added_by=test_users["admin"],
        role="org_admin",
    )

    remove_organisation_member(
        organisation_id=test_organisation,
        user_id=test_users["member"],
        removed_by=test_users["admin"],
    )

    with database_connection() as connection:
        membership = connection.execute(
            """
            SELECT id
            FROM organisation_memberships
            WHERE organisation_id = ?
              AND user_id = ?
            """,
            (test_organisation, test_users["member"]),
        ).fetchone()

    assert membership is None


def test_member_cannot_manage_another_organisation(
    test_database,
    test_users,
    test_organisation,
):
    other_organisation_id = create_organisation(
        name="Another Organisation",
        created_by=test_users["second_member"],
    )

    with pytest.raises(PermissionError):
        add_organisation_member(
            organisation_id=other_organisation_id,
            user_id=test_users["member"],
            added_by=test_users["admin"],
        )
