"""Federated identity account resolution for TimanStat."""

from __future__ import annotations

import re
import secrets
import uuid
from typing import Any

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


SUPPORTED_PROVIDERS = {"google", "microsoft"}


def _placeholder() -> str:
    return "%s" if get_database_type() == "postgresql" else "?"


def authenticate_federated_identity(
    provider: str,
    subject: str,
    email: str,
    email_verified: bool,
    full_name: str,
) -> dict[str, Any] | None:
    """Resolve a verified OIDC identity to an active TimanStat user.

    New users receive the normal 'user' role. Existing accounts are linked
    only when the provider explicitly asserts that the email is verified.
    Provider subject IDs, rather than email addresses, identify returning
    federated users.
    """

    provider = provider.strip().lower() if isinstance(provider, str) else ""
    subject = subject.strip() if isinstance(subject, str) else ""
    email = email.strip().lower() if isinstance(email, str) else ""
    full_name = " ".join(full_name.split()) if isinstance(full_name, str) else ""

    if provider not in SUPPORTED_PROVIDERS:
        return None
    if not subject or len(subject) > 255:
        return None
    if not email_verified or not re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", email):
        return None
    if not full_name:
        full_name = email.split("@", 1)[0][:150] or "TimanStat user"

    p = _placeholder()

    with database_connection() as connection:
        linked = connection.execute(
            f"""
            SELECT u.id, u.username, u.email, u.full_name, u.role,
                   u.is_active, u.email_verified, u.totp_enabled
            FROM federated_identities fi
            JOIN users u ON u.id = fi.user_id
            WHERE fi.provider = {p} AND fi.subject = {p}
            """,
            (provider, subject),
        ).fetchone()

        if linked is not None:
            if not linked["is_active"] or not linked["email_verified"]:
                return None
            connection.execute(
                f"""
                UPDATE federated_identities
                SET last_login_at = CURRENT_TIMESTAMP, email = {p}
                WHERE provider = {p} AND subject = {p}
                """,
                (email, provider, subject),
            )
            connection.execute(
                f"""
                UPDATE users SET last_login_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = {p}
                """,
                (linked["id"],),
            )
            return dict(linked)

        existing = connection.execute(
            f"""
            SELECT id, username, email, full_name, role, is_active,
                   email_verified, totp_enabled
            FROM users WHERE LOWER(email) = {p}
            """,
            (email,),
        ).fetchone()

        if existing is not None:
            if not existing["is_active"] or not existing["email_verified"]:
                return None
            user = dict(existing)
        else:
            base = re.sub(r"[^a-z0-9_.-]", ".", email.split("@", 1)[0].lower())
            base = re.sub(r"[._-]+", ".", base).strip(".") or "user"
            base = base[:24]
            username = base
            while connection.execute(
                f"SELECT 1 FROM users WHERE username = {p}", (username,)
            ).fetchone() is not None:
                username = f"{base[:20]}.{secrets.token_hex(2)}"

            user_id = str(uuid.uuid4())
            # This marker is deliberately not a valid password hash.
            password_hash = "federated-only$" + secrets.token_urlsafe(32)
            connection.execute(
                f"""
                INSERT INTO users (
                    id, username, email, full_name, password_hash,
                    role, is_active, email_verified
                )
                VALUES ({p}, {p}, {p}, {p}, {p}, 'user', TRUE, TRUE)
                """,
                (user_id, username, email, full_name[:150], password_hash),
            )
            user = {
                "id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name[:150],
                "role": "user",
                "is_active": True,
                "email_verified": True,
                "totp_enabled": False,
            }

        connection.execute(
            f"""
            INSERT INTO federated_identities (
                id, user_id, provider, subject, email
            )
            VALUES ({p}, {p}, {p}, {p}, {p})
            """,
            (str(uuid.uuid4()), user["id"], provider, subject, email),
        )
        connection.execute(
            f"""
            UPDATE users SET last_login_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = {p}
            """,
            (user["id"],),
        )

        return user
