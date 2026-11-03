
"""Individual user registration and authentication services for TimanStat."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from typing import Any

from timan_intelligence.database.connection import database_connection, get_database_type


PASSWORD_SCRYPT_N = 2**14
PASSWORD_SCRYPT_R = 8
PASSWORD_SCRYPT_P = 1
PASSWORD_SALT_BYTES = 16
PASSWORD_KEY_BYTES = 64


def _new_id() -> str:
    """Generate a unique user identifier."""
    return str(uuid.uuid4())


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""
    return "%s" if get_database_type() == "postgresql" else "?"


def _normalise_email(email: str) -> str:
    """Validate and normalise an email address."""
    if not isinstance(email, str):
        raise ValueError("Email address must be text.")

    email = email.strip().lower()

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid email address.")

    return email


def _normalise_username(username: str) -> str:
    """Validate and normalise a username."""
    if not isinstance(username, str):
        raise ValueError("Username must be text.")

    username = username.strip().lower()

    if not re.fullmatch(r"[a-z0-9_.-]{3,30}", username):
        raise ValueError(
            "Username must be 3–30 characters and contain only "
            "letters, numbers, dots, underscores or hyphens."
        )

    return username


def _normalise_full_name(full_name: str) -> str:
    """Validate a user's full name."""
    if not isinstance(full_name, str):
        raise ValueError("Full name must be text.")

    full_name = " ".join(full_name.split())

    if len(full_name) < 2 or len(full_name) > 150:
        raise ValueError("Full name must be between 2 and 150 characters.")

    return full_name


def _hash_password(password: str) -> str:
    """Hash a password using scrypt and a unique random salt."""
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)

    password_hash = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=PASSWORD_SCRYPT_N,
        r=PASSWORD_SCRYPT_R,
        p=PASSWORD_SCRYPT_P,
        dklen=PASSWORD_KEY_BYTES,
    )

    return (
        f"scrypt${PASSWORD_SCRYPT_N}${PASSWORD_SCRYPT_R}$"
        f"{PASSWORD_SCRYPT_P}${salt.hex()}${password_hash.hex()}"
    )


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against its stored scrypt hash."""
    if not isinstance(password, str) or not isinstance(stored_hash, str):
        return False

    try:
        algorithm, n, r, p, salt_hex, hash_hex = stored_hash.split("$")

        if algorithm != "scrypt":
            return False

        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        if len(salt) != PASSWORD_SALT_BYTES:
            return False

        if len(expected_hash) != PASSWORD_KEY_BYTES:
            return False

        actual_hash = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected_hash),
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except (ValueError, TypeError, MemoryError):
        return False


def register_user(
    username: str,
    email: str,
    full_name: str,
    password: str,
) -> str:
    """
    Register a new individual TimanStat account.

    Public registration always creates a normal user account.
    Platform privileges cannot be selected during registration.

    Returns:
        The newly created user ID.
    """
    username = _normalise_username(username)
    email = _normalise_email(email)
    full_name = _normalise_full_name(full_name)
    password_hash = _hash_password(password)

    user_id = _new_id()
    p = _placeholder()

    with database_connection() as connection:
        existing = connection.execute(
            f"""
            SELECT id
            FROM users
            WHERE username = {p} OR email = {p}
            """,
            (username, email),
        ).fetchone()

        if existing is not None:
            raise ValueError(
                "An account with that username or email already exists."
            )

        connection.execute(
            f"""
            INSERT INTO users (
                id,
                username,
                email,
                full_name,
                password_hash,
                role,
                is_active,
                email_verified
            )
            VALUES ({p}, {p}, {p}, {p}, {p}, 'user', TRUE, FALSE)
            """,
            (
                user_id,
                username,
                email,
                full_name,
                password_hash,
            ),
        )

    return user_id


def authenticate_user(
    login_identifier: str,
    password: str,
) -> dict[str, Any] | None:
    """
    Authenticate an individual user using username or email.

    Returns:
        A user record without the password hash, or None if authentication fails.
    """
    if not isinstance(login_identifier, str) or not isinstance(password, str):
        return None

    login_identifier = login_identifier.strip().lower()

    if not login_identifier or not password:
        return None

    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT
                id,
                username,
                email,
                full_name,
                password_hash,
                role,
                is_active,
                email_verified
            FROM users
            WHERE username = {p} OR email = {p}
            """,
            (login_identifier, login_identifier),
        ).fetchone()

        if user is None:
            return None

        if not user["is_active"]:
            return None

        if not _verify_password(password, user["password_hash"]):
            return None

        connection.execute(
            f"""
            UPDATE users
            SET last_login_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
            """,
            (user["id"],),
        )

        result = dict(user)
        result.pop("password_hash", None)

        return result


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Retrieve an active user's public account details."""
    if not isinstance(user_id, str) or not user_id.strip():
        return None

    p = _placeholder()

    with database_connection() as connection:
        user = connection.execute(
            f"""
            SELECT
                id,
                username,
                email,
                full_name,
                role,
                is_active,
                email_verified,
                created_at,
                updated_at,
                last_login_at
            FROM users
            WHERE id = {p}
              AND is_active = TRUE
            """,
            (user_id.strip(),),
        ).fetchone()

    return dict(user) if user is not None else None
