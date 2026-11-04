
"""Versioned database migration runner for TimanStat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from timan_intelligence.database.connection import get_database_type
from timan_intelligence.database.migrations.versions import (
    v0001_initial_schema,
)


@dataclass(frozen=True)
class Migration:
    """Represents one database schema migration."""

    version: int
    name: str
    upgrade: Callable


MIGRATIONS = (
    Migration(
        version=v0001_initial_schema.VERSION,
        name=v0001_initial_schema.NAME,
        upgrade=v0001_initial_schema.upgrade,
    ),
)

LATEST_SCHEMA_VERSION = max(
    (migration.version for migration in MIGRATIONS),
    default=0,
)

EXPECTED_COLUMNS = {
    "users": {
        "id", "username", "email", "full_name", "password_hash",
        "role", "is_active", "email_verified", "created_at",
        "updated_at", "last_login_at",
    },
    "organisations": {
        "id", "name", "organisation_type", "registration_number",
        "contact_email", "country", "status", "created_by",
        "created_at", "updated_at",
    },
    "organisation_memberships": {
        "id", "organisation_id", "user_id", "role", "status",
        "joined_at",
    },
    "projects": {
        "id", "organisation_id", "name", "description", "status",
        "created_by", "created_at", "updated_at",
    },
    "project_memberships": {
        "id", "project_id", "user_id", "role", "status", "joined_at",
    },
    "audit_logs": {
        "id", "user_id", "organisation_id", "action", "resource_type",
        "resource_id", "details", "ip_address", "created_at",
    },
}


class MigrationError(RuntimeError):
    """Raised when a database migration cannot proceed."""


def _placeholder() -> str:
    """Return the parameter placeholder for the configured database."""

    return "%s" if get_database_type() == "postgresql" else "?"


def _create_migration_table(connection) -> None:
    """Create the migration history table if it does not exist."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _get_existing_tables(connection) -> set[str]:
    """Return application table names for the configured backend."""

    if get_database_type() == "sqlite":
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
              AND name != 'schema_migrations'
            """
        ).fetchall()

    else:
        rows = connection.execute(
            """
            SELECT table_name AS name
            FROM information_schema.tables
            WHERE table_schema = current_schema()
              AND table_type = 'BASE TABLE'
              AND table_name != 'schema_migrations'
            """
        ).fetchall()

    return {row["name"] for row in rows}


def _get_applied_migrations(connection) -> dict[int, str]:
    """Return previously applied migrations."""

    rows = connection.execute(
        """
        SELECT version, name
        FROM schema_migrations
        ORDER BY version
        """
    ).fetchall()

    return {
        int(row["version"]): row["name"]
        for row in rows
    }


def _validate_migration_history(
    applied: dict[int, str],
) -> None:
    """Validate stored migration history against available migrations."""

    known_migrations = {
        migration.version: migration.name
        for migration in MIGRATIONS
    }

    for version, name in applied.items():
        if version not in known_migrations:
            raise MigrationError(
                f"Database contains unknown migration version {version}."
            )

        if known_migrations[version] != name:
            raise MigrationError(
                f"Migration name mismatch for version {version}: "
                f"database records '{name}', but code expects "
                f"'{known_migrations[version]}'."
            )

    versions = sorted(applied)

    if versions:
        expected_versions = list(range(1, versions[-1] + 1))

        if versions != expected_versions:
            raise MigrationError(
                "Database migration history contains missing versions."
            )


def _get_table_columns(connection, table_name: str) -> set[str]:
    """Return column names for a table."""

    if get_database_type() == "sqlite":
        rows = connection.execute(
            f"PRAGMA table_info('{table_name}')"
        ).fetchall()

        return {row["name"] for row in rows}

    placeholder = _placeholder()

    rows = connection.execute(
        f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = {placeholder}
        """,
        (table_name,),
    ).fetchall()

    return {row["column_name"] for row in rows}


def _validate_existing_schema(connection) -> None:
    """Validate the required tables and columns before baselining."""

    existing_tables = _get_existing_tables(connection)

    missing_tables = set(EXPECTED_COLUMNS) - existing_tables

    if missing_tables:
        raise MigrationError(
            "Existing database cannot be baselined. "
            f"Missing tables: {', '.join(sorted(missing_tables))}."
        )

    for table_name, required_columns in EXPECTED_COLUMNS.items():
        existing_columns = _get_table_columns(connection, table_name)
        missing_columns = required_columns - existing_columns

        if missing_columns:
            raise MigrationError(
                f"Existing table '{table_name}' cannot be baselined. "
                f"Missing columns: {', '.join(sorted(missing_columns))}."
            )


def _record_migration(
    connection,
    migration: Migration,
) -> None:
    """Record a successfully applied migration."""

    placeholder = _placeholder()

    connection.execute(
        f"""
        INSERT INTO schema_migrations (version, name)
        VALUES ({placeholder}, {placeholder})
        """,
        (migration.version, migration.name),
    )


def run_migrations(connection) -> None:
    """Apply pending migrations in version order."""

    _create_migration_table(connection)

    applied = _get_applied_migrations(connection)

    _validate_migration_history(applied)

    if not applied:
        existing_tables = _get_existing_tables(connection)

        if existing_tables:
            _validate_existing_schema(connection)

            baseline = MIGRATIONS[0]
            _record_migration(connection, baseline)

            applied = {
                baseline.version: baseline.name
            }

    for migration in MIGRATIONS:
        if migration.version in applied:
            continue

        expected_version = len(applied) + 1

        if migration.version != expected_version:
            raise MigrationError(
                f"Cannot apply migration {migration.version}. "
                f"Expected migration {expected_version}."
            )

        migration.upgrade(connection)
        _record_migration(connection, migration)

        applied[migration.version] = migration.name
