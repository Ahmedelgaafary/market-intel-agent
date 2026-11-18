"""Tests for persistent memory processing."""

from datetime import date

from market_intel.schemas import Fact
from market_intel.tools.db import count_facts, list_facts
from market_intel.tools.memory import process_facts


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


def test_process_new_fact(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    incoming = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )

    result = process_facts([incoming], db_path)

    assert result.new_count == 1
    assert result.duplicate_count == 0
    assert len(result.saved_fact_ids) == 1
    assert count_facts(db_path) == 1


def test_process_duplicate_fact(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    original = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )

    duplicate = make_fact(
        "Microsoft",
        "MICROSOFT LAUNCHED A NEW AI PLATFORM!",
    )

    first_result = process_facts([original], db_path)
    second_result = process_facts([duplicate], db_path)

    assert first_result.new_count == 1
    assert second_result.new_count == 0
    assert second_result.duplicate_count == 1
    assert second_result.saved_fact_ids == []
    assert count_facts(db_path) == 1


def test_process_mixed_new_and_duplicate_facts(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    original = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )

    process_facts([original], db_path)

    duplicate = make_fact(
        "Microsoft",
        "MICROSOFT LAUNCHED A NEW AI PLATFORM!",
    )

    new_fact = make_fact(
        "Microsoft",
        "Microsoft hired 500 engineers for its cloud division.",
    )

    result = process_facts([duplicate, new_fact], db_path)

    assert result.new_count == 1
    assert result.duplicate_count == 1
    assert count_facts(db_path) == 2


def test_process_facts_from_different_competitors(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    microsoft_fact = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )

    google_fact = make_fact(
        "Google",
        "Google launched a new AI platform.",
    )

    result = process_facts(
        [microsoft_fact, google_fact],
        db_path,
    )

    assert result.new_count == 2
    assert result.duplicate_count == 0
    assert count_facts(db_path) == 2


def test_process_duplicates_inside_same_batch(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    first = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )

    second = make_fact(
        "Microsoft",
        "MICROSOFT LAUNCHED A NEW AI PLATFORM!",
    )

    result = process_facts([first, second], db_path)

    assert result.new_count == 1
    assert result.duplicate_count == 1
    assert count_facts(db_path) == 1


def test_process_empty_list(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    result = process_facts([], db_path)

    assert result.new_facts == []
    assert result.duplicates == []
    assert result.saved_fact_ids == []
    assert count_facts(db_path) == 0


def test_memory_persists_between_calls(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    original = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform.",
    )

    process_facts([original], db_path)

    # A separate call simulates a later agent run.
    repeated = make_fact(
        "Microsoft",
        "MICROSOFT LAUNCHED A NEW AI PLATFORM!",
    )

    result = process_facts([repeated], db_path)

    assert result.duplicate_count == 1
    assert result.new_count == 0

    stored_facts = list_facts(db_path)

    assert len(stored_facts) == 1
    assert stored_facts[0].fact == original.fact


def test_custom_similarity_threshold(tmp_path):
    db_path = tmp_path / "memory.sqlite"

    original = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform for enterprise customers.",
    )

    incoming = make_fact(
        "Microsoft",
        "Microsoft launched a new AI platform for enterprise clients.",
    )

    process_facts([original], db_path)

    result = process_facts(
        [incoming],
        db_path,
        threshold=1.0,
    )

    assert result.new_count == 1
    assert result.duplicate_count == 0
    assert count_facts(db_path) == 2
