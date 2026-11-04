
"""Versioned database migration runner for TimanStat."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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


class MigrationError(RuntimeError):
    """Raised when database migration cannot proceed."""


def _create_migration_table(connection) -> None:
    """Create the schema migration history table."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


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


def _validate_existing_schema(connection) -> None:
    """Check whether an unversioned existing database has the expected schema."""

    required_tables = {
        "users",
        "organisations",
        "organisation_memberships",
        "projects",
        "project_memberships",
        "audit_logs",
    }

    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        """
    ).fetchall()

    existing_tables = {row["name"] for row in rows}

    missing_tables = required_tables - existing_tables

    if missing_tables:
        raise MigrationError(
            "Existing database cannot be baselined. "
            f"Missing tables: {', '.join(sorted(missing_tables))}."
        )


def _record_migration(
    connection,
    migration: Migration,
) -> None:
    """Record a successfully executed migration."""

    connection.execute(
        """
        INSERT INTO schema_migrations (version, name)
        VALUES (?, ?)
        """,
        (migration.version, migration.name),
    )


def run_migrations(connection) -> None:
    """Apply pending database migrations in version order."""

    _create_migration_table(connection)

    applied = _get_applied_migrations(connection)

    _validate_migration_history(applied)

    # Handle databases created before migration tracking existed.
    if not applied:
        existing_tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
              AND name != 'schema_migrations'
            """
        ).fetchall()

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
