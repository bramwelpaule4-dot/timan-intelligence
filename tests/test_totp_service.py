
"""Tests for TimanStat TOTP enrolment and verification services."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.security.totp import generate_totp_code
from timan_intelligence.security.totp_encryption import (
    decrypt_totp_secret,
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
    """Create an isolated database, encryption key and active user."""

    database_file = tmp_path / "test_totp_service.db"

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
        username="totptestuser",
        email="totptest@example.com",
        full_name="TOTP Test User",
        password="SecureTestPassword123!",
    )

    return user_id


def test_begin_totp_enrolment_creates_pending_secret(totp_user):
    """Beginning enrolment stores a protected pending secret."""

    result = begin_totp_enrolment(totp_user)

    assert isinstance(result, dict)
    assert result["secret"]
    assert result["provisioning_uri"].startswith("otpauth://totp/")

    with database_connection() as connection:
        user = connection.execute(
            """
            SELECT
                totp_enabled,
                totp_secret_encrypted,
                totp_pending_secret_encrypted,
                totp_pending_created_at
            FROM users
            WHERE id = ?
            """,
            (totp_user,),
        ).fetchone()

    assert bool(user["totp_enabled"]) is False
    assert user["totp_secret_encrypted"] is None
    assert user["totp_pending_secret_encrypted"] is not None
    assert user["totp_pending_created_at"] is not None

    assert user["totp_pending_secret_encrypted"] != result["secret"]

    assert (
        decrypt_totp_secret(user["totp_pending_secret_encrypted"])
        == result["secret"]
    )


def test_begin_totp_enrolment_rejects_unknown_user():
    """Enrolment must not proceed for a nonexistent account."""

    with pytest.raises(TOTPServiceError):
        begin_totp_enrolment("nonexistent-user")


def test_begin_totp_enrolment_rejects_inactive_user(totp_user):
    """Inactive accounts must not start TOTP enrolment."""

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = FALSE WHERE id = ?",
            (totp_user,),
        )

    with pytest.raises(TOTPServiceError):
        begin_totp_enrolment(totp_user)


def test_begin_totp_enrolment_rejects_already_enabled_user(totp_user):
    """An account with enabled TOTP must not start another enrolment."""

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET totp_enabled = TRUE
            WHERE id = ?
            """,
            (totp_user,),
        )

    with pytest.raises(TOTPServiceError):
        begin_totp_enrolment(totp_user)


def test_confirm_totp_enrolment_enables_two_factor_authentication(
    totp_user,
):
    """A valid authenticator code must complete enrolment."""

    result = begin_totp_enrolment(totp_user)

    code = generate_totp_code(
        result["secret"],
        at_time=TEST_TIMESTAMP,
    )

    confirmed = confirm_totp_enrolment(
        user_id=totp_user,
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is True

    with database_connection() as connection:
        user = connection.execute(
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
            (totp_user,),
        ).fetchone()

    assert bool(user["totp_enabled"]) is True
    assert user["totp_secret_encrypted"] is not None
    assert user["totp_pending_secret_encrypted"] is None
    assert user["totp_last_accepted_counter"] == TEST_TIMESTAMP // 30
    assert user["totp_enrolled_at"] is not None
    assert user["totp_pending_created_at"] is None

    assert (
        decrypt_totp_secret(user["totp_secret_encrypted"])
        == result["secret"]
    )


def test_confirm_totp_enrolment_rejects_invalid_code(totp_user):
    """An invalid code must not activate TOTP."""

    begin_totp_enrolment(totp_user)

    confirmed = confirm_totp_enrolment(
        user_id=totp_user,
        code="000000",
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is False

    with database_connection() as connection:
        user = connection.execute(
            """
            SELECT
                totp_enabled,
                totp_secret_encrypted,
                totp_pending_secret_encrypted
            FROM users
            WHERE id = ?
            """,
            (totp_user,),
        ).fetchone()

    assert bool(user["totp_enabled"]) is False
    assert user["totp_secret_encrypted"] is None
    assert user["totp_pending_secret_encrypted"] is not None


def test_confirm_totp_enrolment_returns_false_without_pending_secret(
    totp_user,
):
    """Confirmation must fail when no enrolment is pending."""

    confirmed = confirm_totp_enrolment(
        user_id=totp_user,
        code="123456",
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is False


def test_confirm_totp_enrolment_rejects_unknown_user():
    """A nonexistent account cannot complete enrolment."""

    confirmed = confirm_totp_enrolment(
        user_id="nonexistent-user",
        code="123456",
        at_time=TEST_TIMESTAMP,
    )

    assert confirmed is False


def test_confirm_totp_enrolment_rejects_repeated_confirmation(
    totp_user,
):
    """An already enrolled account cannot confirm enrolment again."""

    result = begin_totp_enrolment(totp_user)

    code = generate_totp_code(
        result["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        totp_user,
        code,
        at_time=TEST_TIMESTAMP,
    ) is True

    assert confirm_totp_enrolment(
        totp_user,
        code,
        at_time=TEST_TIMESTAMP,
    ) is False


def test_verify_totp_for_user_accepts_next_valid_code(totp_user):
    """An enrolled user must pass verification with a new valid code."""

    result = begin_totp_enrolment(totp_user)

    enrolment_code = generate_totp_code(
        result["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        totp_user,
        enrolment_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    next_timestamp = TEST_TIMESTAMP + 30

    next_code = generate_totp_code(
        result["secret"],
        at_time=next_timestamp,
    )

    verified = verify_totp_for_user(
        user_id=totp_user,
        code=next_code,
        at_time=next_timestamp,
    )

    assert verified is True

    with database_connection() as connection:
        user = connection.execute(
            """
            SELECT totp_last_accepted_counter
            FROM users
            WHERE id = ?
            """,
            (totp_user,),
        ).fetchone()

    assert user["totp_last_accepted_counter"] == next_timestamp // 30


def test_verify_totp_for_user_rejects_replayed_code(totp_user):
    """A successfully accepted TOTP code must not be reused."""

    result = begin_totp_enrolment(totp_user)

    code = generate_totp_code(
        result["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        totp_user,
        code,
        at_time=TEST_TIMESTAMP,
    ) is True

    verified = verify_totp_for_user(
        user_id=totp_user,
        code=code,
        at_time=TEST_TIMESTAMP,
    )

    assert verified is False


def test_verify_totp_for_user_rejects_invalid_code(totp_user):
    """Incorrect authenticator codes must not authenticate a user."""

    result = begin_totp_enrolment(totp_user)

    enrolment_code = generate_totp_code(
        result["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        totp_user,
        enrolment_code,
        at_time=TEST_TIMESTAMP,
    ) is True

    verified = verify_totp_for_user(
        user_id=totp_user,
        code="000000",
        at_time=TEST_TIMESTAMP + 30,
    )

    assert verified is False


def test_verify_totp_for_user_rejects_user_without_totp(totp_user):
    """Users without enabled TOTP must not pass TOTP verification."""

    verified = verify_totp_for_user(
        user_id=totp_user,
        code="123456",
        at_time=TEST_TIMESTAMP,
    )

    assert verified is False


def test_verify_totp_for_user_rejects_unknown_user():
    """A nonexistent account cannot pass TOTP verification."""

    verified = verify_totp_for_user(
        user_id="nonexistent-user",
        code="123456",
        at_time=TEST_TIMESTAMP,
    )

    assert verified is False


def test_verify_totp_for_user_rejects_inactive_user(totp_user):
    """Inactive accounts must not pass TOTP verification."""

    result = begin_totp_enrolment(totp_user)

    code = generate_totp_code(
        result["secret"],
        at_time=TEST_TIMESTAMP,
    )

    assert confirm_totp_enrolment(
        totp_user,
        code,
        at_time=TEST_TIMESTAMP,
    ) is True

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = FALSE WHERE id = ?",
            (totp_user,),
        )

    verified = verify_totp_for_user(
        user_id=totp_user,
        code=generate_totp_code(
            result["secret"],
            at_time=TEST_TIMESTAMP + 30,
        ),
        at_time=TEST_TIMESTAMP + 30,
    )

    assert verified is False


@pytest.mark.parametrize(
    "invalid_user_id",
    [
        "",
        "   ",
        None,
        123,
        [],
        {},
    ],
)
def test_totp_service_rejects_invalid_user_identifiers(
    invalid_user_id,
):
    """TOTP service operations must validate user identifiers."""

    with pytest.raises(TOTPServiceError):
        begin_totp_enrolment(invalid_user_id)
