"""News fetching node for the market intelligence graph."""

from market_intel.state import AgentState
from market_intel.tools.news_api import NewsAPIClient, NewsAPIError


def fetch_node(
    state: AgentState,
    *,
    news_client: NewsAPIClient,
    lookback_days: int = 7,
    max_articles_per_competitor: int = 10,
    language: str = "en",
) -> dict:
    """Fetch recent articles for each competitor independently."""
    articles = []
    errors = []

    for competitor in state["competitors"]:
        try:
            competitor_articles = news_client.fetch_articles(
                competitor=competitor,
                lookback_days=lookback_days,
                max_articles=max_articles_per_competitor,
                language=language,
            )
            articles.extend(competitor_articles)

        except NewsAPIError as exc:
            errors.append(f"News fetch failed for {competitor}: {exc}")

    return {
        "articles": articles,
        "articles_fetched": len(articles),
        "errors": [*state["errors"], *errors],
    }
