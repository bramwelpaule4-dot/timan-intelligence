"""Tests for TimanStat email verification token services."""

import hashlib

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.email_verification import (
    create_email_verification_token,
    verify_email_token,
)
from timan_intelligence.identity.service import (
    get_user_by_id,
    register_user,
)


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""

    database_file = tmp_path / "test_email_verification.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    initialise_database()

    return database_file


def create_test_user():
    """Register a test account and return its ID."""

    return register_user(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        password="SecureTestPassword123!",
    )


def test_token_creation_stores_hash_not_plaintext(test_database):
    user_id = create_test_user()

    token = create_email_verification_token(user_id)

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT token_hash
            FROM email_verification_tokens
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    assert row is not None
    assert row["token_hash"] != token
    assert row["token_hash"] == hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
    assert len(row["token_hash"]) == 64


def test_new_token_does_not_automatically_verify_email(test_database):
    user_id = create_test_user()

    create_email_verification_token(user_id)

    user = get_user_by_id(user_id)

    assert user is not None
    assert bool(user["email_verified"]) is False


def test_valid_token_verifies_email(test_database):
    user_id = create_test_user()

    token = create_email_verification_token(user_id)

    result = verify_email_token(token)

    user = get_user_by_id(user_id)

    assert result is True
    assert user is not None
    assert bool(user["email_verified"]) is True


def test_successful_verification_consumes_token(test_database):
    user_id = create_test_user()

    token = create_email_verification_token(user_id)

    assert verify_email_token(token) is True

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT consumed_at
            FROM email_verification_tokens
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()

    assert row is not None
    assert row["consumed_at"] is not None


def test_token_cannot_be_used_twice(test_database):
    user_id = create_test_user()

    token = create_email_verification_token(user_id)

    assert verify_email_token(token) is True
    assert verify_email_token(token) is False


def test_invalid_token_is_rejected(test_database):
    user_id = create_test_user()

    create_email_verification_token(user_id)

    assert verify_email_token("invalid-token") is False


def test_empty_token_is_rejected(test_database):
    assert verify_email_token("") is False
    assert verify_email_token("   ") is False


def test_non_string_token_is_rejected(test_database):
    assert verify_email_token(None) is False
    assert verify_email_token(12345) is False


def test_excessively_long_token_is_rejected(test_database):
    assert verify_email_token("a" * 513) is False


def test_expired_token_is_rejected(test_database):
    user_id = create_test_user()

    token = create_email_verification_token(user_id)

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE email_verification_tokens
            SET expires_at = '2000-01-01 00:00:00'
            WHERE user_id = ?
            """,
            (user_id,),
        )

    assert verify_email_token(token) is False

    user = get_user_by_id(user_id)

    assert user is not None
    assert bool(user["email_verified"]) is False


def test_new_token_invalidates_previous_token(test_database):
    user_id = create_test_user()

    first_token = create_email_verification_token(user_id)
    second_token = create_email_verification_token(user_id)

    assert first_token != second_token
    assert verify_email_token(first_token) is False
    assert verify_email_token(second_token) is True


def test_token_creation_rejects_unknown_user(test_database):
    with pytest.raises(ValueError):
        create_email_verification_token("nonexistent-user-id")


def test_token_creation_rejects_inactive_user(test_database):
    user_id = create_test_user()

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET is_active = FALSE
            WHERE id = ?
            """,
            (user_id,),
        )

    with pytest.raises(ValueError):
        create_email_verification_token(user_id)


@pytest.mark.parametrize(
    "expiry_minutes",
    [
        0,
        -1,
        1441,
        1.5,
        "30",
        True,
        False,
        None,
    ],
)
def test_token_creation_rejects_invalid_expiry(
    test_database,
    expiry_minutes,
):
    user_id = create_test_user()

    with pytest.raises(ValueError):
        create_email_verification_token(
            user_id,
            expiry_minutes=expiry_minutes,
        )


def test_token_creation_rejects_empty_user_id(test_database):
    with pytest.raises(ValueError):
        create_email_verification_token("")

    with pytest.raises(ValueError):
        create_email_verification_token("   ")

    with pytest.raises(ValueError):
        create_email_verification_token(None)
