"""NewsAPI integration for retrieving and normalizing competitor articles."""

from datetime import UTC, datetime, timedelta
from typing import Any, Self

import httpx

from market_intel.schemas import Article

BASE_URL = "https://newsapi.org/v2/everything"
DEFAULT_TIMEOUT = 15.0
MAX_PAGE_SIZE = 100


class NewsAPIError(Exception):
    """Raised when NewsAPI returns an error or an invalid response."""


class NewsAPIConfigurationError(NewsAPIError):
    """Raised when the NewsAPI client is configured incorrectly."""


class NewsAPIClient:
    """Small HTTP client for the NewsAPI Everything endpoint."""

    def __init__(
        self,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise NewsAPIConfigurationError("NewsAPI API key is required.")

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self._api_key = api_key.strip()
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(
            timeout=timeout,
            headers={"X-Api-Key": self._api_key},
        )

        if http_client is not None:
            self._client.headers.update({"X-Api-Key": self._api_key})

    def close(self) -> None:
        """Close the HTTP client if this instance created it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch_articles(
        self,
        competitor: str,
        lookback_days: int = 7,
        max_articles: int = 10,
        language: str = "en",
        now: datetime | None = None,
    ) -> list[Article]:
        """Fetch recent articles mentioning one competitor."""
        if not competitor or not competitor.strip():
            raise ValueError("competitor must not be empty")

        if lookback_days < 1:
            raise ValueError("lookback_days must be at least 1")

        if not 1 <= max_articles <= MAX_PAGE_SIZE:
            raise ValueError(f"max_articles must be between 1 and {MAX_PAGE_SIZE}")

        if len(language) != 2 or not language.isalpha():
            raise ValueError("language must be a two-letter language code")

        current_time = now or datetime.now(UTC)

        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        current_time = current_time.astimezone(UTC)
        start_time = current_time - timedelta(days=lookback_days)

        params = {
            "q": competitor.strip(),
            "from": start_time.isoformat(timespec="seconds"),
            "to": current_time.isoformat(timespec="seconds"),
            "sortBy": "publishedAt",
            "language": language.lower(),
            "pageSize": max_articles,
            "page": 1,
        }

        try:
            response = self._client.get(BASE_URL, params=params)
        except httpx.TimeoutException as exc:
            raise NewsAPIError("NewsAPI request timed out.") from exc
        except httpx.RequestError as exc:
            raise NewsAPIError(f"Could not connect to NewsAPI: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise NewsAPIError("NewsAPI returned an invalid JSON response.") from exc

        if not isinstance(payload, dict):
            raise NewsAPIError("NewsAPI returned an unexpected response.")

        if response.is_error:
            code = payload.get("code", "http_error")
            message = payload.get("message", response.reason_phrase)
            raise NewsAPIError(f"NewsAPI HTTP {response.status_code} ({code}): {message}")

        if payload.get("status") != "ok":
            code = payload.get("code", "unknown_error")
            message = payload.get("message", "Unknown provider error")
            raise NewsAPIError(f"NewsAPI error ({code}): {message}")

        raw_articles = payload.get("articles")

        if not isinstance(raw_articles, list):
            raise NewsAPIError("NewsAPI response does not contain a valid articles list.")

        articles: list[Article] = []

        for raw_article in raw_articles:
            article = self._normalize_article(competitor, raw_article)

            if article is not None:
                articles.append(article)

        return articles

    @staticmethod
    def _normalize_article(
        competitor: str,
        raw_article: Any,
    ) -> Article | None:
        """Convert one provider article into our Article schema."""
        if not isinstance(raw_article, dict):
            return None

        title = raw_article.get("title")
        source_url = raw_article.get("url")

        if not isinstance(title, str) or not title.strip():
            return None

        if title.strip().lower() == "[removed]":
            return None

        if not isinstance(source_url, str) or not source_url.strip():
            return None

        published_at = NewsAPIClient._parse_published_at(raw_article.get("publishedAt"))

        description = raw_article.get("description")
        content = raw_article.get("content")

        try:
            return Article.from_provider(
                competitor=competitor,
                title=title,
                source_url=source_url,
                published_at=published_at,
                description=(description if isinstance(description, str) else None),
                content=content if isinstance(content, str) else None,
            )
        except ValueError:
            # Skip malformed provider records; preserve other valid articles.
            return None

    @staticmethod
    def _parse_published_at(value: Any) -> datetime | None:
        """Parse the provider's ISO 8601 publication timestamp."""
        if not isinstance(value, str) or not value.strip():
            return None

        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError:
            return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.astimezone(UTC)


def fetch_articles(
    competitor: str,
    api_key: str,
    lookback_days: int = 7,
    max_articles: int = 10,
    language: str = "en",
) -> list[Article]:
    """Convenience function for a single competitor search."""
    with NewsAPIClient(api_key=api_key) as client:
        return client.fetch_articles(
            competitor=competitor,
            lookback_days=lookback_days,
            max_articles=max_articles,
            language=language,
        )
