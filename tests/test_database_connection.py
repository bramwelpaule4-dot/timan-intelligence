
"""Tests for TimanStat database connection management."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from timan_intelligence.database import connection as database_module


@pytest.fixture
def sqlite_database(tmp_path, monkeypatch):
    """Configure an isolated SQLite database for each test."""

    database_file = tmp_path / "test_timanstat.db"

    monkeypatch.setenv(
        "DATABASE_URL",
        f"sqlite:///{database_file.as_posix()}",
    )

    return database_file


def test_sqlite_connection_creates_database_file(sqlite_database):
    """A SQLite connection should create the database file."""

    with database_module.database_connection() as connection:
        result = connection.execute("SELECT 1").fetchone()

    assert result[0] == 1
    assert sqlite_database.exists()


def test_sqlite_connection_enables_foreign_keys(sqlite_database):
    """SQLite foreign-key enforcement should be enabled."""

    with database_module.database_connection() as connection:
        result = connection.execute(
            "PRAGMA foreign_keys"
        ).fetchone()

    assert result[0] == 1


def test_sqlite_connection_uses_write_ahead_logging(sqlite_database):
    """File-based SQLite connections should use WAL journal mode."""

    with database_module.database_connection() as connection:
        result = connection.execute(
            "PRAGMA journal_mode"
        ).fetchone()

    assert result[0].lower() == "wal"


def test_database_connection_commits_successful_transaction(
    sqlite_database,
):
    """Changes should persist after a successful transaction."""

    with database_module.database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE transaction_test (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        connection.execute(
            "INSERT INTO transaction_test (value) VALUES (?)",
            ("committed",),
        )

    with database_module.database_connection() as connection:
        result = connection.execute(
            "SELECT value FROM transaction_test WHERE id = 1"
        ).fetchone()

    assert result["value"] == "committed"


def test_database_connection_rolls_back_failed_transaction(
    sqlite_database,
):
    """Changes should be rolled back when a transaction fails."""

    with database_module.database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE transaction_test (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

    with pytest.raises(RuntimeError, match="Simulated failure"):
        with database_module.database_connection() as connection:
            connection.execute(
                "INSERT INTO transaction_test (value) VALUES (?)",
                ("should_not_persist",),
            )

            raise RuntimeError("Simulated failure")

    with database_module.database_connection() as connection:
        result = connection.execute(
            "SELECT COUNT(*) AS total FROM transaction_test"
        ).fetchone()

    assert result["total"] == 0


def test_database_connection_rolls_back_all_writes_after_constraint_failure(
    sqlite_database,
):
    """A constraint violation should roll back all writes in a transaction."""

    with database_module.database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE transaction_atomicity_test (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE
            )
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        with database_module.database_connection() as connection:
            connection.execute(
                """
                INSERT INTO transaction_atomicity_test (
                    username,
                    email
                )
                VALUES (?, ?)
                """,
                (
                    "rollback_user",
                    "rollback_user@example.com",
                ),
            )

            connection.execute(
                """
                INSERT INTO transaction_atomicity_test (
                    username,
                    email
                )
                VALUES (?, ?)
                """,
                (
                    "rollback_user",
                    "duplicate@example.com",
                ),
            )

    with database_module.database_connection() as connection:
        result = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM transaction_atomicity_test
            """
        ).fetchone()

    assert result["total"] == 0


def test_sqlite_connection_remains_usable_after_failed_transaction(
    sqlite_database,
):
    """A fresh connection should remain usable after a rollback."""

    with database_module.database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE connection_recovery_test (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

    with pytest.raises(RuntimeError, match="Simulated failure"):
        with database_module.database_connection() as connection:
            connection.execute(
                """
                INSERT INTO connection_recovery_test (value)
                VALUES (?)
                """,
                ("temporary",),
            )

            raise RuntimeError("Simulated failure")

    with database_module.database_connection() as connection:
        connection.execute(
            """
            INSERT INTO connection_recovery_test (value)
            VALUES (?)
            """,
            ("recovered",),
        )

        result = connection.execute(
            """
            SELECT value
            FROM connection_recovery_test
            """
        ).fetchone()

    assert result["value"] == "recovered"


def test_database_connection_enforces_foreign_key_constraints(
    sqlite_database,
):
    """Invalid foreign-key references should be rejected."""

    with database_module.database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE parent_records (
                id INTEGER PRIMARY KEY
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE child_records (
                id INTEGER PRIMARY KEY,
                parent_id INTEGER NOT NULL,
                FOREIGN KEY (parent_id) REFERENCES parent_records(id)
            )
            """
        )

    with pytest.raises(sqlite3.IntegrityError):
        with database_module.database_connection() as connection:
            connection.execute(
                "INSERT INTO child_records (parent_id) VALUES (?)",
                (999,),
            )


def test_database_connection_closes_connection_after_context(
    sqlite_database,
    monkeypatch,
):
    """The connection should be closed after leaving its context."""

    original_connect = sqlite3.connect
    created_connections = []

    def tracked_connect(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        created_connections.append(connection)
        return connection

    monkeypatch.setattr(
        database_module.sqlite3,
        "connect",
        tracked_connect,
    )

    with database_module.database_connection() as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1

    assert len(created_connections) == 1

    with pytest.raises(sqlite3.ProgrammingError):
        created_connections[0].execute("SELECT 1")


def test_database_type_recognises_sqlite(sqlite_database):
    """SQLite database URLs should be recognised."""

    assert database_module.get_database_type() == "sqlite"


def test_database_type_rejects_unsupported_database(monkeypatch):
    """Unsupported database URLs should raise a clear error."""

    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql://localhost/timanstat",
    )

    with pytest.raises(ValueError):
        database_module.get_database_type()


def test_sqlite_handles_concurrent_writes_without_losing_records(
    sqlite_database,
):
    """Concurrent writers should persist every submitted record."""

    worker_count = 4
    records_per_worker = 5

    with database_module.database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE concurrent_writes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER NOT NULL,
                record_value TEXT NOT NULL UNIQUE
            )
            """
        )

    def write_records(worker_id):
        """Insert several records using an independent connection."""

        records = [
            (worker_id, f"worker_{worker_id}_record_{record_number}")
            for record_number in range(records_per_worker)
        ]

        with database_module.database_connection() as connection:
            connection.executemany(
                """
                INSERT INTO concurrent_writes (
                    worker_id,
                    record_value
                )
                VALUES (?, ?)
                """,
                records,
            )

        return len(records)

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        completed_writes = list(
            executor.map(
                write_records,
                range(worker_count),
            )
        )

    with database_module.database_connection() as connection:
        total = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM concurrent_writes
            """
        ).fetchone()["total"]

        distinct_values = connection.execute(
            """
            SELECT COUNT(DISTINCT record_value) AS total
            FROM concurrent_writes
            """
        ).fetchone()["total"]

        worker_totals = connection.execute(
            """
            SELECT worker_id, COUNT(*) AS total
            FROM concurrent_writes
            GROUP BY worker_id
            ORDER BY worker_id
            """
        ).fetchall()

    expected_total = worker_count * records_per_worker

    assert completed_writes == [records_per_worker] * worker_count
    assert total == expected_total
    assert distinct_values == expected_total
    assert len(worker_totals) == worker_count
    assert all(
        row["total"] == records_per_worker
        for row in worker_totals
    )


def test_sqlite_supports_concurrent_readers(sqlite_database):
    """Independent connections should read consistent shared data."""

    expected_values = [f"record_{number}" for number in range(20)]

    with database_module.database_connection() as connection:
        connection.execute(
            """
            CREATE TABLE concurrent_reads (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )

        connection.executemany(
            """
            INSERT INTO concurrent_reads (value)
            VALUES (?)
            """,
            [(value,) for value in expected_values],
        )

    def read_records(_reader_id):
        """Read the complete dataset through an independent connection."""

        with database_module.database_connection() as connection:
            rows = connection.execute(
                """
                SELECT value
                FROM concurrent_reads
                ORDER BY id
                """
            ).fetchall()

        return [row["value"] for row in rows]

    reader_count = 5

    with ThreadPoolExecutor(max_workers=reader_count) as executor:
        reader_results = list(
            executor.map(read_records, range(reader_count))
        )

    assert len(reader_results) == reader_count
    assert all(
        result == expected_values
        for result in reader_results
    )
