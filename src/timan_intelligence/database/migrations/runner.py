
"""Versioned database migration runner for TimanStat."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from timan_intelligence.database.connection import get_database_type
from timan_intelligence.database.migrations.versions import (
    v0001_initial_schema,
    v0002_totp_enrolment,
    v0003_email_verification,
    v0004_password_reset,
    v0005_session_version,
    v0006_totp_recovery_codes,
    v0007_distributed_rate_limits,
    v0008_rate_limit_timestamp_precision,
    v0009_subscriptions,
    v0010_entitlement_usage,
    v0011_subscription_change_requests,
    v0012_completed_subscription_changes,
    v0013_billing_records,
    v0014_billing_invoice_item_order,
    v0015_billing_subscription_change_requests,
    v0016_unique_subscription_upgrade_invoice,
    v0017_payment_gateway_sessions,
    v0018_mpesa_transaction_reconciliation,
    v0019_federated_identity_links,
    v0020_user_contact_methods,
    v0021_one_time_password_challenges,
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
    Migration(
        version=v0002_totp_enrolment.VERSION,
        name=v0002_totp_enrolment.NAME,
        upgrade=v0002_totp_enrolment.upgrade,
    ),
    Migration(
        version=v0003_email_verification.VERSION,
        name=v0003_email_verification.NAME,
        upgrade=v0003_email_verification.upgrade,
    ),
    Migration(
        version=v0004_password_reset.VERSION,
        name=v0004_password_reset.NAME,
        upgrade=v0004_password_reset.upgrade,
    ),
    Migration(
        version=v0005_session_version.VERSION,
        name=v0005_session_version.NAME,
        upgrade=v0005_session_version.upgrade,
    ),
    Migration(
        version=v0006_totp_recovery_codes.VERSION,
        name=v0006_totp_recovery_codes.NAME,
        upgrade=v0006_totp_recovery_codes.upgrade,
    ),
    Migration(
        version=v0007_distributed_rate_limits.VERSION,
        name=v0007_distributed_rate_limits.NAME,
        upgrade=v0007_distributed_rate_limits.upgrade,
    ),
    Migration(
        version=v0008_rate_limit_timestamp_precision.VERSION,
        name=v0008_rate_limit_timestamp_precision.NAME,
        upgrade=v0008_rate_limit_timestamp_precision.upgrade,
    ),
    Migration(
        version=v0009_subscriptions.VERSION,
        name=v0009_subscriptions.NAME,
        upgrade=v0009_subscriptions.upgrade,
    ),
    Migration(
        version=v0010_entitlement_usage.VERSION,
        name=v0010_entitlement_usage.NAME,
        upgrade=v0010_entitlement_usage.upgrade,
    ),
    Migration(
        version=v0011_subscription_change_requests.VERSION,
        name=v0011_subscription_change_requests.NAME,
        upgrade=v0011_subscription_change_requests.upgrade,
    ),
    Migration(
        version=v0012_completed_subscription_changes.VERSION,
        name=v0012_completed_subscription_changes.NAME,
        upgrade=v0012_completed_subscription_changes.upgrade,
    ),
    Migration(
        version=v0013_billing_records.VERSION,
        name=v0013_billing_records.NAME,
        upgrade=v0013_billing_records.upgrade,
    ),
    Migration(
        version=v0014_billing_invoice_item_order.VERSION,
        name=v0014_billing_invoice_item_order.NAME,
        upgrade=v0014_billing_invoice_item_order.upgrade,
    ),
    Migration(
        version=v0015_billing_subscription_change_requests.VERSION,
        name=v0015_billing_subscription_change_requests.NAME,
        upgrade=v0015_billing_subscription_change_requests.upgrade,
    ),
    Migration(
        version=v0016_unique_subscription_upgrade_invoice.VERSION,
        name=v0016_unique_subscription_upgrade_invoice.NAME,
        upgrade=v0016_unique_subscription_upgrade_invoice.upgrade,
    ),
    Migration(
        version=v0017_payment_gateway_sessions.VERSION,
        name=v0017_payment_gateway_sessions.NAME,
        upgrade=v0017_payment_gateway_sessions.upgrade,
    ),
    Migration(
        version=v0018_mpesa_transaction_reconciliation.VERSION,
        name=v0018_mpesa_transaction_reconciliation.NAME,
        upgrade=v0018_mpesa_transaction_reconciliation.upgrade,
    ),
    Migration(
        version=v0019_federated_identity_links.VERSION,
        name=v0019_federated_identity_links.NAME,
        upgrade=v0019_federated_identity_links.upgrade,
    ),
    Migration(
        version=v0020_user_contact_methods.VERSION,
        name=v0020_user_contact_methods.NAME,
        upgrade=v0020_user_contact_methods.upgrade,
    ),
    Migration(
        version=v0021_one_time_password_challenges.VERSION,
        name=v0021_one_time_password_challenges.NAME,
        upgrade=v0021_one_time_password_challenges.upgrade,
    ),
)

LATEST_SCHEMA_VERSION = max(
    (migration.version for migration in MIGRATIONS),
    default=0,
)


# These columns describe the original schema (v0001).
# Keep them separate from later migration additions because this
# definition is also used to validate unversioned legacy databases.
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


EXPECTED_CHECK_CONSTRAINTS = {
    ("users", "role"): {
        "super_admin", "admin", "developer", "user",
    },
    ("organisations", "status"): {
        "active", "suspended", "closed",
    },
    ("organisation_memberships", "role"): {
        "org_admin", "org_member",
    },
    ("organisation_memberships", "status"): {
        "active", "pending", "suspended",
    },
    ("projects", "status"): {
        "active", "on_hold", "completed", "archived",
    },
    ("project_memberships", "role"): {
        "project_admin", "project_member",
    },
    ("project_memberships", "status"): {
        "active", "pending", "suspended",
    },
}


EXPECTED_INDEXES = {
    "idx_memberships_user": (
        "organisation_memberships",
        ("user_id",),
    ),
    "idx_memberships_organisation": (
        "organisation_memberships",
        ("organisation_id",),
    ),
    "idx_projects_organisation": (
        "projects",
        ("organisation_id",),
    ),
    "idx_project_memberships_user": (
        "project_memberships",
        ("user_id",),
    ),
    "idx_project_memberships_project": (
        "project_memberships",
        ("project_id",),
    ),
    "idx_audit_user": (
        "audit_logs",
        ("user_id",),
    ),
    "idx_audit_created": (
        "audit_logs",
        ("created_at",),
    ),
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
            relation.relname AS table_name,
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


def _get_check_constraint_definitions(connection) -> list[tuple[str, str]]:
    """Return check-constraint definitions for expected application tables."""

    if get_database_type() == "sqlite":
        definitions = []

        for table_name in EXPECTED_COLUMNS:
            row = connection.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (table_name,),
            ).fetchone()

            if not row or not row["sql"]:
                continue

            # The current schema uses simple IN-list CHECK expressions.
            pattern = re.compile(
                r"CHECK\s*\(\s*"
                r"(?:\"?)([a-zA-Z_][a-zA-Z0-9_]*)(?:\"?)"
                r"\s+IN\s*\(([^()]*)\)\s*\)",
                re.IGNORECASE,
            )

            for match in pattern.finditer(row["sql"]):
                definitions.append((table_name, match.group(0)))

        return definitions

    rows = connection.execute(
        """
        SELECT
            relation.relname AS table_name,
            pg_get_constraintdef(constraint_row.oid) AS definition
        FROM pg_constraint AS constraint_row
        JOIN pg_class AS relation
            ON relation.oid = constraint_row.conrelid
        JOIN pg_namespace AS namespace
            ON namespace.oid = relation.relnamespace
        WHERE constraint_row.contype = 'c'
          AND namespace.nspname = current_schema()
        """
    ).fetchall()

    return [
        (row["table_name"], row["definition"])
        for row in rows
    ]


def _parse_check_constraint(
    table_name: str,
    definition: str,
) -> tuple[str, set[str]] | None:
    """Extract the checked column and allowed string values."""

    expected_columns = {
        column
        for table, column in EXPECTED_CHECK_CONSTRAINTS
        if table == table_name
    }

    for column_name in expected_columns:
        column_pattern = (
            rf'(?<![a-zA-Z0-9_])"?{re.escape(column_name)}"?(?![a-zA-Z0-9_])'
        )

        if not re.search(column_pattern, definition, re.IGNORECASE):
            continue

        # SQLite uses IN (...); PostgreSQL commonly represents this as
        # equality against ANY (ARRAY[...]).
        if not re.search(r"\b(IN|ANY)\b", definition, re.IGNORECASE):
            continue

        values = re.findall(
            r"'((?:''|[^'])*)'",
            definition,
        )

        if not values:
            continue

        decoded_values = {
            value.replace("''", "'")
            for value in values
        }

        return column_name, decoded_values

    return None


def _get_check_constraints(connection) -> dict[tuple[str, str], set[str]]:
    """Return check constraints mapped to their exact allowed values."""

    actual_constraints = {}

    for table_name, definition in _get_check_constraint_definitions(
        connection
    ):
        parsed = _parse_check_constraint(table_name, definition)

        if parsed is None:
            continue

        column_name, allowed_values = parsed
        key = (table_name, column_name)

        if key in actual_constraints:
            raise MigrationError(
                f"Existing table '{table_name}' has duplicate or "
                f"unexpected CHECK constraints for '{column_name}'."
            )

        actual_constraints[key] = allowed_values

    return actual_constraints


def _get_existing_indexes(connection) -> dict[str, tuple[str, tuple[str, ...]]]:
    """Return index names mapped to their table and ordered key columns."""

    indexes = {}

    if get_database_type() == "sqlite":
        rows = connection.execute(
            """
            SELECT name, tbl_name
            FROM sqlite_master
            WHERE type = 'index'
              AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()

        for row in rows:
            index_name = row["name"].replace("'", "''")

            columns = connection.execute(
                f"PRAGMA index_info('{index_name}')"
            ).fetchall()

            ordered_columns = tuple(
                column["name"]
                for column in sorted(
                    columns,
                    key=lambda item: item["seqno"],
                )
                if column["name"] is not None
            )

            indexes[row["name"]] = (
                row["tbl_name"],
                ordered_columns,
            )

        return indexes

    rows = connection.execute(
        """
        SELECT
            index_class.relname AS name,
            table_class.relname AS table_name,
            ARRAY(
                SELECT attribute.attname
                FROM unnest(index_row.indkey)
                    WITH ORDINALITY AS index_key(attnum, position)
                JOIN pg_attribute AS attribute
                    ON attribute.attrelid = index_row.indrelid
                   AND attribute.attnum = index_key.attnum
                WHERE index_key.position <= index_row.indnkeyatts
                ORDER BY index_key.position
            ) AS columns
        FROM pg_index AS index_row
        JOIN pg_class AS index_class
            ON index_class.oid = index_row.indexrelid
        JOIN pg_class AS table_class
            ON table_class.oid = index_row.indrelid
        JOIN pg_namespace AS namespace
            ON namespace.oid = table_class.relnamespace
        WHERE namespace.nspname = current_schema()
        """
    ).fetchall()

    for row in rows:
        indexes[row["name"]] = (
            row["table_name"],
            tuple(row["columns"]),
        )

    return indexes


def _validate_existing_schema(connection) -> None:
    """Validate the original schema before baselining a legacy database."""

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

    actual_checks = _get_check_constraints(connection)

    for key, expected_values in EXPECTED_CHECK_CONSTRAINTS.items():
        actual_values = actual_checks.get(key)

        if actual_values is None:
            raise MigrationError(
                f"Existing table '{key[0]}' is missing the required "
                f"CHECK constraint for column '{key[1]}'."
            )

        if actual_values != expected_values:
            raise MigrationError(
                f"Existing table '{key[0]}' has an incorrect CHECK "
                f"constraint for column '{key[1]}'. "
                f"Expected values: {sorted(expected_values)}; "
                f"found: {sorted(actual_values)}."
            )

    unexpected_checks = set(actual_checks) - set(EXPECTED_CHECK_CONSTRAINTS)

    if unexpected_checks:
        raise MigrationError(
            "Existing database contains unexpected CHECK constraints: "
            f"{sorted(unexpected_checks)}."
        )

    existing_indexes = _get_existing_indexes(connection)

    for index_name, expected_definition in EXPECTED_INDEXES.items():
        actual_definition = existing_indexes.get(index_name)

        if actual_definition is None:
            raise MigrationError(
                f"Existing database is missing required index "
                f"'{index_name}'."
            )

        if actual_definition != expected_definition:
            raise MigrationError(
                f"Existing index '{index_name}' has an incorrect "
                f"definition. Expected {expected_definition}; "
                f"found {actual_definition}."
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
            # Validate against v0001 only. The subsequent migration loop
            # will then upgrade the legacy database to the latest schema.
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
