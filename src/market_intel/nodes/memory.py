"""Memory processing node for the market intelligence graph."""

from market_intel.state import AgentState
from market_intel.tools.db import DatabasePath
from market_intel.tools.memory import process_facts


def memory_node(
    state: AgentState,
    *,
    db_path: DatabasePath,
    similarity_threshold: float = 0.85,
) -> dict:
    """Compare extracted facts with memory and persist new facts."""
    result = process_facts(
        facts=state["extracted_facts"],
        db_path=db_path,
        threshold=similarity_threshold,
    )

    return {
        "new_facts": result.new_facts,
        "duplicates_found": result.duplicate_count,
        "saved_fact_ids": result.saved_fact_ids,
    }
