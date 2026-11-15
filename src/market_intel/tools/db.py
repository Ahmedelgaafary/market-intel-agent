
"""SQLite persistence for market intelligence facts and workflow runs."""

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC
from pathlib import Path

from market_intel.schemas import Fact, RunResult

DatabasePath = str | Path


@contextmanager
def _connection(db_path: DatabasePath) -> Iterator[sqlite3.Connection]:
    """Open a database connection and manage its transaction."""
    path = str(db_path)

    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(db_path: DatabasePath) -> None:
    """Create the database tables and indexes if they do not exist."""
    with _connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                competitor TEXT NOT NULL,
                fact TEXT NOT NULL,
                category TEXT NOT NULL,
                fact_date TEXT NOT NULL,
                source_url TEXT NOT NULL,
                first_seen_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_facts_competitor
                ON facts (competitor);

            CREATE INDEX IF NOT EXISTS idx_facts_date
                ON facts (fact_date);

            CREATE INDEX IF NOT EXISTS idx_facts_competitor_date
                ON facts (competitor, fact_date);

            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'running',
                        'completed',
                        'completed_with_errors',
                        'failed',
                        'no_updates'
                    )
                ),
                articles_fetched INTEGER NOT NULL DEFAULT 0
                    CHECK (articles_fetched >= 0),
                facts_extracted INTEGER NOT NULL DEFAULT 0
                    CHECK (facts_extracted >= 0),
                new_facts INTEGER NOT NULL DEFAULT 0
                    CHECK (new_facts >= 0),
                errors_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE INDEX IF NOT EXISTS idx_runs_started_at
                ON runs (started_at);

            CREATE INDEX IF NOT EXISTS idx_runs_status
                ON runs (status);
            """
        )


def save_fact(fact: Fact, db_path: DatabasePath) -> int:
    """Persist one fact and return its database ID."""
    from datetime import datetime

    first_seen_at = datetime.now(UTC).isoformat()

    with _connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO facts (
                competitor,
                fact,
                category,
                fact_date,
                source_url,
                first_seen_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                fact.competitor,
                fact.fact,
                fact.category,
                fact.date.isoformat(),
                str(fact.source_url),
                first_seen_at,
            ),
        )

        return int(cursor.lastrowid)


def list_facts(
    db_path: DatabasePath,
    competitor: str | None = None,
    limit: int | None = None,
) -> list[Fact]:
    """Retrieve stored facts, optionally filtering by competitor."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    query = """
        SELECT competitor, fact, category, fact_date, source_url
        FROM facts
    """
    parameters: list[str | int] = []

    if competitor is not None:
        query += " WHERE competitor = ?"
        parameters.append(competitor)

    query += " ORDER BY fact_date DESC, id DESC"

    if limit is not None:
        query += " LIMIT ?"
        parameters.append(limit)

    with _connection(db_path) as connection:
        rows = connection.execute(query, parameters).fetchall()

    return [
        Fact(
            competitor=row["competitor"],
            fact=row["fact"],
            category=row["category"],
            date=row["fact_date"],
            source_url=row["source_url"],
        )
        for row in rows
    ]


def save_run(run: RunResult, db_path: DatabasePath) -> None:
    """Insert or update a workflow run."""
    with _connection(db_path) as connection:
        connection.execute(
            """
            INSERT INTO runs (
                run_id,
                started_at,
                completed_at,
                status,
                articles_fetched,
                facts_extracted,
                new_facts,
                errors_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                started_at = excluded.started_at,
                completed_at = excluded.completed_at,
                status = excluded.status,
                articles_fetched = excluded.articles_fetched,
                facts_extracted = excluded.facts_extracted,
                new_facts = excluded.new_facts,
                errors_json = excluded.errors_json
            """,
            (
                run.run_id,
                run.started_at.isoformat(),
                (
                    run.completed_at.isoformat()
                    if run.completed_at is not None
                    else None
                ),
                run.status,
                run.articles_fetched,
                run.facts_extracted,
                run.new_facts,
                json.dumps(run.errors),
            ),
        )


def get_run(run_id: str, db_path: DatabasePath) -> RunResult | None:
    """Retrieve one workflow run by its ID."""
    with _connection(db_path) as connection:
        row = connection.execute(
            "SELECT * FROM runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()

    if row is None:
        return None

    return RunResult(
        run_id=row["run_id"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        status=row["status"],
        articles_fetched=row["articles_fetched"],
        facts_extracted=row["facts_extracted"],
        new_facts=row["new_facts"],
        errors=json.loads(row["errors_json"]),
    )


def list_runs(
    db_path: DatabasePath,
    limit: int = 100,
) -> list[RunResult]:
    """Retrieve recent workflow runs, newest first."""
    if limit < 1:
        raise ValueError("limit must be greater than zero")

    with _connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM runs
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        RunResult(
            run_id=row["run_id"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            status=row["status"],
            articles_fetched=row["articles_fetched"],
            facts_extracted=row["facts_extracted"],
            new_facts=row["new_facts"],
            errors=json.loads(row["errors_json"]),
        )
        for row in rows
    ]


def count_facts(db_path: DatabasePath) -> int:
    """Return the total number of stored facts."""
    with _connection(db_path) as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total FROM facts"
        ).fetchone()

    return int(row["total"])
