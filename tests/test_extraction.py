
from datetime import UTC, date, datetime

import pytest

from market_intel.schemas import Article, FactExtraction
from market_intel.tools.extraction import (
    FactExtractionError,
    extract_facts,
)


class FakeStructuredModel:
    """Simulate a LangChain model with structured output."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.schema = None
        self.prompts = []

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        self.calls += 1
        self.prompts.append(messages)

        response = self.responses.pop(0)

        if isinstance(response, Exception):
            raise response

        return response


@pytest.fixture
def article():
    return Article(
        competitor="Microsoft",
        title="Microsoft announces a new enterprise AI platform",
        source_url="https://example.com/microsoft-ai",
        published_at=datetime(
            2026, 11, 14, 10, 30, tzinfo=UTC
        ),
        description="Microsoft announced a new AI platform.",
        content="The platform will serve enterprise customers.",
    )


@pytest.fixture
def valid_response():
    return {
        "facts": [
            {
                "fact": (
                    "Microsoft announced a new enterprise AI platform."
                ),
                "category": "product_launch",
                "event_date": "2026-11-14",
            }
        ]
    }


def test_extract_facts_returns_valid_fact(article, valid_response):
    model = FakeStructuredModel([valid_response])

    result = extract_facts(article, model)

    assert len(result.facts) == 1
    assert result.facts[0].competitor == "Microsoft"
    assert result.facts[0].category == "product_launch"
    assert result.facts[0].date == date(2026, 11, 14)
    assert str(result.facts[0].source_url) == str(article.source_url)
    assert result.attempts == 1
    assert result.warnings == []


def test_extract_facts_uses_article_publication_date(
    article,
):
    response = {
        "facts": [
            {
                "fact": "Microsoft announced an enterprise AI partnership.",
                "category": "partnership",
                "event_date": None,
            }
        ]
    }

    model = FakeStructuredModel([response])

    result = extract_facts(article, model)

    assert len(result.facts) == 1
    assert result.facts[0].date == date(2026, 11, 14)


def test_extract_facts_skips_fact_without_any_date():
    undated_article = Article(
        competitor="Microsoft",
        title="Microsoft announces a new product",
        source_url="https://example.com/product",
    )

    response = {
        "facts": [
            {
                "fact": "Microsoft announced a new enterprise AI product.",
                "category": "product_launch",
                "event_date": None,
            }
        ]
    }

    model = FakeStructuredModel([response])

    result = extract_facts(undated_article, model)

    assert result.facts == []
    assert len(result.warnings) == 1


def test_extract_facts_returns_empty_result_when_no_developments(
    article,
):
    model = FakeStructuredModel([{"facts": []}])

    result = extract_facts(article, model)

    assert result.facts == []
    assert result.warnings == []
    assert result.attempts == 1


def test_extract_facts_retries_after_invalid_response(
    article,
    valid_response,
):
    invalid_response = {
        "facts": [
            {
                "fact": "Short",
                "category": "product_launch",
            }
        ]
    }

    model = FakeStructuredModel(
        [invalid_response, valid_response]
    )

    result = extract_facts(article, model)

    assert len(result.facts) == 1
    assert result.attempts == 2
    assert model.calls == 2


def test_extract_facts_fails_after_second_invalid_response(article):
    invalid_response = {
        "facts": [
            {
                "fact": "Short",
                "category": "invalid_category",
            }
        ]
    }

    model = FakeStructuredModel(
        [invalid_response, invalid_response]
    )

    with pytest.raises(FactExtractionError, match="2 attempts"):
        extract_facts(article, model)

    assert model.calls == 2


def test_extract_facts_does_not_retry_provider_errors(article):
    model = FakeStructuredModel(
        [RuntimeError("Provider connection failed")]
    )

    with pytest.raises(RuntimeError, match="Provider connection failed"):
        extract_facts(article, model)

    assert model.calls == 1


def test_extraction_uses_expected_pydantic_schema(
    article,
    valid_response,
):
    model = FakeStructuredModel([valid_response])

    extract_facts(article, model)

    assert model.schema is FactExtraction


def test_extraction_prompt_contains_article_information(
    article,
    valid_response,
):
    model = FakeStructuredModel([valid_response])

    extract_facts(article, model)

    prompt_text = str(model.prompts[0])

    assert article.title in prompt_text
    assert article.competitor in prompt_text
    assert str(article.source_url) in prompt_text


def test_extraction_does_not_trust_model_competitor_or_source(
    article,
):
    model = FakeStructuredModel(
        [
            {
                "facts": [
                    {
                        "fact": (
                            "Microsoft announced a new enterprise AI platform."
                        ),
                        "category": "product_launch",
                        "event_date": "2026-11-14",
                    }
                ]
            }
        ]
    )

    result = extract_facts(article, model)

    assert result.facts[0].competitor == article.competitor
    assert result.facts[0].source_url == article.source_url
