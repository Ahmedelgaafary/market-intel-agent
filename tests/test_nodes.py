from datetime import date
from unittest.mock import Mock, patch

from market_intel.nodes.decide import decide_node
from market_intel.nodes.extract import extract_node
from market_intel.nodes.fetch import fetch_node
from market_intel.nodes.memory import memory_node
from market_intel.schemas import Article, Fact
from market_intel.tools.extraction import ExtractionResult, FactExtractionError
from market_intel.tools.memory import MemoryProcessingResult
from market_intel.utils.similarity import DuplicateMatch


def make_article(competitor: str) -> Article:
    return Article(
        competitor=competitor,
        title=f"{competitor} announces a new development",
        source_url="https://example.com/article",
    )


def make_state(competitors: list[str]) -> dict:
    return {
        "run_id": "test-run",
        "competitors": competitors,
        "articles": [],
        "extracted_facts": [],
        "new_facts": [],
        "articles_fetched": 0,
        "facts_extracted": 0,
        "duplicates_found": 0,
        "saved_fact_ids": [],
        "errors": [],
        "status": "running",
        "report_required": False,
        "summary": None,
    }


def test_fetch_node_collects_articles_from_all_competitors():
    client = Mock()
    client.fetch_articles.side_effect = [
        [make_article("Microsoft")],
        [make_article("Google")],
    ]

    result = fetch_node(
        make_state(["Microsoft", "Google"]),
        news_client=client,
    )

    assert len(result["articles"]) == 2
    assert result["articles_fetched"] == 2
    assert result["errors"] == []
    assert client.fetch_articles.call_count == 2


def test_fetch_node_continues_after_competitor_failure():
    from market_intel.tools.news_api import NewsAPIError

    client = Mock()
    client.fetch_articles.side_effect = [
        NewsAPIError("Provider unavailable"),
        [make_article("Google")],
    ]

    result = fetch_node(
        make_state(["Microsoft", "Google"]),
        news_client=client,
    )

    assert len(result["articles"]) == 1
    assert result["articles"][0].competitor == "Google"
    assert result["articles_fetched"] == 1
    assert len(result["errors"]) == 1
    assert "Microsoft" in result["errors"][0]


def test_fetch_node_handles_empty_competitor_list():
    client = Mock()

    result = fetch_node(
        make_state([]),
        news_client=client,
    )

    assert result["articles"] == []
    assert result["articles_fetched"] == 0
    assert result["errors"] == []
    client.fetch_articles.assert_not_called()


def make_fact(competitor: str) -> Fact:
    return Fact(
        competitor=competitor,
        fact=f"{competitor} announced a significant new business development.",
        category="strategy",
        date=date(2026, 11, 18),
        source_url="https://example.com/article",
    )


def test_extract_node_collects_facts_from_articles():
    from market_intel.nodes.extract import extract_node

    state = make_state(["Microsoft", "Google"])
    state["articles"] = [
        make_article("Microsoft"),
        make_article("Google"),
    ]

    model = Mock()

    with patch(
        "market_intel.nodes.extract.extract_facts",
        side_effect=[
            ExtractionResult(
                facts=[make_fact("Microsoft")],
                warnings=[],
                attempts=1,
            ),
            ExtractionResult(
                facts=[make_fact("Google")],
                warnings=[],
                attempts=1,
            ),
        ],
    ):
        result = extract_node(state, model=model)

    assert len(result["extracted_facts"]) == 2
    assert result["facts_extracted"] == 2
    assert result["errors"] == []


def test_extract_node_continues_after_article_failure():
    from market_intel.nodes.extract import extract_node

    state = make_state(["Microsoft", "Google"])
    state["articles"] = [
        make_article("Microsoft"),
        make_article("Google"),
    ]

    model = Mock()

    with patch(
        "market_intel.nodes.extract.extract_facts",
        side_effect=[
            FactExtractionError("Invalid structured output"),
            ExtractionResult(
                facts=[make_fact("Google")],
                warnings=[],
                attempts=1,
            ),
        ],
    ):
        result = extract_node(state, model=model)

    assert len(result["extracted_facts"]) == 1
    assert result["extracted_facts"][0].competitor == "Google"
    assert result["facts_extracted"] == 1
    assert len(result["errors"]) == 1
    assert "Microsoft" in result["errors"][0]


def test_extract_node_handles_empty_articles():
    from market_intel.nodes.extract import extract_node

    state = make_state([])

    result = extract_node(state, model=Mock())

    assert result["extracted_facts"] == []
    assert result["facts_extracted"] == 0
    assert result["errors"] == []


def test_memory_node_processes_extracted_facts():
    state = make_state(["Microsoft"])
    state["extracted_facts"] = [make_fact("Microsoft")]

    expected = MemoryProcessingResult(
        new_facts=[make_fact("Microsoft")],
        duplicates=[],
        saved_fact_ids=[1],
    )

    with patch(
        "market_intel.nodes.memory.process_facts",
        return_value=expected,
    ) as process_mock:
        result = memory_node(
            state,
            db_path=":memory:",
            similarity_threshold=0.85,
        )

    assert result["new_facts"] == expected.new_facts
    assert result["duplicates_found"] == 0
    assert result["saved_fact_ids"] == [1]

    process_mock.assert_called_once_with(
        facts=state["extracted_facts"],
        db_path=":memory:",
        threshold=0.85,
    )


def test_memory_node_records_duplicate_count():
    state = make_state(["Microsoft"])
    state["extracted_facts"] = [make_fact("Microsoft")]

    duplicate = DuplicateMatch(
        incoming=make_fact("Microsoft"),
        matched=make_fact("Microsoft"),
        similarity=0.95,
    )

    expected = MemoryProcessingResult(
        new_facts=[],
        duplicates=[duplicate],
        saved_fact_ids=[],
    )

    with patch(
        "market_intel.nodes.memory.process_facts",
        return_value=expected,
    ):
        result = memory_node(
            state,
            db_path=":memory:",
        )

    assert result["new_facts"] == []
    assert result["duplicates_found"] == 1
    assert result["saved_fact_ids"] == []


def test_decide_node_requires_report_when_new_facts_exist():
    state = make_state(["Microsoft"])
    state["new_facts"] = [make_fact("Microsoft")]

    result = decide_node(state)

    assert result["report_required"] is True
    assert result["status"] == "completed"


def test_decide_node_returns_no_updates_when_no_new_facts_exist():
    state = make_state(["Microsoft"])

    result = decide_node(state)

    assert result["report_required"] is False
    assert result["status"] == "no_updates"


def test_decide_node_preserves_partial_success_status():
    state = make_state(["Microsoft", "Google"])
    state["new_facts"] = [make_fact("Microsoft")]
    state["errors"] = ["News fetch failed for Google"]

    result = decide_node(state)

    assert result["report_required"] is True
    assert result["status"] == "completed_with_errors"


def test_decide_node_reports_errors_without_new_facts():
    state = make_state(["Microsoft"])
    state["errors"] = ["News fetch failed for Microsoft"]

    result = decide_node(state)

    assert result["report_required"] is False
    assert result["status"] == "completed_with_errors"


def test_extract_node_records_extraction_warnings():
    state = make_state(["Microsoft"])
    state["articles"] = [make_article("Microsoft")]

    extraction_result = ExtractionResult(
        facts=[],
        warnings=["Article contains insufficient information."],
        attempts=1,
    )

    with patch(
        "market_intel.nodes.extract.extract_facts",
        return_value=extraction_result,
    ):
        result = extract_node(state, model=Mock())

    assert result["extracted_facts"] == []
    assert result["facts_extracted"] == 0
    assert len(result["errors"]) == 1
    assert "insufficient information" in result["errors"][0]


def test_extract_node_handles_unexpected_exception():
    state = make_state(["Microsoft"])
    state["articles"] = [make_article("Microsoft")]

    with patch(
        "market_intel.nodes.extract.extract_facts",
        side_effect=RuntimeError("Unexpected model failure"),
    ):
        result = extract_node(state, model=Mock())

    assert result["extracted_facts"] == []
    assert result["facts_extracted"] == 0
    assert len(result["errors"]) == 1
    assert "Unexpected model failure" in result["errors"][0]
