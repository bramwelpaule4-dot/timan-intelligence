
"""Tests for TimanStat platform audit logging."""

import json

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.organisations.service import create_organisation
from timan_intelligence.administration.audit import (
    record_audit_event,
    list_audit_events,
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
def test_user(test_database):
    """Create a real user for audit foreign-key relationships."""

    return register_user(
        username="audituser",
        email="audituser@example.com",
        full_name="Audit Test User",
        password="SecureTestPassword123!",
    )


@pytest.fixture
def test_organisation(test_database, test_user):
    """Create a real organisation for audit foreign-key relationships."""

    return create_organisation(
        name="Audit Test Organisation",
        created_by=test_user,
    )


def test_record_audit_event_creates_record(test_database, test_user):
    audit_id = record_audit_event(
        action="user_registered",
        user_id=test_user,
        resource_type="user",
        resource_id=test_user,
    )

    assert isinstance(audit_id, str)

    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row is not None
    assert row["action"] == "user_registered"
    assert row["user_id"] == test_user
    assert row["resource_type"] == "user"
    assert row["resource_id"] == test_user


def test_record_audit_event_returns_unique_ids(test_database):
    first_id = record_audit_event(action="first_event")
    second_id = record_audit_event(action="second_event")

    assert first_id != second_id


def test_record_audit_event_supports_optional_fields(
    test_database,
    test_user,
    test_organisation,
):
    audit_id = record_audit_event(
        action="organisation_created",
        user_id=test_user,
        organisation_id=test_organisation,
        resource_type="organisation",
        resource_id=test_organisation,
        details={"name": "Audit Test Organisation"},
        ip_address="192.168.1.10",
    )

    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row is not None
    assert row["organisation_id"] == test_organisation
    assert row["ip_address"] == "192.168.1.10"
    assert json.loads(row["details"]) == {
        "name": "Audit Test Organisation"
    }


def test_record_audit_event_trims_text_fields(test_database, test_user):
    audit_id = record_audit_event(
        action="  user_updated  ",
        user_id=f"  {test_user}  ",
        resource_type="  user  ",
        resource_id=f"  {test_user}  ",
    )

    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row["action"] == "user_updated"
    assert row["user_id"] == test_user
    assert row["resource_type"] == "user"
    assert row["resource_id"] == test_user


def test_audit_details_exclude_sensitive_fields(test_database):
    audit_id = record_audit_event(
        action="security_event",
        details={
            "username": "testuser",
            "password": "secret-password",
            "password_hash": "sensitive-hash",
            "token": "secret-token",
            "access_token": "access-value",
            "refresh_token": "refresh-value",
            "secret": "private-value",
            "api_key": "private-api-key",
        },
    )

    with database_connection() as connection:
        row = connection.execute(
            "SELECT details FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    stored_details = json.loads(row["details"])

    assert stored_details == {"username": "testuser"}

    for sensitive_key in (
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
    ):
        assert sensitive_key not in stored_details


def test_record_audit_event_accepts_no_details(test_database):
    audit_id = record_audit_event(action="user_logged_out")

    with database_connection() as connection:
        row = connection.execute(
            "SELECT details FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row["details"] is None


def test_record_audit_event_rejects_empty_action(test_database):
    with pytest.raises(ValueError):
        record_audit_event(action="")


def test_record_audit_event_rejects_whitespace_action(test_database):
    with pytest.raises(ValueError):
        record_audit_event(action="   ")


def test_record_audit_event_rejects_non_text_user_id(test_database):
    with pytest.raises(ValueError):
        record_audit_event(
            action="user_updated",
            user_id=123,
        )


def test_record_audit_event_rejects_non_text_organisation_id(test_database):
    with pytest.raises(ValueError):
        record_audit_event(
            action="organisation_updated",
            organisation_id=123,
        )


def test_record_audit_event_rejects_long_ip_address(test_database):
    with pytest.raises(ValueError):
        record_audit_event(
            action="user_logged_in",
            ip_address="1" * 46,
        )


def test_list_audit_events_returns_records(test_database):
    first_id = record_audit_event(action="first_event")
    second_id = record_audit_event(action="second_event")

    events = list_audit_events(
        requested_by_role="super_admin",
    )

    returned_ids = {event["id"] for event in events}

    assert first_id in returned_ids
    assert second_id in returned_ids


def test_admin_can_list_audit_events(test_database):
    record_audit_event(action="test_event")

    events = list_audit_events(
        requested_by_role="admin",
    )

    assert len(events) >= 1


@pytest.mark.parametrize(
    "role",
    ["developer", "user", "unknown"],
)
def test_unauthorised_roles_cannot_list_audit_events(
    test_database,
    role,
):
    with pytest.raises(PermissionError):
        list_audit_events(requested_by_role=role)


def test_list_audit_events_respects_limit(test_database):
    for number in range(5):
        record_audit_event(action=f"event_{number}")

    events = list_audit_events(
        requested_by_role="admin",
        limit=2,
    )

    assert len(events) == 2


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, 1001, 1.5, True, "10"],
)
def test_list_audit_events_rejects_invalid_limit(
    test_database,
    invalid_limit,
):
    with pytest.raises(ValueError):
        list_audit_events(
            requested_by_role="admin",
            limit=invalid_limit,
        )
