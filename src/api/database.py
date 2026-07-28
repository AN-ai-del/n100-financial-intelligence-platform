"""SQLite database utilities for the FastAPI service."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_CANDIDATES = [
    PROJECT_ROOT / "db" / "nifty100.db",
    PROJECT_ROOT / "data" / "nifty100.db",
]


def resolve_database_path() -> Path:
    """Return the first existing Nifty 100 SQLite database path."""

    for candidate in DATABASE_CANDIDATES:
        if candidate.exists():
            return candidate

    searched_paths = "\n".join(
        f"- {path}"
        for path in DATABASE_CANDIDATES
    )

    raise FileNotFoundError(
        "The Nifty 100 database could not be found.\n"
        f"Searched:\n{searched_paths}"
    )


DB_PATH = resolve_database_path()


def create_connection() -> sqlite3.Connection:
    """Create a configured SQLite connection."""

    connection = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield one SQLite connection for a FastAPI request."""

    connection = create_connection()

    try:
        yield connection

    finally:
        connection.close()


def get_user_table_names(
    connection: sqlite3.Connection,
) -> list[str]:
    """Return all non-internal SQLite table names."""

    query = """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """

    rows = connection.execute(
        query
    ).fetchall()

    return [
        str(row["name"])
        for row in rows
    ]


def get_database_row_counts() -> dict[str, int]:
    """Return the row count for every user-created database table."""

    with create_connection() as connection:
        table_names = get_user_table_names(
            connection
        )

        row_counts: dict[str, int] = {}

        for table_name in table_names:
            escaped_table_name = (
                table_name.replace(
                    '"',
                    '""',
                )
            )

            query = (
                f'SELECT COUNT(*) AS row_count '
                f'FROM "{escaped_table_name}"'
            )

            row = connection.execute(
                query
            ).fetchone()

            row_counts[table_name] = (
                int(row["row_count"])
                if row is not None
                else 0
            )

    return row_counts