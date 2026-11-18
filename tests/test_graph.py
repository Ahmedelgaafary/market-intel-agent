from unittest.mock import Mock

import pytest

from market_intel.graph import build_graph
from market_intel.tools.db import get_run
from market_intel.tools.news_api import NewsAPIError


def make_initial_state(competitors):
    return {
        "run_id": "test-run-001",
        "competitors": competitors,
        "articles": [],
        "extracted_facts": [],
        "new_facts": [],
        "articles_fetched": 0,
        "facts_extracted": 0,
        "duplicates_found": 0,
        "saved_fact_ids": [],
        "errors": [],
        "status": "running",
        "report_required": False,
        "summary": None,
    }


def test_graph_completes_when_no_articles_are_found(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    news_client = Mock()
    news_client.fetch_articles.return_value = []

    model = Mock()

    graph = build_graph(
        news_client=news_client,
        model=model,
        db_path=db_path,
    )

    result = graph.invoke(make_initial_state(["Microsoft"]))

    assert result["articles"] == []
    assert result["new_facts"] == []
    assert result["report_required"] is False
    assert result["status"] == "no_updates"
    assert result["errors"] == []

    news_client.fetch_articles.assert_called_once()

    # Verify the completed run was persisted.
    saved_run = get_run("test-run-001", db_path)

    assert saved_run is not None
    assert saved_run.status == "no_updates"
    assert saved_run.completed_at is not None
    assert saved_run.started_at is not None
    assert saved_run.articles_fetched == 0
    assert saved_run.facts_extracted == 0
    assert saved_run.new_facts == 0
    assert saved_run.errors == []


def test_graph_continues_after_news_fetch_failure(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    news_client = Mock()
    news_client.fetch_articles.side_effect = NewsAPIError("Simulated provider failure")

    model = Mock()

    graph = build_graph(
        news_client=news_client,
        model=model,
        db_path=db_path,
    )

    result = graph.invoke(make_initial_state(["Microsoft"]))

    assert result["articles"] == []
    assert result["report_required"] is False
    assert result["status"] == "completed_with_errors"
    assert len(result["errors"]) == 1
    assert "Microsoft" in result["errors"][0]

    news_client.fetch_articles.assert_called_once()

    # Verify the partial-failure status was persisted.
    saved_run = get_run("test-run-001", db_path)

    assert saved_run is not None
    assert saved_run.status == "completed_with_errors"
    assert saved_run.completed_at is not None
    assert saved_run.started_at is not None
    assert len(saved_run.errors) == 1
    assert "Microsoft" in saved_run.errors[0]


def test_graph_records_unexpected_failure(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    news_client = Mock()
    news_client.fetch_articles.side_effect = RuntimeError("Unexpected internal failure")

    model = Mock()

    graph = build_graph(
        news_client=news_client,
        model=model,
        db_path=db_path,
    )

    # The graph should record the failure and then propagate it.
    with pytest.raises(RuntimeError, match="Unexpected internal failure"):
        graph.invoke(make_initial_state(["Microsoft"]))

    saved_run = get_run("test-run-001", db_path)

    assert saved_run is not None
    assert saved_run.status == "failed"
    assert saved_run.completed_at is not None
    assert saved_run.started_at is not None
    assert len(saved_run.errors) == 1
    assert "Unexpected internal failure" in saved_run.errors[0]
