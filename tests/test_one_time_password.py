"""Tests for TimanStat one-time-password cryptographic primitives."""

import pytest

from timan_intelligence.security.one_time_password import (
    OneTimePasswordError,
    generate_one_time_password,
    hash_one_time_password,
    verify_one_time_password,
)


TEST_PEPPER = "test-otp-pepper-with-at-least-32-bytes-long"


def test_generated_otp_is_six_decimal_digits():
    for _ in range(100):
        code = generate_one_time_password()
        assert len(code) == 6
        assert code.isascii()
        assert code.isdigit()


def test_generated_otp_preserves_leading_zero(monkeypatch):
    import timan_intelligence.security.one_time_password as otp

    monkeypatch.setattr(otp.secrets, "randbelow", lambda upper: 7)
    assert generate_one_time_password() == "000007"


def test_hash_and_verify_valid_otp():
    digest = hash_one_time_password(
        "042816",
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    )

    assert len(digest) == 64
    assert verify_one_time_password(
        "042816",
        digest,
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    ) is True


@pytest.mark.parametrize(
    ("user_id", "purpose", "pepper"),
    [
        ("another-user", "sms_login", TEST_PEPPER),
        ("user-123", "email_recovery", TEST_PEPPER),
        ("user-123", "sms_login", "different-otp-pepper-with-32-bytes"),
    ],
)
def test_digest_is_bound_to_user_purpose_and_pepper(
    user_id,
    purpose,
    pepper,
):
    digest = hash_one_time_password(
        "042816",
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    )

    assert verify_one_time_password(
        "042816",
        digest,
        user_id=user_id,
        purpose=purpose,
        pepper=pepper,
    ) is False


def test_wrong_code_is_rejected():
    digest = hash_one_time_password(
        "042816",
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    )

    assert verify_one_time_password(
        "042817",
        digest,
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    ) is False


@pytest.mark.parametrize("invalid_code", ["", "12345", "1234567", "12a456", " 12345"])
def test_hash_rejects_invalid_otp_format(invalid_code):
    with pytest.raises(OneTimePasswordError):
        hash_one_time_password(
            invalid_code,
            user_id="user-123",
            purpose="sms_login",
            pepper=TEST_PEPPER,
        )


@pytest.mark.parametrize("invalid_pepper", ["short", b"short", None])
def test_hash_rejects_missing_or_weak_pepper(invalid_pepper):
    with pytest.raises(OneTimePasswordError):
        hash_one_time_password(
            "123456",
            user_id="user-123",
            purpose="sms_login",
            pepper=invalid_pepper,
        )


@pytest.mark.parametrize(
    ("user_id", "purpose"),
    [
        ("", "sms_login"),
        ("user-123", ""),
        ("user-123", "sms login"),
        ("user-123", "x" * 65),
    ],
)
def test_hash_rejects_invalid_context(user_id, purpose):
    with pytest.raises(OneTimePasswordError):
        hash_one_time_password(
            "123456",
            user_id=user_id,
            purpose=purpose,
            pepper=TEST_PEPPER,
        )


def test_verify_rejects_malformed_digest_and_invalid_code():
    assert verify_one_time_password(
        "123456",
        "not-a-digest",
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    ) is False

    digest = hash_one_time_password(
        "123456",
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    )

    assert verify_one_time_password(
        "invalid",
        digest,
        user_id="user-123",
        purpose="sms_login",
        pepper=TEST_PEPPER,
    ) is False
