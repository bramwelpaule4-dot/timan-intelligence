"""Tests for TOTP account-security management operations."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.security.totp import generate_totp_code
from timan_intelligence.security.totp_encryption import generate_totp_encryption_key
from timan_intelligence.security.totp_service import (
    begin_totp_enrolment,
    confirm_totp_enrolment,
    disable_totp_for_user,
    get_totp_status,
)


TEST_TIMESTAMP = 1_700_000_000
PASSWORD = "SecureTestPassword123!"


@pytest.fixture
def enrolled_user(tmp_path, monkeypatch):
    """Create an isolated account with a confirmed authenticator."""

    database_file = tmp_path / "test_totp_management.db"
    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )
    monkeypatch.setenv(
        "TIMANSTAT_TOTP_ENCRYPTION_KEY",
        generate_totp_encryption_key(),
    )
    monkeypatch.setenv(
        "TIMANSTAT_RATE_LIMIT_HMAC_KEY",
        "test-rate-limit-hmac-key-with-at-least-32-bytes",
    )
    initialise_database()

    user_id = register_user(
        username="security_user",
        email="security_user@example.com",
        full_name="Security User",
        password=PASSWORD,
    )

    return user_id


def _session_version(user_id):
    with database_connection() as connection:
        row = connection.execute(
            "SELECT session_version FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return row["session_version"]


def test_totp_status_reports_disabled_before_enrolment(enrolled_user):
    assert get_totp_status(enrolled_user) is False


def test_totp_status_reports_enabled_after_confirmation(enrolled_user):
    enrolment = begin_totp_enrolment(enrolled_user)
    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        enrolled_user,
        code,
        at_time=TEST_TIMESTAMP,
    ) is True
    assert get_totp_status(enrolled_user) is True


def test_confirming_totp_revokes_existing_sessions(enrolled_user):
    before = _session_version(enrolled_user)
    enrolment = begin_totp_enrolment(enrolled_user)
    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        enrolled_user,
        code,
        at_time=TEST_TIMESTAMP,
    ) is True
    assert _session_version(enrolled_user) == before + 1


def test_disabling_totp_requires_current_password_and_fresh_code(enrolled_user):
    enrolment = begin_totp_enrolment(enrolled_user)
    setup_code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )
    assert confirm_totp_enrolment(
        enrolled_user,
        setup_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    before = _session_version(enrolled_user)
    disable_time = TEST_TIMESTAMP + 30
    disable_code = generate_totp_code(
        enrolment["secret"],
        at_time=disable_time,
    )

    assert disable_totp_for_user(
        enrolled_user,
        "WrongPassword123!",
        disable_code,
        at_time=disable_time,
    ) is False
    assert get_totp_status(enrolled_user) is True
    assert _session_version(enrolled_user) == before

    assert disable_totp_for_user(
        enrolled_user,
        PASSWORD,
        disable_code,
        at_time=disable_time,
    ) is True
    assert get_totp_status(enrolled_user) is False
    assert _session_version(enrolled_user) == before + 1


def test_disabling_totp_rejects_invalid_code(enrolled_user):
    enrolment = begin_totp_enrolment(enrolled_user)
    setup_code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )
    assert confirm_totp_enrolment(
        enrolled_user,
        setup_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    before = _session_version(enrolled_user)
    assert disable_totp_for_user(
        enrolled_user,
        PASSWORD,
        "000000",
        at_time=TEST_TIMESTAMP + 30,
    ) is False
    assert get_totp_status(enrolled_user) is True
    assert _session_version(enrolled_user) == before


def test_disabling_totp_clears_encrypted_and_pending_secrets(enrolled_user):
    enrolment = begin_totp_enrolment(enrolled_user)
    setup_code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )
    assert confirm_totp_enrolment(
        enrolled_user,
        setup_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    disable_time = TEST_TIMESTAMP + 30
    disable_code = generate_totp_code(
        enrolment["secret"],
        at_time=disable_time,
    )
    assert disable_totp_for_user(
        enrolled_user,
        PASSWORD,
        disable_code,
        at_time=disable_time,
    ) is True

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT
                totp_enabled,
                totp_secret_encrypted,
                totp_pending_secret_encrypted,
                totp_last_accepted_counter,
                totp_enrolled_at,
                totp_pending_created_at
            FROM users
            WHERE id = ?
            """,
            (enrolled_user,),
        ).fetchone()

    assert row["totp_enabled"] in (False, 0)
    assert row["totp_secret_encrypted"] is None
    assert row["totp_pending_secret_encrypted"] is None
    assert row["totp_last_accepted_counter"] is None
    assert row["totp_enrolled_at"] is None
    assert row["totp_pending_created_at"] is None


def test_totp_management_rejects_unknown_user():
    with pytest.raises(Exception):
        get_totp_status("unknown-user")
