
"""Lightweight text similarity and memory-diff utilities."""

import math
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from market_intel.schemas import Fact

DEFAULT_SIMILARITY_THRESHOLD = 0.88


@dataclass
class DuplicateMatch:
    """An incoming fact matched against an existing fact."""

    incoming: Fact
    matched: Fact
    similarity: float


@dataclass
class MemoryDiff:
    """The result of comparing incoming facts with stored memory."""

    new_facts: list[Fact]
    duplicates: list[DuplicateMatch]


def validate_threshold(threshold: float) -> None:
    """Validate a similarity threshold between zero and one."""
    if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
        raise ValueError("Similarity threshold must be between 0.0 and 1.0.")


def normalize_fact_text(text: str) -> str:
    """Normalize text for reliable comparison."""
    normalized = unicodedata.normalize("NFKC", text).casefold()

    characters = [
        " " if unicodedata.category(char)[0] in {"P", "S"} else char
        for char in normalized
    ]

    return " ".join("".join(characters).split())


def calculate_similarity(left: str, right: str) -> float:
    """Calculate normalized character-level similarity between two texts."""
    normalized_left = normalize_fact_text(left)
    normalized_right = normalize_fact_text(right)

    if not normalized_left or not normalized_right:
        return 0.0

    return SequenceMatcher(
        None,
        normalized_left,
        normalized_right,
        autojunk=False,
    ).ratio()


def compare_facts(
    incoming_facts: Sequence[Fact],
    existing_facts: Sequence[Fact],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> MemoryDiff:
    """Separate new facts from duplicates.

    Facts are compared only when they belong to the same competitor.
    Newly accepted facts are also considered when checking later incoming
    facts, preventing duplicates within the same batch.
    """
    validate_threshold(threshold)

    known_facts = list(existing_facts)
    new_facts: list[Fact] = []
    duplicates: list[DuplicateMatch] = []

    for incoming in incoming_facts:
        best_match: Fact | None = None
        best_similarity = 0.0

        for existing in known_facts:
            if incoming.competitor != existing.competitor:
                continue

            similarity = calculate_similarity(
                incoming.fact,
                existing.fact,
            )

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = existing

        if best_match is not None and best_similarity >= threshold:
            duplicates.append(
                DuplicateMatch(
                    incoming=incoming,
                    matched=best_match,
                    similarity=best_similarity,
                )
            )
        else:
            new_facts.append(incoming)
            known_facts.append(incoming)

    return MemoryDiff(
        new_facts=new_facts,
        duplicates=duplicates,
    )
