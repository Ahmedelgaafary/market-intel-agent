from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from market_intel.graph import build_graph
from market_intel.schemas import (
    Article,
    ExtractedFact,
    FactExtraction,
)
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


def make_article():
    return Article(
        competitor="Microsoft",
        title="Microsoft announces an AI investment",
        source_url="https://example.com/microsoft",
        published_at=datetime(2026, 11, 15, tzinfo=UTC),
        description="A new AI infrastructure investment.",
    )


def make_reporting_model():
    model = Mock()

    structured_model = Mock()
    structured_model.invoke.return_value = FactExtraction(
        facts=[
            ExtractedFact(
                fact="Microsoft announced a major AI infrastructure investment.",
                category="strategy",
                event_date=date(2026, 11, 15),
            )
        ]
    )

    model.with_structured_output.return_value = structured_model

    model.invoke.return_value = SimpleNamespace(
        content=("Microsoft announced a major AI infrastructure investment on November 15, 2026.")
    )

    return model


def test_graph_generates_and_delivers_executive_report(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    news_client = Mock()
    news_client.fetch_articles.return_value = [make_article()]

    model = make_reporting_model()
    slack_client = Mock()

    graph = build_graph(
        news_client=news_client,
        model=model,
        db_path=db_path,
        slack_client=slack_client,
        report_dir=tmp_path / "reports",
    )

    result = graph.invoke(make_initial_state(["Microsoft"]))

    assert result["status"] == "completed"
    assert result["report_required"] is True
    assert result["summary"] is not None
    assert result["delivery_status"] == "slack"
    assert result["report_path"] is None
    assert len(result["new_facts"]) == 1

    slack_client.send_message.assert_called_once()

    saved_run = get_run("test-run-001", db_path)

    assert saved_run is not None
    assert saved_run.status == "completed"
    assert saved_run.new_facts == 1
    assert saved_run.completed_at is not None


def test_graph_falls_back_to_local_report_when_slack_fails(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    news_client = Mock()
    news_client.fetch_articles.return_value = [make_article()]

    model = make_reporting_model()

    slack_client = Mock()
    slack_client.send_message.side_effect = RuntimeError("Slack is unavailable")

    graph = build_graph(
        news_client=news_client,
        model=model,
        db_path=db_path,
        slack_client=slack_client,
        report_dir=tmp_path / "reports",
    )

    result = graph.invoke(make_initial_state(["Microsoft"]))

    assert result["status"] == "completed_with_errors"
    assert result["delivery_status"] == "local_fallback"
    assert result["report_path"] is not None
    assert "Slack is unavailable" in result["errors"][-1]

    from pathlib import Path

    report_path = Path(result["report_path"])

    assert report_path.exists()
    assert "Microsoft" in report_path.read_text(encoding="utf-8")

    saved_run = get_run("test-run-001", db_path)

    assert saved_run is not None
    assert saved_run.status == "completed_with_errors"
    assert saved_run.new_facts == 1
    assert saved_run.completed_at is not None
