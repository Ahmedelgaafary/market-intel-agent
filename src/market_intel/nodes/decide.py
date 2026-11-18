"""Decision node for the market intelligence graph."""

from market_intel.state import AgentState


def decide_node(state: AgentState) -> dict:
    """Determine whether a report is required and set the run status."""
    has_new_facts = bool(state["new_facts"])
    has_errors = bool(state["errors"])

    if has_errors:
        status = "completed_with_errors"
    elif has_new_facts:
        status = "completed"
    else:
        status = "no_updates"

    return {
        "report_required": has_new_facts,
        "status": status,
    }
