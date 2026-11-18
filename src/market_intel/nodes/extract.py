"""Fact extraction node for the market intelligence graph."""

from typing import Any

from market_intel.state import AgentState
from market_intel.tools.extraction import (
    FactExtractionError,
    extract_facts,
)


def extract_node(
    state: AgentState,
    *,
    model: Any,
) -> dict:
    """Extract structured facts from each article independently."""
    extracted_facts = []
    errors = []

    for article in state["articles"]:
        try:
            result = extract_facts(article, model)

            extracted_facts.extend(result.facts)

            for warning in result.warnings:
                errors.append(f"Extraction warning for {article.competitor}: {warning}")

        except FactExtractionError as exc:
            errors.append(
                f"Fact extraction failed for {article.competitor} ({article.title}): {exc}"
            )

        except Exception as exc:  # noqa: BLE001
            # Isolate unexpected failures so other articles can be processed.
            errors.append(
                f"Unexpected extraction error for {article.competitor} ({article.title}): {exc}"
            )

    return {
        "extracted_facts": extracted_facts,
        "facts_extracted": len(extracted_facts),
        "errors": [*state["errors"], *errors],
    }
