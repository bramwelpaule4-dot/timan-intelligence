"""Database connection management for TimanStat."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import unquote, urlparse

import streamlit as st


SUPPORTED_POSTGRESQL_SCHEMES = {
    "postgresql",
    "postgres",
}


def get_database_url() -> str:
    """Read the database URL from environment variables or Streamlit Secrets."""

    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url:
        return database_url

    try:
        secrets = st.secrets
        database_settings = secrets.get("database", {})
        database_url = str(database_settings.get("url", "")).strip()
    except Exception:
        database_url = ""

    return database_url


def get_database_type() -> str:
    """Identify the configured database backend."""

    url = get_database_url()

    if not url:
        return "sqlite"

    parsed_url = urlparse(url)

    if parsed_url.scheme in SUPPORTED_POSTGRESQL_SCHEMES:
        return "postgresql"

    if parsed_url.scheme == "sqlite":
        return "sqlite"

    raise ValueError(
        "Unsupported database URL configuration. "
        "Use a SQLite or PostgreSQL connection URL."
    )


def get_sqlite_path() -> Path:
    """Resolve the SQLite database path."""

    url = get_database_url()

    if url:
        parsed_url = urlparse(url)

        if parsed_url.scheme != "sqlite":
            raise ValueError(
                "A SQLite database URL is required to resolve "
                "the SQLite database path."
            )

        if parsed_url.query or parsed_url.fragment:
            raise ValueError(
                "SQLite database URLs must not contain query "
                "parameters or fragments."
            )

        raw_path = unquote(parsed_url.path)

        if not raw_path:
            raise ValueError(
                "The SQLite database URL does not specify a database path."
            )

        if parsed_url.netloc and parsed_url.netloc != "localhost":
            raise ValueError(
                "Remote SQLite database paths are not supported."
            )

        database_path = Path(raw_path)

        return database_path.expanduser().resolve()

    default_path = os.getenv(
        "TIMANSTAT_SQLITE_PATH",
        "data/timanstat.db",
    )

    return Path(default_path).expanduser().resolve()


def _create_sqlite_connection() -> sqlite3.Connection:
    """Create a configured SQLite connection."""

    database_path = get_sqlite_path()

    database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        str(database_path),
        timeout=30,
    )

    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        connection.execute("PRAGMA journal_mode = WAL")

        return connection

    except Exception:
        connection.close()
        raise


def _create_postgresql_connection() -> Any:
    """Create a configured PostgreSQL connection."""

    url = get_database_url()

    if not url:
        raise ValueError(
            "A PostgreSQL database URL is required."
        )

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


def get_connection() -> Any:
    """Create and return a database connection."""

    database_type = get_database_type()

    if database_type == "sqlite":
        return _create_sqlite_connection()

    if database_type == "postgresql":
        return _create_postgresql_connection()

    raise RuntimeError(
        "Unsupported database backend."
    )


@contextmanager
def database_connection() -> Iterator[Any]:
    """Provide a managed connection with automatic commit or rollback."""

    connection = get_connection()

    try:
        yield connection
        connection.commit()

    except BaseException:
        try:
            connection.rollback()
        finally:
            connection.close()

        raise

    else:
        connection.close()
