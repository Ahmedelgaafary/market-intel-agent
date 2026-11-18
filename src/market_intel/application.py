from contextlib import ExitStack
from datetime import UTC, datetime
from uuid import uuid4

from market_intel.config import AppConfig
from market_intel.graph import build_graph
from market_intel.tools.news_api import NewsAPIClient
from market_intel.tools.slack import SlackWebhookClient


def create_initial_state(
    run_id: str,
    competitors: tuple[str, ...],
) -> dict:
    """Create the initial state for one workflow execution."""

    return {
        "run_id": run_id,
        "started_at": datetime.now(UTC),
        "competitors": list(competitors),
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
        "delivery_status": "pending",
        "report_path": None,
    }


def run_once(
    *,
    config: AppConfig,
    model,
) -> dict:
    """Execute one complete competitor-monitoring workflow."""

    if not config.news_api_key:
        raise ValueError("NEWS_API_KEY is not configured.")

    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    config.report_dir.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid4())

    with ExitStack() as stack:
        news_client = stack.enter_context(NewsAPIClient(api_key=config.news_api_key))

        slack_client = None
        if config.slack_webhook_url:
            slack_client = stack.enter_context(
                SlackWebhookClient(webhook_url=config.slack_webhook_url)
            )

        graph = build_graph(
            news_client=news_client,
            model=model,
            db_path=config.database_path,
            lookback_days=config.news.lookback_days,
            max_articles_per_competitor=(config.news.max_articles_per_competitor),
            language=config.news.language,
            similarity_threshold=config.memory.similarity_threshold,
            slack_client=slack_client,
            max_summary_words=config.summary.max_words,
            report_dir=str(config.report_dir),
        )

        initial_state = create_initial_state(
            run_id=run_id,
            competitors=config.competitors,
        )

        return graph.invoke(initial_state)
