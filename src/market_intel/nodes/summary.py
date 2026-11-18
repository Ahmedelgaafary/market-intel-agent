"""LangGraph node for executive-summary generation."""

from typing import Any

from market_intel.state import AgentState
from market_intel.tools.summarization import generate_summary


def summary_node(
    state: AgentState,
    *,
    model: Any,
    max_words: int = 300,
) -> dict:
    """Generate a summary from newly discovered facts."""

    try:
        summary = generate_summary(
            facts=state["new_facts"],
            model=model,
            max_words=max_words,
        )

        return {"summary": summary}

    except Exception as exc:  # noqa: BLE001
        return {
            "summary": None,
            "report_required": False,
            "status": "completed_with_errors",
            "errors": [
                *state["errors"],
                f"Executive summary generation failed: {exc}",
            ],
            "delivery_status": "failed",
        }
