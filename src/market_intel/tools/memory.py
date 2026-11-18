"""Persistent memory processing for extracted facts."""

from collections.abc import Iterable
from dataclasses import dataclass

from market_intel.schemas import Fact
from market_intel.tools.db import (
    DatabasePath,
    initialize_database,
    list_facts,
    save_fact,
)
from market_intel.utils.similarity import (
    DEFAULT_SIMILARITY_THRESHOLD,
    DuplicateMatch,
    compare_facts,
)


@dataclass
class MemoryProcessingResult:
    """Summary of one memory-processing operation."""

    new_facts: list[Fact]
    duplicates: list[DuplicateMatch]
    saved_fact_ids: list[int]

    @property
    def new_count(self) -> int:
        """Return the number of newly stored facts."""
        return len(self.new_facts)

    @property
    def duplicate_count(self) -> int:
        """Return the number of duplicate facts."""
        return len(self.duplicates)


def process_facts(
    facts: Iterable[Fact],
    db_path: DatabasePath,
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> MemoryProcessingResult:
    """Compare incoming facts with SQLite memory and save only new facts.

    Existing facts are loaded only for competitors represented in the
    incoming batch. New facts from the current batch are also compared
    against one another.
    """
    incoming_facts = list(facts)

    initialize_database(db_path)

    if not incoming_facts:
        return MemoryProcessingResult(
            new_facts=[],
            duplicates=[],
            saved_fact_ids=[],
        )

    competitors = sorted({fact.competitor for fact in incoming_facts})

    existing_facts: list[Fact] = []

    for competitor in competitors:
        existing_facts.extend(list_facts(db_path, competitor=competitor))

    diff = compare_facts(
        incoming_facts=incoming_facts,
        existing_facts=existing_facts,
        threshold=threshold,
    )

    saved_fact_ids = [save_fact(fact, db_path) for fact in diff.new_facts]

    return MemoryProcessingResult(
        new_facts=diff.new_facts,
        duplicates=diff.duplicates,
        saved_fact_ids=saved_fact_ids,
    )
