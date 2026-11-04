
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


EXPECTED_FOREIGN_KEYS = {
    ("organisations", "created_by", "users", "id", "NO ACTION"),
    ("organisation_memberships", "organisation_id", "organisations", "id", "CASCADE"),
    ("organisation_memberships", "user_id", "users", "id", "CASCADE"),
    ("projects", "organisation_id", "organisations", "id", "CASCADE"),
    ("projects", "created_by", "users", "id", "SET NULL"),
    ("project_memberships", "project_id", "projects", "id", "CASCADE"),
    ("project_memberships", "user_id", "users", "id", "CASCADE"),
    ("audit_logs", "user_id", "users", "id", "SET NULL"),
    ("audit_logs", "organisation_id", "organisations", "id", "SET NULL"),
}


EXPECTED_UNIQUE_CONSTRAINTS = {
    ("organisation_memberships", ("organisation_id", "user_id")),
    ("project_memberships", ("project_id", "user_id")),
}


EXPECTED_CHECK_COUNTS = {
    "users": 1,
    "organisations": 1,
    "organisation_memberships": 2,
    "projects": 1,
    "project_memberships": 2,
}


EXPECTED_INDEXES = {
    "idx_memberships_user",
    "idx_memberships_organisation",
    "idx_projects_organisation",
    "idx_project_memberships_user",
    "idx_project_memberships_project",
    "idx_audit_user",
    "idx_audit_created",
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


def _validate_migration_history(applied: dict[int, str]) -> None:
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


def _get_foreign_keys(connection) -> set[tuple]:
    """Return foreign-key relationships and deletion rules."""

    if get_database_type() == "sqlite":
        foreign_keys = set()

        for table_name in EXPECTED_COLUMNS:
            rows = connection.execute(
                f"PRAGMA foreign_key_list('{table_name}')"
            ).fetchall()

            for row in rows:
                foreign_keys.add(
                    (
                        table_name,
                        row["from"],
                        row["table"],
                        row["to"],
                        row["on_delete"].upper(),
                    )
                )

        return foreign_keys

    rows = connection.execute(
        """
        SELECT
            source.relname AS table_name,
            source_column.attname AS column_name,
            target.relname AS referenced_table,
            target_column.attname AS referenced_column,
            CASE constraint_row.confdeltype
                WHEN 'a' THEN 'NO ACTION'
                WHEN 'r' THEN 'RESTRICT'
                WHEN 'c' THEN 'CASCADE'
                WHEN 'n' THEN 'SET NULL'
                WHEN 'd' THEN 'SET DEFAULT'
            END AS on_delete
        FROM pg_constraint AS constraint_row
        JOIN pg_class AS source
            ON source.oid = constraint_row.conrelid
        JOIN pg_namespace AS namespace
            ON namespace.oid = source.relnamespace
        JOIN pg_class AS target
            ON target.oid = constraint_row.confrelid
        JOIN LATERAL unnest(constraint_row.conkey)
            WITH ORDINALITY AS source_key(attnum, position)
            ON TRUE
        JOIN LATERAL unnest(constraint_row.confkey)
            WITH ORDINALITY AS target_key(attnum, position)
            ON target_key.position = source_key.position
        JOIN pg_attribute AS source_column
            ON source_column.attrelid = source.oid
           AND source_column.attnum = source_key.attnum
        JOIN pg_attribute AS target_column
            ON target_column.attrelid = target.oid
           AND target_column.attnum = target_key.attnum
        WHERE constraint_row.contype = 'f'
          AND namespace.nspname = current_schema()
        """
    ).fetchall()

    return {
        (
            row["table_name"],
            row["column_name"],
            row["referenced_table"],
            row["referenced_column"],
            row["on_delete"],
        )
        for row in rows
    }


def _get_unique_constraints(connection) -> set[tuple]:
    """Return unique constraints as table and ordered column pairs."""

    if get_database_type() == "sqlite":
        constraints = set()

        for table_name in EXPECTED_COLUMNS:
            indexes = connection.execute(
                f"PRAGMA index_list('{table_name}')"
            ).fetchall()

            for index in indexes:
                if not index["unique"]:
                    continue

                index_name = index["name"].replace("'", "''")

                columns = connection.execute(
                    f"PRAGMA index_info('{index_name}')"
                ).fetchall()

                ordered_columns = tuple(
                    row["name"]
                    for row in sorted(
                        columns,
                        key=lambda item: item["seqno"],
                    )
                )

                constraints.add((table_name, ordered_columns))

        return constraints

    rows = connection.execute(
        """
        SELECT
            constraint_row.conrelid::regclass::text AS table_name,
            ARRAY(
                SELECT attribute.attname
                FROM unnest(constraint_row.conkey)
                    WITH ORDINALITY AS key_column(attnum, position)
                JOIN pg_attribute AS attribute
                    ON attribute.attrelid = constraint_row.conrelid
                   AND attribute.attnum = key_column.attnum
                ORDER BY key_column.position
            ) AS columns
        FROM pg_constraint AS constraint_row
        JOIN pg_class AS relation
            ON relation.oid = constraint_row.conrelid
        JOIN pg_namespace AS namespace
            ON namespace.oid = relation.relnamespace
        WHERE constraint_row.contype = 'u'
          AND namespace.nspname = current_schema()
        """
    ).fetchall()

    return {
        (row["table_name"], tuple(row["columns"]))
        for row in rows
    }


def _get_check_constraint_counts(connection) -> dict[str, int]:
    """Return the number of check constraints for each expected table."""

    if get_database_type() == "sqlite":
        counts = {}

        for table_name in EXPECTED_COLUMNS:
            row = connection.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (table_name,),
            ).fetchone()

            sql = (row["sql"] or "").upper() if row else ""
            counts[table_name] = sql.count("CHECK")

        return counts

    rows = connection.execute(
        """
        SELECT
            constraint_row.conrelid::regclass::text AS table_name,
            COUNT(*) AS constraint_count
        FROM pg_constraint AS constraint_row
        JOIN pg_class AS relation
            ON relation.oid = constraint_row.conrelid
        JOIN pg_namespace AS namespace
            ON namespace.oid = relation.relnamespace
        WHERE constraint_row.contype = 'c'
          AND namespace.nspname = current_schema()
        GROUP BY constraint_row.conrelid
        """
    ).fetchall()

    return {
        row["table_name"]: int(row["constraint_count"])
        for row in rows
    }


def _get_existing_indexes(connection) -> set[str]:
    """Return the names of explicitly required database indexes."""

    if get_database_type() == "sqlite":
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT indexname AS name
            FROM pg_indexes
            WHERE schemaname = current_schema()
            """
        ).fetchall()

    return {row["name"] for row in rows}


def _validate_existing_schema(connection) -> None:
    """Validate tables, columns and structural constraints before baselining."""

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

    existing_foreign_keys = _get_foreign_keys(connection)
    missing_foreign_keys = EXPECTED_FOREIGN_KEYS - existing_foreign_keys

    if missing_foreign_keys:
        raise MigrationError(
            "Existing database is missing required foreign keys: "
            f"{sorted(missing_foreign_keys)}."
        )

    existing_unique_constraints = _get_unique_constraints(connection)
    missing_unique_constraints = (
        EXPECTED_UNIQUE_CONSTRAINTS - existing_unique_constraints
    )

    if missing_unique_constraints:
        raise MigrationError(
            "Existing database is missing required unique constraints: "
            f"{sorted(missing_unique_constraints)}."
        )

    check_counts = _get_check_constraint_counts(connection)

    for table_name, required_count in EXPECTED_CHECK_COUNTS.items():
        actual_count = check_counts.get(table_name, 0)

        if actual_count < required_count:
            raise MigrationError(
                f"Existing table '{table_name}' has {actual_count} "
                f"check constraints; at least {required_count} are required."
            )

    existing_indexes = _get_existing_indexes(connection)
    missing_indexes = EXPECTED_INDEXES - existing_indexes

    if missing_indexes:
        raise MigrationError(
            "Existing database is missing required indexes: "
            f"{', '.join(sorted(missing_indexes))}."
        )


def _record_migration(connection, migration: Migration) -> None:
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
