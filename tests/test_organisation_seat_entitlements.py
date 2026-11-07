"""Organisation team-seat entitlement enforcement tests."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.entitlements.subscriptions import assign_subscription
from timan_intelligence.identity.service import register_user
from timan_intelligence.organisations.service import (
    add_organisation_member,
    create_organisation,
)


@pytest.fixture
def seat_setup(tmp_path, monkeypatch):
    database_file = tmp_path / "seat_entitlements.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database_file.as_posix()}")
    initialise_database()
    users = []
    for username in ("seatadmin", "seatmember", "seatmember2"):
        users.append(register_user(
            username=username,
            email=f"{username}@example.com",
            full_name=username.title(),
            password="SecureTestPassword123!",
        ))
    organisation_id = create_organisation(
        name="Seat Test Organisation", created_by=users[0]
    )
    return users, organisation_id


def test_free_plan_cannot_add_second_active_team_member(seat_setup):
    users, organisation_id = seat_setup
    with pytest.raises(ValueError, match="Free plan allows 1 active team member"):
        add_organisation_member(
            organisation_id=organisation_id,
            user_id=users[1],
            added_by=users[0],
        )


def test_professional_plan_still_has_one_team_seat(seat_setup):
    users, organisation_id = seat_setup
    assign_subscription(organisation_id=organisation_id, plan_code="professional")
    with pytest.raises(ValueError, match="Professional plan allows 1 active team member"):
        add_organisation_member(
            organisation_id=organisation_id,
            user_id=users[1],
            added_by=users[0],
        )


def test_enterprise_plan_allows_additional_team_members(seat_setup):
    users, organisation_id = seat_setup
    assign_subscription(organisation_id=organisation_id, plan_code="enterprise")
    membership_id = add_organisation_member(
        organisation_id=organisation_id,
        user_id=users[1],
        added_by=users[0],
    )
    assert membership_id
