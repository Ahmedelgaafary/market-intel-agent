from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from market_intel.schemas import Article, Fact, RunResult


def test_article_accepts_valid_data():
    article = Article(
        competitor="Acme",
        title="Acme launches a new AI product",
        source_url="https://example.com/news",
        published_at=datetime(2026, 10, 25, tzinfo=UTC),
    )

    assert article.competitor == "Acme"
    assert str(article.source_url) == "https://example.com/news"


def test_article_rejects_invalid_url():
    with pytest.raises(ValidationError):
        Article(
            competitor="Acme",
            title="New product",
            source_url="not-a-url",
        )


def test_fact_accepts_valid_data():
    fact = Fact(
        competitor="Acme",
        fact="Acme announced a new enterprise AI product.",
        category="product_launch",
        date=date(2026, 10, 25),
        source_url="https://example.com/news",
    )

    assert fact.category == "product_launch"
    assert fact.date == date(2026, 10, 25)


def test_fact_rejects_unknown_category():
    with pytest.raises(ValidationError):
        Fact(
            competitor="Acme",
            fact="Acme announced a new enterprise AI product.",
            category="random_category",
            date="2026-10-25",
            source_url="https://example.com/news",
        )


def test_run_result_rejects_negative_counts():
    with pytest.raises(ValidationError):
        RunResult(
            run_id="run-001",
            started_at=datetime.now(UTC),
            articles_fetched=-1,
        )


def test_run_result_defaults():
    result = RunResult(
        run_id="run-001",
        started_at=datetime.now(UTC),
    )

    assert result.status == "running"
    assert result.articles_fetched == 0
    assert result.facts_extracted == 0
    assert result.new_facts == 0
    assert result.errors == []
    assert result.completed_at is None