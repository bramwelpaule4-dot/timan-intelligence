
"""Audit logging service for TimanStat."""

from __future__ import annotations

import json
import uuid
from typing import Any

from timan_intelligence.database.connection import (
    database_connection,
    get_database_type,
)


def _new_id() -> str:
    """Generate a unique audit record identifier."""
    return str(uuid.uuid4())


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""
    return "%s" if get_database_type() == "postgresql" else "?"


def _serialise_details(details: dict[str, Any] | None) -> str | None:
    """Convert audit details into safe JSON text."""

    if details is None:
        return None

    if not isinstance(details, dict):
        raise ValueError("Audit details must be supplied as a dictionary.")

    forbidden_keys = {
        "password",
        "password_hash",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
    }

    safe_details = {
        key: value
        for key, value in details.items()
        if str(key).lower() not in forbidden_keys
    }

    return json.dumps(safe_details, default=str)


def record_audit_event(
    action: str,
    user_id: str | None = None,
    organisation_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> str:
    """
    Record an application or administrative activity.

    Returns:
        The new audit record ID.
    """

    if not isinstance(action, str) or not action.strip():
        raise ValueError("Audit action is required.")

    if user_id is not None and not isinstance(user_id, str):
        raise ValueError("User ID must be text.")

    if organisation_id is not None and not isinstance(organisation_id, str):
        raise ValueError("Organisation ID must be text.")

    if ip_address is not None and len(ip_address) > 45:
        raise ValueError("IP address is too long.")

    audit_id = _new_id()
    p = _placeholder()
    details_json = _serialise_details(details)

    with database_connection() as connection:
        connection.execute(
            f"""
            INSERT INTO audit_logs (
                id,
                user_id,
                organisation_id,
                action,
                resource_type,
                resource_id,
                details,
                ip_address
            )
            VALUES ({p}, {p}, {p}, {p}, {p}, {p}, {p}, {p})
            """,
            (
                audit_id,
                user_id.strip() if user_id else None,
                organisation_id.strip() if organisation_id else None,
                action.strip(),
                resource_type.strip() if resource_type else None,
                resource_id.strip() if resource_id else None,
                details_json,
                ip_address,
            ),
        )

    return audit_id


def list_audit_events(
    requested_by_role: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Retrieve recent platform audit events.

    Only Super Admins and platform Admins may access this function.
    """

    if requested_by_role not in {"super_admin", "admin"}:
        raise PermissionError(
            "Only platform administrators can view audit records."
        )

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError("Limit must be an integer.")

    if limit < 1 or limit > 1000:
        raise ValueError("Limit must be between 1 and 1000.")

    p = _placeholder()

    with database_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                id,
                user_id,
                organisation_id,
                action,
                resource_type,
                resource_id,
                details,
                ip_address,
                created_at
            FROM audit_logs
            ORDER BY created_at DESC
            LIMIT {p}
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
