"""Tests for TimanStat password-reset token services."""

import hashlib

import pytest

from timan_intelligence.database.connection import database_connection
from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.identity.password_reset import (
    create_password_reset_token,
    reset_password_with_token,
)
from timan_intelligence.identity.service import (
    _verify_password,
    authenticate_user,
    register_user,
)


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    """Create an isolated SQLite database for each test."""

    database_file = tmp_path / "test_password_reset.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    initialise_database()

    return database_file


@pytest.fixture
def test_user(test_database):
    """Register a test account."""

    user_id = register_user(
        username="resetuser",
        email="reset@example.com",
        full_name="Reset User",
        password="OriginalSecurePassword123!",
    )

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET email_verified = TRUE
            WHERE id = ?
            """,
            (user_id,),
        )

    return user_id


def test_token_creation_stores_hash_not_plaintext(test_user):
    token = create_password_reset_token(test_user)

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT token_hash
            FROM password_reset_tokens
            WHERE user_id = ?
            """,
            (test_user,),
        ).fetchone()

    assert row is not None
    assert row["token_hash"] != token
    assert row["token_hash"] == hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()
    assert len(row["token_hash"]) == 64


def test_token_creation_does_not_change_password(test_user):
    token = create_password_reset_token(test_user)

    assert token

    assert authenticate_user(
        "resetuser",
        "OriginalSecurePassword123!",
    ) is not None


def test_valid_token_changes_password(test_user):
    token = create_password_reset_token(test_user)

    result = reset_password_with_token(
        token,
        "NewSecurePassword456!",
    )

    assert result is True

    assert authenticate_user(
        "resetuser",
        "NewSecurePassword456!",
    ) is not None


def test_old_password_no_longer_authenticates_after_reset(test_user):
    token = create_password_reset_token(test_user)

    assert reset_password_with_token(
        token,
        "NewSecurePassword456!",
    ) is True

    assert authenticate_user(
        "resetuser",
        "OriginalSecurePassword123!",
    ) is None


def test_successful_reset_consumes_token(test_user):
    token = create_password_reset_token(test_user)

    assert reset_password_with_token(
        token,
        "NewSecurePassword456!",
    ) is True

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT consumed_at
            FROM password_reset_tokens
            WHERE user_id = ?
            """,
            (test_user,),
        ).fetchone()

    assert row is not None
    assert row["consumed_at"] is not None


def test_token_cannot_be_used_twice(test_user):
    token = create_password_reset_token(test_user)

    assert reset_password_with_token(
        token,
        "NewSecurePassword456!",
    ) is True

    assert reset_password_with_token(
        token,
        "AnotherSecurePassword789!",
    ) is False

    assert authenticate_user(
        "resetuser",
        "NewSecurePassword456!",
    ) is not None


def test_invalid_token_is_rejected(test_user):
    create_password_reset_token(test_user)

    assert reset_password_with_token(
        "invalid-token",
        "NewSecurePassword456!",
    ) is False


def test_empty_token_is_rejected(test_user):
    assert reset_password_with_token(
        "",
        "NewSecurePassword456!",
    ) is False

    assert reset_password_with_token(
        "   ",
        "NewSecurePassword456!",
    ) is False


def test_non_string_token_is_rejected(test_user):
    assert reset_password_with_token(
        None,
        "NewSecurePassword456!",
    ) is False


def test_excessively_long_token_is_rejected(test_user):
    assert reset_password_with_token(
        "a" * 513,
        "NewSecurePassword456!",
    ) is False


def test_expired_token_is_rejected(test_user):
    token = create_password_reset_token(test_user)

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE password_reset_tokens
            SET expires_at = '2000-01-01 00:00:00'
            WHERE user_id = ?
            """,
            (test_user,),
        )

    assert reset_password_with_token(
        token,
        "NewSecurePassword456!",
    ) is False

    assert authenticate_user(
        "resetuser",
        "OriginalSecurePassword123!",
    ) is not None


def test_new_token_invalidates_previous_token(test_user):
    first_token = create_password_reset_token(test_user)
    second_token = create_password_reset_token(test_user)

    assert first_token != second_token

    assert reset_password_with_token(
        first_token,
        "FirstNewSecurePassword123!",
    ) is False

    assert reset_password_with_token(
        second_token,
        "SecondNewSecurePassword456!",
    ) is True


def test_token_creation_rejects_unknown_user(test_database):
    with pytest.raises(ValueError):
        create_password_reset_token("nonexistent-user-id")


def test_token_creation_rejects_inactive_user(test_user):
    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET is_active = FALSE
            WHERE id = ?
            """,
            (test_user,),
        )

    with pytest.raises(ValueError):
        create_password_reset_token(test_user)


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
    test_user,
    expiry_minutes,
):
    with pytest.raises(ValueError):
        create_password_reset_token(
            test_user,
            expiry_minutes=expiry_minutes,
        )


def test_token_creation_rejects_empty_user_id(test_database):
    with pytest.raises(ValueError):
        create_password_reset_token("")

    with pytest.raises(ValueError):
        create_password_reset_token("   ")

    with pytest.raises(ValueError):
        create_password_reset_token(None)


@pytest.mark.parametrize(
    "password",
    [
        "",
        "short",
        "12345678901",
        "a" * 1025,
        None,
    ],
)
def test_password_reset_rejects_invalid_password(
    test_user,
    password,
):
    token = create_password_reset_token(test_user)

    with pytest.raises((TypeError, ValueError)):
        reset_password_with_token(token, password)

    assert authenticate_user(
        "resetuser",
        "OriginalSecurePassword123!",
    ) is not None


def test_invalid_password_does_not_consume_token(test_user):
    token = create_password_reset_token(test_user)

    with pytest.raises(ValueError):
        reset_password_with_token(token, "short")

    assert reset_password_with_token(
        token,
        "NewSecurePassword456!",
    ) is True


def test_reset_for_inactive_account_is_rejected(test_user):
    token = create_password_reset_token(test_user)

    with database_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET is_active = FALSE
            WHERE id = ?
            """,
            (test_user,),
        )

    assert reset_password_with_token(
        token,
        "NewSecurePassword456!",
    ) is False


def test_reset_password_uses_existing_password_hashing(test_user):
    token = create_password_reset_token(test_user)

    new_password = "NewSecurePassword456!"

    assert reset_password_with_token(
        token,
        new_password,
    ) is True

    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT password_hash
            FROM users
            WHERE id = ?
            """,
            (test_user,),
        ).fetchone()

    assert row is not None
    assert _verify_password(new_password, row["password_hash"])
