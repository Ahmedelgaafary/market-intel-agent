from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from market_intel.application import create_initial_state, run_once
from market_intel.config import (
    AppConfig,
    MemoryConfig,
    NewsConfig,
    ScheduleConfig,
    SummaryConfig,
)


def make_config(tmp_path):
    return AppConfig(
        competitors=("Microsoft", "Google"),
        news=NewsConfig(
            lookback_days=7,
            max_articles_per_competitor=10,
            language="en",
        ),
        memory=MemoryConfig(similarity_threshold=0.85),
        summary=SummaryConfig(max_words=300),
        schedule=ScheduleConfig(
            day="monday",
            hour=9,
            minute=0,
            timezone="UTC",
        ),
        database_path=tmp_path / "db" / "facts.sqlite",
        report_dir=tmp_path / "reports",
        news_api_key="test-news-key",
        slack_webhook_url=None,
    )


def test_create_initial_state():
    state = create_initial_state(
        "run-123",
        ("Microsoft", "Google"),
    )

    assert state["run_id"] == "run-123"
    assert state["competitors"] == ["Microsoft", "Google"]
    assert state["articles"] == []
    assert state["new_facts"] == []
    assert state["status"] == "running"
    assert state["delivery_status"] == "pending"
    assert isinstance(state["started_at"], datetime)
    assert state["started_at"].tzinfo == UTC


def test_run_once_rejects_missing_news_api_key(tmp_path):
    config = make_config(tmp_path)
    config = AppConfig(
        competitors=config.competitors,
        news=config.news,
        memory=config.memory,
        summary=config.summary,
        schedule=config.schedule,
        database_path=config.database_path,
        report_dir=config.report_dir,
        news_api_key=None,
        slack_webhook_url=None,
    )

    with pytest.raises(ValueError, match="NEWS_API_KEY"):
        run_once(config=config, model=object())


def test_run_once_invokes_graph_and_closes_clients(
    tmp_path,
    monkeypatch,
):
    from market_intel import application

    config = make_config(tmp_path)
    events = []

    class FakeNewsClient:
        def __init__(self, api_key):
            assert api_key == "test-news-key"

        def __enter__(self):
            events.append("news_open")
            return self

        def __exit__(self, *args):
            events.append("news_close")

    class FakeGraph:
        def invoke(self, state):
            events.append("graph_invoke")
            assert state["competitors"] == ["Microsoft", "Google"]
            return {"run_id": state["run_id"], "status": "completed"}

    monkeypatch.setattr(
        application,
        "NewsAPIClient",
        FakeNewsClient,
    )
    monkeypatch.setattr(
        application,
        "build_graph",
        lambda **kwargs: FakeGraph(),
    )

    result = run_once(config=config, model=object())

    assert result["status"] == "completed"
    assert events == ["news_open", "graph_invoke", "news_close"]
    assert config.database_path.parent.is_dir()
    assert config.report_dir.is_dir()


def test_run_once_passes_config_to_graph(
    tmp_path,
    monkeypatch,
):
    from market_intel import application

    config = make_config(tmp_path)
    captured = {}

    class FakeNewsClient:
        def __init__(self, api_key):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeGraph:
        def invoke(self, state):
            return {"run_id": state["run_id"], "status": "completed"}

    def fake_build_graph(**kwargs):
        captured.update(kwargs)
        return FakeGraph()

    monkeypatch.setattr(application, "NewsAPIClient", FakeNewsClient)
    monkeypatch.setattr(application, "build_graph", fake_build_graph)

    model = SimpleNamespace()
    run_once(config=config, model=model)

    assert captured["model"] is model
    assert captured["lookback_days"] == 7
    assert captured["max_articles_per_competitor"] == 10
    assert captured["language"] == "en"
    assert captured["similarity_threshold"] == 0.85
    assert captured["max_summary_words"] == 300
