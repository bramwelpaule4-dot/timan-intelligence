
"""Tests for TimanStat individual registration and authentication."""

import pytest

from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.database.connection import database_connection
from timan_intelligence.identity.service import (
    register_user,
    authenticate_user,
    get_user_by_id,
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


def test_register_user_creates_individual_account(test_database):
    """A new account should be created with the normal user role."""

    user_id = register_user(
        username="bramwel",
        email="bramwel@example.com",
        full_name="Bramwel Paule",
        password="SecureTestPassword123!",
    )

    user = get_user_by_id(user_id)

    assert user is not None
    assert user["username"] == "bramwel"
    assert user["email"] == "bramwel@example.com"
    assert user["full_name"] == "Bramwel Paule"
    assert user["role"] == "user"
    assert user["is_active"] is True


def test_registration_does_not_store_plain_text_password(test_database):
    """The database should store a password hash, not the original password."""

    password = "SecureTestPassword123!"

    user_id = register_user(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        password=password,
    )

    with database_connection() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    assert row is not None
    assert row["password_hash"] != password
    assert row["password_hash"].startswith("scrypt$")


def test_user_can_login_with_username(test_database):
    """A registered user should be able to log in with their username."""

    register_user(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        password="SecureTestPassword123!",
    )

    user = authenticate_user(
        "testuser",
        "SecureTestPassword123!",
    )

    assert user is not None
    assert user["username"] == "testuser"
    assert "password_hash" not in user


def test_user_can_login_with_email(test_database):
    """A registered user should be able to log in with their email."""

    register_user(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        password="SecureTestPassword123!",
    )

    user = authenticate_user(
        "testuser@example.com",
        "SecureTestPassword123!",
    )

    assert user is not None
    assert user["email"] == "testuser@example.com"


def test_login_rejects_incorrect_password(test_database):
    """An incorrect password should not authenticate the user."""

    register_user(
        username="testuser",
        email="testuser@example.com",
        full_name="Test User",
        password="SecureTestPassword123!",
    )

    user = authenticate_user(
        "testuser",
        "WrongPassword123!",
    )

    assert user is None


def test_login_rejects_unknown_user(test_database):
    """An unknown account should not authenticate."""

    user = authenticate_user(
        "unknownuser",
        "SecureTestPassword123!",
    )

    assert user is None


def test_registration_rejects_short_password(test_database):
    """Passwords shorter than 12 characters should be rejected."""

    with pytest.raises(ValueError):
        register_user(
            username="testuser",
            email="testuser@example.com",
            full_name="Test User",
            password="short",
        )


def test_registration_rejects_duplicate_username(test_database):
    """A username must be unique."""

    register_user(
        username="testuser",
        email="first@example.com",
        full_name="First User",
        password="SecureTestPassword123!",
    )

    with pytest.raises(ValueError):
        register_user(
            username="testuser",
            email="second@example.com",
            full_name="Second User",
            password="AnotherSecurePassword123!",
        )


def test_registration_rejects_duplicate_email(test_database):
    """An email address must be unique."""

    register_user(
        username="firstuser",
        email="same@example.com",
        full_name="First User",
        password="SecureTestPassword123!",
    )

    with pytest.raises(ValueError):
        register_user(
            username="seconduser",
            email="same@example.com",
            full_name="Second User",
            password="AnotherSecurePassword123!",
        )


def test_inactive_user_cannot_login(test_database):
    """Deactivated accounts should not be allowed to log in."""

    user_id = register_user(
        username="inactiveuser",
        email="inactive@example.com",
        full_name="Inactive User",
        password="SecureTestPassword123!",
    )

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = FALSE WHERE id = ?",
            (user_id,),
        )

    user = authenticate_user(
        "inactiveuser",
        "SecureTestPassword123!",
    )

    assert user is None
