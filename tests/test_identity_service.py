"""Tests for TimanStat individual registration and authentication."""

import pytest

from timan_intelligence.database.initialise import initialise_database
from timan_intelligence.database.connection import database_connection
from timan_intelligence.identity.email_verification import (
    create_email_verification_token,
    verify_email_token,
)
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


def register_test_user(
    username="testuser",
    email="testuser@example.com",
    full_name="Test User",
    password="SecureTestPassword123!",
):
    """Register a user and return the user ID."""

    return register_user(
        username=username,
        email=email,
        full_name=full_name,
        password=password,
    )


def verify_test_user(user_id):
    """Verify a registered user's email address."""

    token = create_email_verification_token(user_id)

    assert verify_email_token(token) is True


def test_register_user_creates_individual_account(test_database):
    user_id = register_test_user(
        username="bramwel",
        email="bramwel@example.com",
        full_name="Bramwel Paule",
    )

    user = get_user_by_id(user_id)

    assert user is not None
    assert user["username"] == "bramwel"
    assert user["email"] == "bramwel@example.com"
    assert user["full_name"] == "Bramwel Paule"
    assert user["role"] == "user"
    assert bool(user["is_active"]) is True
    assert bool(user["email_verified"]) is False


def test_registration_does_not_store_plain_text_password(test_database):
    password = "SecureTestPassword123!"

    user_id = register_test_user(password=password)

    with database_connection() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()

    assert row is not None
    assert row["password_hash"] != password
    assert row["password_hash"].startswith("scrypt$")


def test_unverified_user_cannot_login(test_database):
    register_test_user()

    user = authenticate_user(
        "testuser",
        "SecureTestPassword123!",
    )

    assert user is None


def test_verified_user_can_login_with_username(test_database):
    user_id = register_test_user()

    verify_test_user(user_id)

    user = authenticate_user(
        "testuser",
        "SecureTestPassword123!",
    )

    assert user is not None
    assert user["username"] == "testuser"
    assert "password_hash" not in user


def test_verified_user_can_login_with_email(test_database):
    user_id = register_test_user()

    verify_test_user(user_id)

    user = authenticate_user(
        "testuser@example.com",
        "SecureTestPassword123!",
    )

    assert user is not None
    assert user["email"] == "testuser@example.com"


def test_login_rejects_incorrect_password(test_database):
    user_id = register_test_user()

    verify_test_user(user_id)

    user = authenticate_user(
        "testuser",
        "WrongPassword123!",
    )

    assert user is None


def test_login_rejects_unknown_user(test_database):
    user = authenticate_user(
        "unknownuser",
        "SecureTestPassword123!",
    )

    assert user is None


def test_registration_rejects_short_password(test_database):
    with pytest.raises(ValueError):
        register_test_user(password="short")


def test_registration_rejects_duplicate_username(test_database):
    register_test_user(
        username="testuser",
        email="first@example.com",
    )

    with pytest.raises(ValueError):
        register_test_user(
            username="testuser",
            email="second@example.com",
        )


def test_registration_rejects_duplicate_email(test_database):
    register_test_user(
        username="firstuser",
        email="same@example.com",
    )

    with pytest.raises(ValueError):
        register_test_user(
            username="seconduser",
            email="same@example.com",
        )


def test_inactive_user_cannot_login(test_database):
    user_id = register_test_user()

    verify_test_user(user_id)

    with database_connection() as connection:
        connection.execute(
            "UPDATE users SET is_active = FALSE WHERE id = ?",
            (user_id,),
        )

    user = authenticate_user(
        "testuser",
        "SecureTestPassword123!",
    )

    assert user is None
