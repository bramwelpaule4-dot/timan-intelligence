
"""Database connection management for TimanStat."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Any

import streamlit as st


def get_database_url() -> str:
    """Read the database URL from environment variables or Streamlit Secrets."""

    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url:
        return database_url

    try:
        database_url = str(
            st.secrets.get("database", {}).get("url", "")
        ).strip()
    except Exception:
        database_url = ""

    return database_url


def get_database_type() -> str:
    """Identify the configured database backend."""

    url = get_database_url()

    if url.startswith(("postgresql://", "postgres://")):
        return "postgresql"

    if url.startswith("sqlite:///"):
        return "sqlite"

    if not url:
        return "sqlite"

    raise ValueError("Unsupported database URL configuration.")


def get_sqlite_path() -> Path:
    """Resolve the SQLite database path."""

    url = get_database_url()

    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
        return Path(path).expanduser().resolve()

    default_path = os.getenv(
        "TIMANSTAT_SQLITE_PATH",
        "data/timanstat.db",
    )

    return Path(default_path).expanduser().resolve()


def get_connection() -> Any:
    """Create and return a database connection."""

    database_type = get_database_type()
    url = get_database_url()

    if database_type == "sqlite":
        database_path = get_sqlite_path()
        database_path.parent.mkdir(parents=True, exist_ok=True)

        connection = sqlite3.connect(
            str(database_path),
            timeout=30,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")

        return connection

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL is configured, but psycopg is not installed. "
            "Install the PostgreSQL dependency."
        ) from exc

    return psycopg.connect(
        url,
        row_factory=dict_row,
        connect_timeout=10,
    )


@contextmanager
def database_connection() -> Iterator[Any]:
    """Provide a managed connection with automatic commit or rollback."""

    connection = get_connection()

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
