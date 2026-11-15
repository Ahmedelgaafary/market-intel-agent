from typing import TypedDict

from market_intel.schemas import Article, Fact


class AgentState(TypedDict):
    """Shared state for one market intelligence workflow run."""

    run_id: str
    competitors: list[str]
    articles: list[Article]
    extracted_facts: list[Fact]
    new_facts: list[Fact]
    summary: str | None
    errors: list[str]