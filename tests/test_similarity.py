
"""Tests for fact normalization and similarity comparison."""

from datetime import date

import pytest

from market_intel.schemas import Fact
from market_intel.utils.similarity import (
    DEFAULT_SIMILARITY_THRESHOLD,
    calculate_similarity,
    compare_facts,
    normalize_fact_text,
)


def make_fact(
    competitor: str,
    fact: str,
) -> Fact:
    return Fact(
        competitor=competitor,
        fact=fact,
        category="product_launch",
        date=date(2026, 11, 15),
        source_url="https://example.com/article",
    )


def test_normalize_fact_text():
    result = normalize_fact_text("  Microsoft LAUNCHED, AI!  ")

    assert result == "microsoft launched ai"


def test_normalize_unicode_text():
    assert normalize_fact_text("Ｍｉｃｒｏｓｏｆｔ") == "microsoft"


def test_normalize_repeated_whitespace():
    assert normalize_fact_text("Microsoft   launched\nAI") == (
        "microsoft launched ai"
    )


def test_exact_text_similarity():
    text = "Microsoft launched a new AI platform."

    assert calculate_similarity(text, text) == 1.0


def test_normalized_exact_match_similarity():
    assert calculate_similarity(
        "Microsoft launched a new AI platform.",
        "  MICROSOFT LAUNCHED A NEW AI PLATFORM! ",
    ) == 1.0


def test_empty_text_similarity():
    assert calculate_similarity("", "Microsoft launched AI") == 0.0


def test_threshold_default():
    assert DEFAULT_SIMILARITY_THRESHOLD == 0.88


def test_compare_exact_duplicate():
    existing = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )
    incoming = make_fact(
        "Microsoft",
        "MICROSOFT LAUNCHED A NEW AI PLATFORM!",
    )

    result = compare_facts([incoming], [existing])

    assert result.new_facts == []
    assert len(result.duplicates) == 1
    assert result.duplicates[0].matched == existing
    assert result.duplicates[0].similarity == 1.0


def test_compare_similar_duplicate():
    existing = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform for enterprise customers.",
    )
    incoming = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform for enterprise clients.",
    )

    result = compare_facts([incoming], [existing], threshold=0.88)

    assert result.new_facts == []
    assert len(result.duplicates) == 1
    assert result.duplicates[0].similarity >= 0.88


def test_compare_new_fact():
    existing = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )
    incoming = make_fact(
        "Microsoft",
        "Microsoft hired 500 engineers for its cloud division.",
    )

    result = compare_facts([incoming], [existing])

    assert result.new_facts == [incoming]
    assert result.duplicates == []


def test_different_competitors_are_not_compared():
    existing = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )
    incoming = make_fact(
        "Google",
        "Microsoft launched a new AI platform.",
    )

    result = compare_facts([incoming], [existing])

    assert result.new_facts == [incoming]
    assert result.duplicates == []


def test_duplicate_inside_same_batch():
    first = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )
    second = make_fact(
        "Microsoft",
        "MICROSOFT LAUNCHED A NEW AI PLATFORM!",
    )

    result = compare_facts([first, second], [])

    assert result.new_facts == [first]
    assert len(result.duplicates) == 1
    assert result.duplicates[0].matched == first


def test_multiple_competitors_in_same_batch():
    microsoft_fact = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )
    google_fact = make_fact(
        "Google",
        "Google launched a new AI platform.",
    )

    result = compare_facts(
        [microsoft_fact, google_fact],
        [],
    )

    assert result.new_facts == [microsoft_fact, google_fact]
    assert result.duplicates == []


@pytest.mark.parametrize(
    "threshold",
    [-0.1, 1.1, float("nan"), float("inf")],
)
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError):
        compare_facts([], [], threshold=threshold)


def test_threshold_one_requires_exact_match():
    existing = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform for enterprise customers.",
    )
    incoming = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform for enterprise clients.",
    )

    result = compare_facts(
        [incoming],
        [existing],
        threshold=1.0,
    )

    assert result.new_facts == [incoming]
    assert result.duplicates == []
