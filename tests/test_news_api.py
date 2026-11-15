
from datetime import UTC, datetime

import httpx
import pytest

from market_intel.schemas import Article
from market_intel.tools.news_api import (
    BASE_URL,
    NewsAPIClient,
    NewsAPIConfigurationError,
    NewsAPIError,
)


@pytest.fixture
def now():
    return datetime(2026, 11, 15, 9, 0, tzinfo=UTC)


@pytest.fixture
def valid_article():
    return {
        "title": "Microsoft announces a new AI platform",
        "url": "https://example.com/microsoft-ai",
        "publishedAt": "2026-11-14T10:30:00Z",
        "description": "A new enterprise AI platform was announced.",
        "content": "Microsoft announced its new platform.",
    }


def make_client(handler, api_key="test-api-key"):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport)

    return NewsAPIClient(
        api_key=api_key,
        http_client=http_client,
    ), http_client


def test_client_requires_api_key():
    with pytest.raises(NewsAPIConfigurationError):
        NewsAPIClient(api_key=" ")


def test_client_rejects_invalid_timeout():
    with pytest.raises(ValueError, match="timeout"):
        NewsAPIClient(api_key="test-key", timeout=0)


def test_fetch_articles_normalizes_response(valid_article, now):
    def handler(request):
        assert request.url.path == "/v2/everything"
        assert request.headers["X-Api-Key"] == "test-api-key"

        return httpx.Response(
            200,
            json={
                "status": "ok",
                "totalResults": 1,
                "articles": [valid_article],
            },
        )

    client, http_client = make_client(handler)

    try:
        articles = client.fetch_articles(
            competitor="Microsoft",
            now=now,
        )
    finally:
        http_client.close()

    assert len(articles) == 1
    assert isinstance(articles[0], Article)
    assert articles[0].competitor == "Microsoft"
    assert articles[0].title == valid_article["title"]
    assert str(articles[0].source_url) == valid_article["url"]
    assert articles[0].published_at == datetime(
        2026, 11, 14, 10, 30, tzinfo=UTC
    )


def test_fetch_articles_sends_search_parameters(now):
    def handler(request):
        params = dict(request.url.params)

        assert params["q"] == "Microsoft"
        assert params["language"] == "en"
        assert params["sortBy"] == "publishedAt"
        assert params["pageSize"] == "10"
        assert params["page"] == "1"
        assert params["from"] == "2026-11-08T09:00:00+00:00"
        assert params["to"] == "2026-11-15T09:00:00+00:00"

        return httpx.Response(
            200,
            json={"status": "ok", "articles": []},
        )

    client, http_client = make_client(handler)

    try:
        articles = client.fetch_articles(
            competitor="Microsoft",
            lookback_days=7,
            max_articles=10,
            now=now,
        )
    finally:
        http_client.close()

    assert articles == []


def test_fetch_articles_skips_removed_and_invalid_articles(
    valid_article,
    now,
):
    removed = {
        "title": "[Removed]",
        "url": "https://example.com/removed",
    }
    invalid = {
        "title": "Article without a valid URL",
        "url": "not-a-url",
    }
    missing_title = {
        "url": "https://example.com/missing-title",
    }

    def handler(request):
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "articles": [
                    valid_article,
                    removed,
                    invalid,
                    missing_title,
                    None,
                ],
            },
        )

    client, http_client = make_client(handler)

    try:
        articles = client.fetch_articles("Microsoft", now=now)
    finally:
        http_client.close()

    assert len(articles) == 1
    assert articles[0].title == valid_article["title"]


def test_fetch_articles_handles_missing_optional_fields(now):
    article_data = {
        "title": "A company announcement",
        "url": "https://example.com/announcement",
    }

    def handler(request):
        return httpx.Response(
            200,
            json={
                "status": "ok",
                "articles": [article_data],
            },
        )

    client, http_client = make_client(handler)

    try:
        articles = client.fetch_articles("Microsoft", now=now)
    finally:
        http_client.close()

    assert len(articles) == 1
    assert articles[0].published_at is None
    assert articles[0].description is None
    assert articles[0].content is None


@pytest.mark.parametrize(
    "competitor, lookback_days, max_articles, language",
    [
        ("", 7, 10, "en"),
        ("Microsoft", 0, 10, "en"),
        ("Microsoft", 7, 0, "en"),
        ("Microsoft", 7, 101, "en"),
        ("Microsoft", 7, 10, "english"),
    ],
)
def test_fetch_articles_rejects_invalid_parameters(
    competitor,
    lookback_days,
    max_articles,
    language,
):
    def handler(request):
        pytest.fail("The HTTP request should not be made.")

    client, http_client = make_client(handler)

    try:
        with pytest.raises(ValueError):
            client.fetch_articles(
                competitor=competitor,
                lookback_days=lookback_days,
                max_articles=max_articles,
                language=language,
            )
    finally:
        http_client.close()


def test_fetch_articles_requires_timezone_aware_now():
    def handler(request):
        pytest.fail("The HTTP request should not be made.")

    client, http_client = make_client(handler)

    try:
        with pytest.raises(ValueError, match="timezone-aware"):
            client.fetch_articles(
                "Microsoft",
                now=datetime.fromisoformat("2026-11-15T09:00:00"),
            )
    finally:
        http_client.close()


@pytest.mark.parametrize(
    "status_code, payload, expected_message",
    [
        (
            401,
            {"code": "apiKeyInvalid", "message": "Invalid API key"},
            "apiKeyInvalid",
        ),
        (
            429,
            {"code": "rateLimited", "message": "Too many requests"},
            "rateLimited",
        ),
        (
            500,
            {"code": "unexpectedError", "message": "Server error"},
            "unexpectedError",
        ),
    ],
)
def test_fetch_articles_handles_http_errors(
    status_code,
    payload,
    expected_message,
):
    def handler(request):
        return httpx.Response(status_code, json=payload)

    client, http_client = make_client(handler)

    try:
        with pytest.raises(NewsAPIError, match=expected_message):
            client.fetch_articles("Microsoft")
    finally:
        http_client.close()


def test_fetch_articles_handles_provider_error():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "status": "error",
                "code": "apiKeyExhausted",
                "message": "API request limit reached",
            },
        )

    client, http_client = make_client(handler)

    try:
        with pytest.raises(NewsAPIError, match="apiKeyExhausted"):
            client.fetch_articles("Microsoft")
    finally:
        http_client.close()


def test_fetch_articles_handles_timeout():
    def handler(request):
        raise httpx.ReadTimeout("Request timed out")

    client, http_client = make_client(handler)

    try:
        with pytest.raises(NewsAPIError, match="timed out"):
            client.fetch_articles("Microsoft")
    finally:
        http_client.close()


def test_fetch_articles_handles_connection_error():
    def handler(request):
        raise httpx.ConnectError("Connection refused")

    client, http_client = make_client(handler)

    try:
        with pytest.raises(NewsAPIError, match="Could not connect"):
            client.fetch_articles("Microsoft")
    finally:
        http_client.close()


def test_fetch_articles_handles_invalid_json():
    def handler(request):
        return httpx.Response(
            200,
            text="This is not JSON",
        )

    client, http_client = make_client(handler)

    try:
        with pytest.raises(NewsAPIError, match="invalid JSON"):
            client.fetch_articles("Microsoft")
    finally:
        http_client.close()


def test_fetch_articles_rejects_invalid_response_shape():
    def handler(request):
        return httpx.Response(200, json={"status": "ok", "articles": None})

    client, http_client = make_client(handler)

    try:
        with pytest.raises(NewsAPIError, match="articles list"):
            client.fetch_articles("Microsoft")
    finally:
        http_client.close()


def test_fetch_articles_uses_expected_endpoint():
    def handler(request):
        assert str(request.url).startswith(BASE_URL)
        return httpx.Response(
            200,
            json={"status": "ok", "articles": []},
        )

    client, http_client = make_client(handler)

    try:
        client.fetch_articles("Microsoft")
    finally:
        http_client.close()
