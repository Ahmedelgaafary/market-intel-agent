"""LangGraph assembly with auditing, executive summaries, and delivery."""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from market_intel.nodes.decide import decide_node
from market_intel.nodes.delivery import delivery_node
from market_intel.nodes.extract import extract_node
from market_intel.nodes.fetch import fetch_node
from market_intel.nodes.memory import memory_node
from market_intel.nodes.summary import summary_node
from market_intel.schemas import RunResult, utc_now
from market_intel.state import AgentState
from market_intel.tools.db import (
    DatabasePath,
    initialize_database,
    save_run,
)
from market_intel.tools.news_api import NewsAPIClient
from market_intel.tools.slack import SlackWebhookClient


def _create_run(
    state: AgentState,
    *,
    status: str,
    completed: bool = False,
    errors: list[str] | None = None,
) -> RunResult:
    """Build an audit record from the current workflow state."""

    run = RunResult(
        run_id=state["run_id"],
        started_at=state.get("started_at", utc_now()),
        status=status,
        articles_fetched=state.get("articles_fetched", 0),
        facts_extracted=state.get("facts_extracted", 0),
        new_facts=len(state.get("new_facts", [])),
        errors=errors if errors is not None else state.get("errors", []),
    )

    if completed:
        run.mark_completed()

    return run


def _guard_node(
    node: Callable[[AgentState], dict],
    *,
    db_path: DatabasePath,
) -> Callable[[AgentState], dict]:
    """Persist unexpected node failures before propagating them."""

    def guarded(state: AgentState) -> dict:
        try:
            return node(state)
        except Exception as exc:
            errors = [
                *state.get("errors", []),
                f"Workflow execution failed: {exc}",
            ]

            failed_run = _create_run(
                state,
                status="failed",
                completed=True,
                errors=errors,
            )
            save_run(failed_run, db_path)
            raise

    return guarded


def build_graph(
    *,
    news_client: NewsAPIClient,
    model: Any,
    db_path: DatabasePath,
    lookback_days: int = 7,
    max_articles_per_competitor: int = 10,
    language: str = "en",
    similarity_threshold: float = 0.85,
    slack_client: SlackWebhookClient | None = None,
    max_summary_words: int = 300,
    report_dir: str | Path = "reports",
):
    """Build and compile the complete competitor-monitoring workflow."""

    if max_summary_words < 1:
        raise ValueError("max_summary_words must be greater than zero.")

    if slack_client is None:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL", "").strip()

        if webhook_url:
            slack_client = SlackWebhookClient(webhook_url)

    workflow = StateGraph(AgentState)

    def audit_start(state: AgentState) -> dict:
        """Initialize persistence and record the running status."""

        initialize_database(db_path)

        started_at = utc_now()

        run = RunResult(
            run_id=state["run_id"],
            started_at=started_at,
            status="running",
        )
        save_run(run, db_path)

        return {
            "started_at": started_at,
            "delivery_status": "pending",
            "report_path": None,
        }

    def run_fetch(state: AgentState) -> dict:
        return fetch_node(
            state,
            news_client=news_client,
            lookback_days=lookback_days,
            max_articles_per_competitor=max_articles_per_competitor,
            language=language,
        )

    def run_extract(state: AgentState) -> dict:
        return extract_node(state, model=model)

    def run_memory(state: AgentState) -> dict:
        return memory_node(
            state,
            db_path=db_path,
            similarity_threshold=similarity_threshold,
        )

    def run_decide(state: AgentState) -> dict:
        return decide_node(state)

    def run_summary(state: AgentState) -> dict:
        return summary_node(
            state,
            model=model,
            max_words=max_summary_words,
        )

    def run_delivery(state: AgentState) -> dict:
        return delivery_node(
            state,
            slack_client=slack_client,
            report_dir=report_dir,
        )

    def route_after_decision(state: AgentState) -> str:
        """Skip reporting when no new facts were discovered."""

        return "summary" if state["report_required"] else "audit_finish"

    def route_after_summary(state: AgentState) -> str:
        """Skip delivery if summary generation failed."""

        return "delivery" if state.get("summary") else "audit_finish"

    def audit_finish(state: AgentState) -> dict:
        """Persist final workflow metrics and status."""

        run = _create_run(
            state,
            status=state["status"],
            completed=True,
        )
        save_run(run, db_path)

        return {}

    workflow.add_node("audit_start", audit_start)

    workflow.add_node(
        "fetch",
        _guard_node(run_fetch, db_path=db_path),
    )
    workflow.add_node(
        "extract",
        _guard_node(run_extract, db_path=db_path),
    )
    workflow.add_node(
        "memory",
        _guard_node(run_memory, db_path=db_path),
    )
    workflow.add_node(
        "decide",
        _guard_node(run_decide, db_path=db_path),
    )
    workflow.add_node(
        "summary",
        _guard_node(run_summary, db_path=db_path),
    )
    workflow.add_node(
        "delivery",
        _guard_node(run_delivery, db_path=db_path),
    )
    workflow.add_node(
        "audit_finish",
        _guard_node(audit_finish, db_path=db_path),
    )

    workflow.add_edge(START, "audit_start")
    workflow.add_edge("audit_start", "fetch")
    workflow.add_edge("fetch", "extract")
    workflow.add_edge("extract", "memory")
    workflow.add_edge("memory", "decide")

    workflow.add_conditional_edges(
        "decide",
        route_after_decision,
        {
            "summary": "summary",
            "audit_finish": "audit_finish",
        },
    )

    workflow.add_conditional_edges(
        "summary",
        route_after_summary,
        {
            "delivery": "delivery",
            "audit_finish": "audit_finish",
        },
    )

    workflow.add_edge("delivery", "audit_finish")
    workflow.add_edge("audit_finish", END)

    return workflow.compile()
