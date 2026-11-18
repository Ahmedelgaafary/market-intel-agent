from datetime import UTC, date, datetime

import pytest

from market_intel.schemas import Fact, RunResult
from market_intel.tools.db import (
    count_facts,
    get_run,
    initialize_database,
    list_facts,
    list_runs,
    save_fact,
    save_run,
)


@pytest.fixture
def db_path(tmp_path):
    """Provide an initialized temporary SQLite database."""
    path = tmp_path / "test_market_intel.db"
    initialize_database(path)
    return path


@pytest.fixture
def sample_fact():
    return Fact(
        competitor="Microsoft",
        fact="Microsoft announced a new AI product for enterprise customers.",
        category="product_launch",
        date=date(2026, 11, 10),
        source_url="https://example.com/microsoft-ai",
    )


@pytest.fixture
def sample_run():
    return RunResult(
        run_id="test-run-001",
        started_at=datetime(2026, 11, 15, 8, 0, tzinfo=UTC),
        status="completed",
        articles_fetched=10,
        facts_extracted=5,
        new_facts=2,
        errors=[],
    )


def test_initialize_database_creates_tables(db_path):
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

    assert "facts" in tables
    assert "runs" in tables


def test_save_and_list_fact(db_path, sample_fact):
    fact_id = save_fact(sample_fact, db_path)

    assert fact_id > 0
    assert count_facts(db_path) == 1

    stored_facts = list_facts(db_path)

    assert len(stored_facts) == 1
    assert stored_facts[0] == sample_fact


def test_list_facts_filters_by_competitor(db_path):
    microsoft_fact = Fact(
        competitor="Microsoft",
        fact="Microsoft announced a new enterprise AI service.",
        category="product_launch",
        date=date(2026, 11, 10),
        source_url="https://example.com/microsoft",
    )
    google_fact = Fact(
        competitor="Google",
        fact="Google announced a new cloud computing partnership.",
        category="partnership",
        date=date(2026, 11, 11),
        source_url="https://example.com/google",
    )

    save_fact(microsoft_fact, db_path)
    save_fact(google_fact, db_path)

    results = list_facts(db_path, competitor="Google")

    assert len(results) == 1
    assert results[0].competitor == "Google"


def test_list_facts_respects_limit(db_path):
    for index in range(3):
        fact = Fact(
            competitor="Microsoft",
            fact=f"Microsoft announced development number {index}.",
            category="strategy",
            date=date(2026, 11, 10 + index),
            source_url=f"https://example.com/fact-{index}",
        )
        save_fact(fact, db_path)

    results = list_facts(db_path, limit=2)

    assert len(results) == 2


def test_list_facts_rejects_invalid_limit(db_path):
    with pytest.raises(ValueError, match="limit"):
        list_facts(db_path, limit=0)


def test_save_and_get_run(db_path, sample_run):
    save_run(sample_run, db_path)

    stored_run = get_run(sample_run.run_id, db_path)

    assert stored_run == sample_run


def test_get_run_returns_none_for_unknown_id(db_path):
    assert get_run("missing-run", db_path) is None


def test_save_run_updates_existing_run(db_path, sample_run):
    save_run(sample_run, db_path)

    updated_run = sample_run.model_copy(
        update={
            "status": "completed_with_errors",
            "new_facts": 3,
            "errors": ["One article could not be processed."],
        }
    )
    save_run(updated_run, db_path)

    stored_run = get_run(sample_run.run_id, db_path)

    assert stored_run == updated_run
    assert len(list_runs(db_path)) == 1


def test_list_runs_returns_recent_runs(db_path):
    first_run = RunResult(
        run_id="run-001",
        started_at=datetime(2026, 11, 13, tzinfo=UTC),
    )
    second_run = RunResult(
        run_id="run-002",
        started_at=datetime(2026, 11, 14, tzinfo=UTC),
    )

    save_run(first_run, db_path)
    save_run(second_run, db_path)

    results = list_runs(db_path)

    assert [run.run_id for run in results] == ["run-002", "run-001"]


def test_list_runs_rejects_invalid_limit(db_path):
    with pytest.raises(ValueError, match="limit"):
        list_runs(db_path, limit=0)
