"""Tests for database-backed TimanStat OTP challenges."""

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.service import register_user
from timan_intelligence.security.one_time_password_service import (
    OTPChallengeServiceError,
    create_otp_challenge,
    set_phone_number_for_verification,
    set_recovery_email_for_verification,
    verify_otp_challenge,
)


TEST_PEPPER = "test-only-otp-pepper-with-at-least-32-bytes"


@pytest.fixture
def otp_user(tmp_path, monkeypatch):
    database_file = tmp_path / "otp_challenge_test.db"
    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )
    monkeypatch.setenv("TIMANSTAT_OTP_PEPPER", TEST_PEPPER)
    monkeypatch.setenv(
        "TIMANSTAT_RATE_LIMIT_HMAC_KEY",
        "test-rate-limit-hmac-key-with-at-least-32-bytes",
    )
    initialise_database()

    user_id = register_user(
        username="otp_challenge_user",
        email="otp_challenge@example.com",
        full_name="OTP Challenge User",
        password="SecureTestPassword123!",
    )
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET phone_number_e164 = '+254712345678',
                phone_verified = TRUE,
                recovery_email = 'recovery@example.com',
                recovery_email_verified = TRUE
            WHERE id = ?
            """,
            (user_id,),
        )
    return user_id


def _get_challenge(challenge_id):
    with database_connection() as connection:
        return connection.execute(
            """
            SELECT *
            FROM one_time_password_challenges
            WHERE id = ?
            """,
            (challenge_id,),
        ).fetchone()


def test_create_otp_challenge_stores_only_hash_and_returns_code(otp_user):
    result = create_otp_challenge(otp_user, "login_mfa", "sms")
    row = _get_challenge(result["challenge_id"])

    assert result["code"].isascii()
    assert len(result["code"]) == 6
    assert row is not None
    assert row["user_id"] == otp_user
    assert row["purpose"] == "login_mfa"
    assert row["channel"] == "sms"
    assert row["code_hash"] != result["code"]
    assert len(row["code_hash"]) == 64
    assert row["failed_attempts"] == 0
    assert row["max_attempts"] == 5
    assert row["consumed_at"] is None
    assert row["invalidated_at"] is None


@pytest.mark.parametrize("channel", ["sms", "email"])
def test_valid_code_is_consumed_and_cannot_be_reused(otp_user, channel):
    challenge = create_otp_challenge(otp_user, "login_mfa", channel)

    assert verify_otp_challenge(
        challenge["challenge_id"],
        otp_user,
        "login_mfa",
        challenge["code"],
    ) is True
    assert _get_challenge(challenge["challenge_id"])["consumed_at"] is not None
    assert verify_otp_challenge(
        challenge["challenge_id"],
        otp_user,
        "login_mfa",
        challenge["code"],
    ) is False


def test_wrong_code_increments_failed_attempts(otp_user):
    challenge = create_otp_challenge(otp_user, "login_mfa", "sms")

    assert verify_otp_challenge(
        challenge["challenge_id"], otp_user, "login_mfa", "000000"
    ) is False
    row = _get_challenge(challenge["challenge_id"])
    assert row["failed_attempts"] == 1
    assert row["consumed_at"] is None


def test_challenge_is_rejected_after_five_failed_attempts(otp_user):
    challenge = create_otp_challenge(otp_user, "login_mfa", "sms")

    for _ in range(5):
        assert verify_otp_challenge(
            challenge["challenge_id"], otp_user, "login_mfa", "000000"
        ) is False

    row = _get_challenge(challenge["challenge_id"])
    assert row["failed_attempts"] == 5
    assert verify_otp_challenge(
        challenge["challenge_id"],
        otp_user,
        "login_mfa",
        challenge["code"],
    ) is False


def test_new_challenge_invalidates_previous_active_challenge(otp_user):
    first = create_otp_challenge(otp_user, "login_mfa", "sms")
    second = create_otp_challenge(otp_user, "login_mfa", "email")

    assert _get_challenge(first["challenge_id"])["invalidated_at"] is not None
    assert verify_otp_challenge(
        first["challenge_id"], otp_user, "login_mfa", first["code"]
    ) is False
    assert verify_otp_challenge(
        second["challenge_id"], otp_user, "login_mfa", second["code"]
    ) is True


def test_challenge_cannot_be_used_for_another_user_or_purpose(otp_user):
    challenge = create_otp_challenge(otp_user, "login_mfa", "sms")

    assert verify_otp_challenge(
        challenge["challenge_id"],
        "different-user",
        "login_mfa",
        challenge["code"],
    ) is False
    assert verify_otp_challenge(
        challenge["challenge_id"],
        otp_user,
        "password_recovery",
        challenge["code"],
    ) is False
    assert _get_challenge(challenge["challenge_id"])["consumed_at"] is None


def test_expired_challenge_is_rejected(otp_user):
    challenge = create_otp_challenge(otp_user, "login_mfa", "sms")
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE one_time_password_challenges
            SET expires_at = datetime('now', '-1 minute')
            WHERE id = ?
            """,
            (challenge["challenge_id"],),
        )

    assert verify_otp_challenge(
        challenge["challenge_id"],
        otp_user,
        "login_mfa",
        challenge["code"],
    ) is False


@pytest.mark.parametrize("channel", ["sms", "email"])
def test_unverified_contact_method_cannot_receive_challenge(
    otp_user, channel
):
    column = "phone_verified" if channel == "sms" else "recovery_email_verified"
    with database_connection() as connection:
        connection.execute(
            f"UPDATE users SET {column} = FALSE WHERE id = ?",
            (otp_user,),
        )

    with pytest.raises(
        OTPChallengeServiceError,
        match="must be verified",
    ):
        create_otp_challenge(otp_user, "login_mfa", channel)


def test_inactive_user_cannot_receive_challenge(otp_user):
    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = FALSE WHERE id = ?",
            (otp_user,),
        )

    with pytest.raises(OTPChallengeServiceError, match="active user"):
        create_otp_challenge(otp_user, "login_mfa", "sms")


def test_service_fails_closed_without_configured_pepper(otp_user, monkeypatch):
    monkeypatch.delenv("TIMANSTAT_OTP_PEPPER")
    with pytest.raises(OTPChallengeServiceError, match="not configured"):
        create_otp_challenge(otp_user, "login_mfa", "sms")


def test_invalid_challenge_inputs_are_rejected(otp_user):
    with pytest.raises(OTPChallengeServiceError):
        create_otp_challenge(otp_user, "invalid purpose", "sms")
    with pytest.raises(OTPChallengeServiceError):
        create_otp_challenge(otp_user, "login_mfa", "voice")
    assert verify_otp_challenge("", otp_user, "login_mfa", "123456") is False



def test_phone_number_change_requires_password_and_resets_verification(otp_user):
    with pytest.raises(OTPChallengeServiceError, match="password"):
        set_phone_number_for_verification(
            otp_user, "+254722123456", "IncorrectPassword123!"
        )

    updated = set_phone_number_for_verification(
        otp_user, "+254722123456", "SecureTestPassword123!"
    )
    assert updated == "+254722123456"

    with database_connection() as connection:
        user = connection.execute(
            "SELECT phone_number_e164, phone_verified FROM users WHERE id = ?",
            (otp_user,),
        ).fetchone()
    assert user["phone_number_e164"] == "+254722123456"
    assert bool(user["phone_verified"]) is False


def test_phone_contact_verification_marks_only_matching_number_verified(otp_user):
    set_phone_number_for_verification(
        otp_user, "+254722123456", "SecureTestPassword123!"
    )
    challenge = create_otp_challenge(otp_user, "verify_phone", "sms")

    assert verify_otp_challenge(
        challenge["challenge_id"], otp_user, "verify_phone", challenge["code"]
    ) is True

    with database_connection() as connection:
        user = connection.execute(
            "SELECT phone_verified FROM users WHERE id = ?",
            (otp_user,),
        ).fetchone()
    assert bool(user["phone_verified"]) is True


def test_old_phone_code_cannot_verify_a_replaced_number(otp_user):
    set_phone_number_for_verification(
        otp_user, "+254722123456", "SecureTestPassword123!"
    )
    challenge = create_otp_challenge(otp_user, "verify_phone", "sms")

    set_phone_number_for_verification(
        otp_user, "+254733123456", "SecureTestPassword123!"
    )
    assert verify_otp_challenge(
        challenge["challenge_id"], otp_user, "verify_phone", challenge["code"]
    ) is False

    with database_connection() as connection:
        user = connection.execute(
            "SELECT phone_number_e164, phone_verified FROM users WHERE id = ?",
            (otp_user,),
        ).fetchone()
    assert user["phone_number_e164"] == "+254733123456"
    assert user["phone_verified"] is False


def test_recovery_email_change_and_verification(otp_user):
    updated = set_recovery_email_for_verification(
        otp_user, "new-recovery@example.com", "SecureTestPassword123!"
    )
    assert updated == "new-recovery@example.com"

    challenge = create_otp_challenge(
        otp_user, "verify_recovery_email", "email"
    )
    assert verify_otp_challenge(
        challenge["challenge_id"],
        otp_user,
        "verify_recovery_email",
        challenge["code"],
    ) is True

    with database_connection() as connection:
        user = connection.execute(
            "SELECT recovery_email, recovery_email_verified FROM users WHERE id = ?",
            (otp_user,),
        ).fetchone()
    assert user["recovery_email"] == "new-recovery@example.com"
    assert bool(user["recovery_email_verified"]) is True


def test_contact_verification_purpose_rejects_wrong_channel(otp_user):
    set_phone_number_for_verification(
        otp_user, "+254722123456", "SecureTestPassword123!"
    )
    with pytest.raises(OTPChallengeServiceError, match="channel"):
        create_otp_challenge(otp_user, "verify_phone", "email")


def test_contact_verification_requires_a_pending_contact(otp_user):
    with pytest.raises(OTPChallengeServiceError, match="already verified"):
        create_otp_challenge(otp_user, "verify_phone", "sms")
