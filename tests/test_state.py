from market_intel.schemas import Article, Fact
from market_intel.state import AgentState


def test_agent_state_accepts_expected_fields():
    article = Article(
        competitor="Acme",
        title="Acme announces a partnership",
        source_url="https://example.com/partnership",
    )

    fact = Fact(
        competitor="Acme",
        fact="Acme announced a strategic partnership.",
        category="partnership",
        date="2026-10-25",
        source_url="https://example.com/partnership",
    )

    state: AgentState = {
        "run_id": "run-001",
        "competitors": ["Acme"],
        "articles": [article],
        "extracted_facts": [fact],
        "new_facts": [fact],
        "summary": None,
        "errors": [],
    }

    assert state["run_id"] == "run-001"
    assert len(state["articles"]) == 1
    assert len(state["new_facts"]) == 1
    assert state["summary"] is None
