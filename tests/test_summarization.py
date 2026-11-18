from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from market_intel.schemas import Fact
from market_intel.tools.summarization import (
    SummaryGenerationError,
    build_summary_prompt,
    count_words,
    generate_summary,
)


def make_fact():
    return Fact(
        competitor="Microsoft",
        fact="Microsoft announced a new AI infrastructure investment.",
        category="strategy",
        date=date(2026, 11, 10),
        source_url="https://example.com/news",
    )


def test_count_words():
    assert count_words("One two three") == 3
    assert count_words("") == 0


def test_build_summary_prompt_includes_fact_details():
    prompt = build_summary_prompt([make_fact()], max_words=300)

    assert "Microsoft" in prompt
    assert "strategy" in prompt
    assert "2026-11-10" in prompt
    assert "https://example.com/news" in prompt
    assert "Maximum 300 words" in prompt


def test_generate_summary_returns_valid_summary():
    model = Mock()
    model.invoke.return_value = SimpleNamespace(
        content="Microsoft announced a new AI infrastructure investment."
    )

    summary = generate_summary([make_fact()], model)

    assert summary.startswith("Microsoft")
    model.invoke.assert_called_once()


def test_generate_summary_rejects_empty_facts():
    with pytest.raises(SummaryGenerationError, match="without new facts"):
        generate_summary([], Mock())


def test_generate_summary_rejects_too_many_words():
    model = Mock()
    model.invoke.return_value = SimpleNamespace(content="one two three four five")

    with pytest.raises(SummaryGenerationError, match="maximum allowed is 3"):
        generate_summary([make_fact()], model, max_words=3)


def test_generate_summary_rejects_empty_response():
    model = Mock()
    model.invoke.return_value = SimpleNamespace(content="   ")

    with pytest.raises(SummaryGenerationError, match="empty"):
        generate_summary([make_fact()], model)


def test_generate_summary_handles_model_failure():
    model = Mock()
    model.invoke.side_effect = RuntimeError("Provider unavailable")

    with pytest.raises(SummaryGenerationError, match="Provider unavailable"):
        generate_summary([make_fact()], model)


def test_generate_summary_rejects_unsupported_response():
    model = Mock()
    model.invoke.return_value = SimpleNamespace(content=123)

    with pytest.raises(SummaryGenerationError, match="unsupported"):
        generate_summary([make_fact()], model)


def test_generate_summary_accepts_block_response():
    model = Mock()
    model.invoke.return_value = SimpleNamespace(
        content=[{"type": "text", "text": "Microsoft expanded its AI strategy."}]
    )

    summary = generate_summary([make_fact()], model)

    assert summary == "Microsoft expanded its AI strategy."


def test_generate_summary_rejects_invalid_word_limit():
    with pytest.raises(ValueError, match="greater than zero"):
        generate_summary([make_fact()], Mock(), max_words=0)
