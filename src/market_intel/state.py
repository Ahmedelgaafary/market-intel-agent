from datetime import datetime
from typing import Literal, TypedDict

from market_intel.schemas import Article, Fact


class AgentState(TypedDict):
    """Shared state for one market intelligence workflow run."""

    run_id: str
    started_at: datetime
    competitors: list[str]

    articles: list[Article]
    extracted_facts: list[Fact]
    new_facts: list[Fact]

    articles_fetched: int
    facts_extracted: int
    duplicates_found: int
    saved_fact_ids: list[int]

    errors: list[str]

    status: Literal[
        "running",
        "completed",
        "completed_with_errors",
        "failed",
        "no_updates",
    ]

    report_required: bool
    summary: str | None

    delivery_status: Literal[
        "pending",
        "slack",
        "local_fallback",
        "failed",
        "skipped",
    ]
    report_path: str | None
