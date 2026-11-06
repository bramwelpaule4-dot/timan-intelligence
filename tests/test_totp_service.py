
"""Tests for TimanStat TOTP enrolment and verification services."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.security.totp import (
    TOTPError,
    generate_totp_code,
)
from timan_intelligence.security.totp_encryption import (
    generate_totp_encryption_key,
)
from timan_intelligence.security.totp_service import (
    TOTPServiceError,
    begin_totp_enrolment,
    confirm_totp_enrolment,
    verify_totp_for_user,
)


TEST_TIMESTAMP = 1_700_000_000


@pytest.fixture
def totp_user(tmp_path, monkeypatch):
    """Create an isolated database and registered test user."""

    database_file = tmp_path / "test_timanstat_totp.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    encryption_key = generate_totp_encryption_key()

    monkeypatch.setenv(
        "TIMANSTAT_TOTP_ENCRYPTION_KEY",
        encryption_key,
    )

    initialise_database()

    user_id = register_user(
        username="totp_test_user",
        email="totp_test@example.com",
        full_name="TOTP Test User",
        password="SecureTestPassword123!",
    )

    return {
        "user_id": user_id,
        "username": "totp_test_user",
        "email": "totp_test@example.com",
        "encryption_key": encryption_key,
        "database_file": database_file,
    }


def _get_user_totp_state(user_id):
    """Read persisted TOTP fields for a user."""

    with database_connection() as connection:
        cursor = connection.cursor()

        cursor.execute(
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
            (user_id,),
        )

        return cursor.fetchone()


def test_begin_totp_enrolment_creates_pending_secret(totp_user):
    """Beginning enrolment stores an encrypted pending secret."""

    result = begin_totp_enrolment(totp_user["user_id"])

    assert result is not None
    assert result["secret"]
    assert result["provisioning_uri"].startswith("otpauth://totp/")

    state = _get_user_totp_state(totp_user["user_id"])

    assert state is not None
    assert state[0] in (False, 0)
    assert state[1] is None
    assert state[2] is not None
    assert state[2] != result["secret"]
    assert state[5] is not None


def test_begin_totp_enrolment_rejects_unknown_user(totp_user):
    """An unknown account cannot begin enrolment."""

    with pytest.raises(
        TOTPServiceError,
        match="active user account was not found",
    ):
        begin_totp_enrolment("nonexistent-user")


def test_begin_totp_enrolment_rejects_inactive_user(totp_user):
    """An inactive account cannot begin enrolment."""

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (False, totp_user["user_id"]),
        )

    with pytest.raises(
        TOTPServiceError,
        match="active user account was not found",
    ):
        begin_totp_enrolment(totp_user["user_id"])


def test_begin_totp_enrolment_does_not_enable_totp(totp_user):
    """Starting enrolment must not activate TOTP before confirmation."""

    begin_totp_enrolment(totp_user["user_id"])

    state = _get_user_totp_state(totp_user["user_id"])

    assert state[0] in (False, 0)
    assert state[1] is None
    assert state[2] is not None


def test_begin_totp_enrolment_rejects_already_enabled_user(totp_user):
    """An account with active TOTP cannot start another enrolment."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=code,
        at_time=TEST_TIMESTAMP,
    ) is True

    with pytest.raises(
        TOTPServiceError,
        match="already enabled",
    ):
        begin_totp_enrolment(totp_user["user_id"])


def test_begin_totp_enrolment_does_not_save_secret_when_uri_generation_fails(
    totp_user,
    monkeypatch,
):
    """A provisioning URI failure must not persist a pending secret."""

    def fail_provisioning_uri(**kwargs):
        raise TOTPError("Invalid provisioning configuration.")

    monkeypatch.setattr(
        "timan_intelligence.security.totp_service.build_totp_provisioning_uri",
        fail_provisioning_uri,
    )

    with pytest.raises(
        TOTPServiceError,
        match="Unable to create the authenticator provisioning URI",
    ):
        begin_totp_enrolment(totp_user["user_id"])

    state = _get_user_totp_state(totp_user["user_id"])

    assert state is not None
    assert state[0] in (False, 0)
    assert state[1] is None
    assert state[2] is None
    assert state[5] is None


def test_confirm_totp_enrolment_rejects_expired_pending_enrolment(totp_user):
    """An enrolment older than 15 minutes is rejected and cleared."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET totp_pending_created_at = datetime('now', '-16 minutes')
            WHERE id = ?
            """,
            (totp_user["user_id"],),
        )

    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    confirmed = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is False

    state = _get_user_totp_state(totp_user["user_id"])

    assert state[0] in (False, 0)
    assert state[1] is None
    assert state[2] is None
    assert state[5] is None


def test_confirm_totp_enrolment_accepts_pending_enrolment_within_ttl(
    totp_user,
):
    """An enrolment still within the 15-minute window can be confirmed."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET totp_pending_created_at = datetime('now', '-14 minutes')
            WHERE id = ?
            """,
            (totp_user["user_id"],),
        )

    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    confirmed = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is True

    state = _get_user_totp_state(totp_user["user_id"])

    assert state[0] in (True, 1)
    assert state[1] is not None
    assert state[2] is None
    assert state[3] is not None
    assert state[4] is not None
    assert state[5] is None


def test_confirm_totp_enrolment_rejects_missing_pending_timestamp(totp_user):
    """A pending secret without a creation timestamp cannot be confirmed."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET totp_pending_created_at = NULL
            WHERE id = ?
            """,
            (totp_user["user_id"],),
        )

    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    confirmed = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is False

    state = _get_user_totp_state(totp_user["user_id"])

    assert state[0] in (False, 0)
    assert state[1] is None
    assert state[2] is None
    assert state[5] is None


def test_confirm_totp_enrolment_rejects_unknown_user(totp_user):
    """A nonexistent account cannot complete enrolment."""

    confirmed = confirm_totp_enrolment(
        user_id="nonexistent-user",
        code="123456",
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is False


def test_confirm_totp_enrolment_rejects_invalid_code(totp_user):
    """An invalid authenticator code cannot complete enrolment."""

    begin_totp_enrolment(totp_user["user_id"])

    confirmed = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code="000000",
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is False

    state = _get_user_totp_state(totp_user["user_id"])

    assert state[0] in (False, 0)
    assert state[1] is None
    assert state[2] is not None


def test_confirm_totp_enrolment_enables_totp(totp_user):
    """A valid authenticator code activates TOTP."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    confirmed = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is True

    state = _get_user_totp_state(totp_user["user_id"])

    assert state[0] in (True, 1)
    assert state[1] is not None
    assert state[2] is None
    assert state[3] is not None
    assert state[4] is not None
    assert state[5] is None


def test_confirm_totp_enrolment_cannot_be_repeated(totp_user):
    """A completed enrolment cannot be confirmed again."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    first_confirmation = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    second_confirmation = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert first_confirmation is True
    assert second_confirmation is False


def test_verify_totp_for_user_rejects_unknown_user(totp_user):
    """A nonexistent account cannot pass TOTP verification."""

    verified = verify_totp_for_user(
        user_id="nonexistent-user",
        code="123456",
        at_time=TEST_TIMESTAMP,
    )

    assert verified is False


def test_verify_totp_for_user_rejects_user_without_enrolment(totp_user):
    """An account without active TOTP cannot pass verification."""

    verified = verify_totp_for_user(
        user_id=totp_user["user_id"],
        code="123456",
        at_time=TEST_TIMESTAMP,
    )

    assert verified is False


def test_verify_totp_for_user_accepts_valid_code(totp_user):
    """A valid code from an enrolled authenticator is accepted."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    enrolment_code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    confirmed = confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=enrolment_code,
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is True

    verification_timestamp = TEST_TIMESTAMP + 30

    verification_code = generate_totp_code(
        enrolment["secret"],
        at_time=verification_timestamp,
    )

    verified = verify_totp_for_user(
        user_id=totp_user["user_id"],
        code=verification_code,
        at_time=verification_timestamp,
    )

    assert verified is True


def test_verify_totp_for_user_rejects_invalid_code(totp_user):
    """An invalid code is rejected for an enrolled account."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    valid_code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=valid_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    verified = verify_totp_for_user(
        user_id=totp_user["user_id"],
        code="000000",
        at_time=TEST_TIMESTAMP + 30,
    )

    assert verified is False


def test_verify_totp_for_user_rejects_replayed_code(totp_user):
    """A successfully accepted TOTP code cannot be reused."""

    enrolment = begin_totp_enrolment(totp_user["user_id"])

    enrolment_code = generate_totp_code(
        enrolment["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        user_id=totp_user["user_id"],
        code=enrolment_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    verification_timestamp = TEST_TIMESTAMP + 30

    code = generate_totp_code(
        enrolment["secret"],
        at_time=verification_timestamp,
    )

    first_attempt = verify_totp_for_user(
        user_id=totp_user["user_id"],
        code=code,
        at_time=verification_timestamp,
    )

    second_attempt = verify_totp_for_user(
        user_id=totp_user["user_id"],
        code=code,
        at_time=verification_timestamp,
    )

    assert first_attempt is True
    assert second_attempt is False


@pytest.mark.parametrize(
    "invalid_user_id",
    [
        None,
        "",
        " ",
        0,
        -1,
    ],
)
def test_totp_services_reject_invalid_user_ids(
    totp_user,
    invalid_user_id,
):
    """All TOTP service operations reject malformed user identifiers."""

    with pytest.raises(TOTPServiceError):
        begin_totp_enrolment(invalid_user_id)

    with pytest.raises(TOTPServiceError):
        confirm_totp_enrolment(
            user_id=invalid_user_id,
            code="123456",
            at_time=TEST_TIMESTAMP,
        )

    with pytest.raises(TOTPServiceError):
        verify_totp_for_user(
            user_id=invalid_user_id,
            code="123456",
            at_time=TEST_TIMESTAMP,
        )
