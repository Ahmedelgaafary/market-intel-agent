"""Executive summary generation and validation."""

from typing import Any

from market_intel.schemas import Fact
from market_intel.tools.llm_rate_limit import invoke_with_rate_limit


class SummaryGenerationError(Exception):
    """Raised when an executive summary cannot be generated or validated."""


def count_words(text: str) -> int:
    """Count whitespace-separated words in a summary."""
    return len(text.split())


def build_summary_prompt(facts: list[Fact], max_words: int) -> str:
    """Build a grounded executive-summary prompt."""

    fact_lines = []

    for index, fact in enumerate(facts, start=1):
        fact_lines.append(
            f"{index}. Competitor: {fact.competitor}\n"
            f"   Category: {fact.category}\n"
            f"   Date: {fact.date.isoformat()}\n"
            f"   Development: {fact.fact}\n"
            f"   Source: {fact.source_url}"
        )

    facts_text = "\n\n".join(fact_lines)

    return f"""
You are a market intelligence analyst.

Write a concise executive summary based ONLY on the facts below.

Requirements:
- Maximum {max_words} words.
- Highlight the most strategically important developments.
- Group related developments where appropriate.
- Preserve competitor names and important dates.
- Do not invent information or infer unsupported conclusions.
- Do not include developments that are not supported by the facts.
- Use clear, professional business language.
- Return only the summary, without a title or introductory explanation.

NEW COMPETITOR DEVELOPMENTS:

{facts_text}
""".strip()


def _extract_text(response: Any) -> str:
    """Extract text from a typical LangChain model response."""

    content = getattr(response, "content", response)

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        text_parts = [
            item["text"]
            for item in content
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ]
        return "\n".join(text_parts).strip()

    raise SummaryGenerationError("The language model returned an unsupported response format.")


def generate_summary(
    facts: list[Fact],
    model: Any,
    max_words: int = 300,
) -> str:
    """Generate and validate an executive summary."""

    if max_words < 1:
        raise ValueError("max_words must be greater than zero.")

    if not facts:
        raise SummaryGenerationError("Cannot generate a summary without new facts.")

    prompt = build_summary_prompt(facts, max_words)

    try:
        response = invoke_with_rate_limit(lambda: model.invoke(prompt))
    except Exception as exc:
        raise SummaryGenerationError(f"Language model summary generation failed: {exc}") from exc

    summary = _extract_text(response)

    if not summary:
        raise SummaryGenerationError("The generated summary is empty.")

    word_count = count_words(summary)

    if word_count > max_words:
        raise SummaryGenerationError(
            f"Generated summary contains {word_count} words; the maximum allowed is {max_words}."
        )

    return summary
