"""Tests for secure, single-use TOTP recovery codes."""

from __future__ import annotations

import hashlib

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.security.recovery_codes import (
    RECOVERY_CODE_COUNT,
    RecoveryCodeError,
    consume_recovery_code,
    generate_recovery_codes,
    get_recovery_code_count,
    regenerate_recovery_codes,
)
from timan_intelligence.security.totp import generate_totp_code
from timan_intelligence.security.totp_service import (
    begin_totp_enrolment,
    confirm_totp_enrolment,
)


@pytest.fixture
def totp_user(enrolled_user):
    """Return an enrolled user and their authenticator secret."""

    enrolment = begin_totp_enrolment(enrolled_user)
    code = generate_totp_code(enrolment["secret"])
    assert confirm_totp_enrolment(enrolled_user, code) is True
    return enrolled_user, enrolment["secret"]


def test_generate_recovery_codes_stores_only_hashes(totp_user):
    user_id, _ = totp_user

    codes = generate_recovery_codes(user_id)

    assert len(codes) == RECOVERY_CODE_COUNT
    assert len(set(codes)) == RECOVERY_CODE_COUNT
    assert all(len(code.replace("-", "")) == 32 for code in codes)
    assert get_recovery_code_count(user_id) == RECOVERY_CODE_COUNT

    with database_connection() as connection:
        rows = connection.execute(
            """
            SELECT code_hash
            FROM totp_recovery_codes
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()

    stored_hashes = {row["code_hash"] for row in rows}
    assert stored_hashes == {
        hashlib.sha256(code.replace("-", "").encode("ascii")).hexdigest()
        for code in codes
    }
    assert all(code.replace("-", "") not in stored_hashes for code in codes)


def test_recovery_code_can_only_be_used_once(totp_user):
    user_id, _ = totp_user
    codes = generate_recovery_codes(user_id)

    assert consume_recovery_code(user_id, codes[0]) is True
    assert consume_recovery_code(user_id, codes[0]) is False
    assert get_recovery_code_count(user_id) == RECOVERY_CODE_COUNT - 1


def test_recovery_code_accepts_case_and_separator_variations(totp_user):
    user_id, _ = totp_user
    code = generate_recovery_codes(user_id)[0]

    assert consume_recovery_code(
        user_id,
        code.lower().replace("-", " "),
    ) is True


def test_invalid_recovery_code_is_rejected(totp_user):
    user_id, _ = totp_user
    generate_recovery_codes(user_id)

    assert consume_recovery_code(user_id, "not-a-valid-code") is False
    assert get_recovery_code_count(user_id) == RECOVERY_CODE_COUNT


def test_regeneration_invalidates_all_previous_codes(totp_user):
    user_id, secret = totp_user
    previous = generate_recovery_codes(user_id)
    fresh_totp = generate_totp_code(secret)

    replacement = regenerate_recovery_codes(
        user_id,
        "SecureTestPassword123!",
        fresh_totp,
    )

    assert replacement is not None
    assert len(replacement) == RECOVERY_CODE_COUNT
    assert set(previous).isdisjoint(replacement)
    assert consume_recovery_code(user_id, previous[0]) is False
    assert consume_recovery_code(user_id, replacement[0]) is True


def test_regeneration_requires_current_password_and_authenticator(totp_user):
    user_id, secret = totp_user
    existing = generate_recovery_codes(user_id)

    assert regenerate_recovery_codes(
        user_id,
        "WrongPassword123!",
        generate_totp_code(secret),
    ) is None
    assert regenerate_recovery_codes(
        user_id,
        "SecureTestPassword123!",
        "000000",
    ) is None

    assert consume_recovery_code(user_id, existing[0]) is True


def test_recovery_codes_require_totp_enabled_account(enrolled_user):
    with pytest.raises(RecoveryCodeError):
        generate_recovery_codes(enrolled_user)
