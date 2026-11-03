
"""Tests for TimanStat platform audit logging."""

import json

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
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


def test_record_audit_event_creates_record(test_database):
    """A valid audit event should be stored in the database."""

    audit_id = record_audit_event(
        action="user_registered",
        user_id="user-001",
        resource_type="user",
        resource_id="user-001",
    )

    assert audit_id is not None
    assert isinstance(audit_id, str)

    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row is not None
    assert row["action"] == "user_registered"
    assert row["user_id"] == "user-001"
    assert row["resource_type"] == "user"
    assert row["resource_id"] == "user-001"


def test_record_audit_event_returns_unique_ids(test_database):
    """Each audit event should have a unique identifier."""

    first_id = record_audit_event(action="first_event")
    second_id = record_audit_event(action="second_event")

    assert first_id != second_id


def test_record_audit_event_supports_optional_fields(test_database):
    """Optional audit fields should be stored when supplied."""

    audit_id = record_audit_event(
        action="organisation_created",
        user_id="user-001",
        organisation_id="org-001",
        resource_type="organisation",
        resource_id="org-001",
        details={"name": "Example Organisation"},
        ip_address="192.168.1.10",
    )

    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row is not None
    assert row["organisation_id"] == "org-001"
    assert row["ip_address"] == "192.168.1.10"
    assert json.loads(row["details"]) == {
        "name": "Example Organisation"
    }


def test_record_audit_event_trims_text_fields(test_database):
    """Text fields should be stripped of surrounding whitespace."""

    audit_id = record_audit_event(
        action="  user_updated  ",
        user_id="  user-001  ",
        organisation_id="  org-001  ",
        resource_type="  user  ",
        resource_id="  user-001  ",
    )

    with database_connection() as connection:
        row = connection.execute(
            "SELECT * FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row["action"] == "user_updated"
    assert row["user_id"] == "user-001"
    assert row["organisation_id"] == "org-001"
    assert row["resource_type"] == "user"
    assert row["resource_id"] == "user-001"


def test_audit_details_exclude_sensitive_fields(test_database):
    """Sensitive top-level values should not be stored in audit details."""

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
    """Details may be omitted."""

    audit_id = record_audit_event(
        action="user_logged_out",
    )

    with database_connection() as connection:
        row = connection.execute(
            "SELECT details FROM audit_logs WHERE id = ?",
            (audit_id,),
        ).fetchone()

    assert row["details"] is None


def test_record_audit_event_rejects_empty_action(test_database):
    """An empty action must be rejected."""

    with pytest.raises(ValueError):
        record_audit_event(action="")


def test_record_audit_event_rejects_whitespace_action(test_database):
    """An action containing only whitespace must be rejected."""

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
    """IP address values longer than 45 characters must be rejected."""

    with pytest.raises(ValueError):
        record_audit_event(
            action="user_logged_in",
            ip_address="1" * 46,
        )


def test_list_audit_events_returns_records(test_database):
    """Platform administrators should be able to retrieve audit records."""

    first_id = record_audit_event(
        action="first_event",
        user_id="user-001",
    )

    second_id = record_audit_event(
        action="second_event",
        user_id="user-002",
    )

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
def test_unauthorised_roles_cannot_list_audit_events(test_database, role):
    """Only platform administrators should access audit records."""

    with pytest.raises(PermissionError):
        list_audit_events(
            requested_by_role=role,
        )


def test_list_audit_events_respects_limit(test_database):
    """The requested limit should restrict the number of returned records."""

    for number in range(5):
        record_audit_event(
            action=f"event_{number}",
        )

    events = list_audit_events(
        requested_by_role="admin",
        limit=2,
    )

    assert len(events) == 2


@pytest.mark.parametrize(
    "invalid_limit",
    [0, -1, 1001, 1.5, True, "10"],
)
def test_list_audit_events_rejects_invalid_limit(test_database, invalid_limit):
    """Invalid audit retrieval limits should be rejected."""

    with pytest.raises(ValueError):
        list_audit_events(
            requested_by_role="admin",
            limit=invalid_limit,
        )

