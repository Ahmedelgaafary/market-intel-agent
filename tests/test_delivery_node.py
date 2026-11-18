from datetime import date
from unittest.mock import Mock

from market_intel.nodes.delivery import delivery_node
from market_intel.schemas import Fact
from market_intel.tools.slack import SlackDeliveryError


def make_fact():
    return Fact(
        competitor="Amazon",
        fact="Amazon announced a new logistics technology investment.",
        category="strategy",
        date=date(2026, 11, 13),
        source_url="https://example.com/amazon-news",
    )


def make_state():
    return {
        "run_id": "delivery-test-001",
        "competitors": ["Amazon"],
        "articles": [],
        "extracted_facts": [],
        "new_facts": [make_fact()],
        "articles_fetched": 1,
        "facts_extracted": 1,
        "duplicates_found": 0,
        "saved_fact_ids": [1],
        "errors": [],
        "status": "completed",
        "report_required": True,
        "summary": "Amazon announced a logistics technology investment.",
    }


def test_delivery_node_sends_report_to_slack():
    slack_client = Mock()

    result = delivery_node(
        make_state(),
        slack_client=slack_client,
    )

    slack_client.send_message.assert_called_once()
    message = slack_client.send_message.call_args.args[0]

    assert "Executive Summary" in message
    assert "Amazon" in message
    assert result["delivery_status"] == "slack"
    assert result["report_path"] is None


def test_delivery_node_uses_local_fallback_when_slack_fails(tmp_path):
    slack_client = Mock()
    slack_client.send_message.side_effect = SlackDeliveryError("Slack unavailable")

    result = delivery_node(
        make_state(),
        slack_client=slack_client,
        report_dir=tmp_path,
    )

    assert result["delivery_status"] == "local_fallback"
    assert result["status"] == "completed_with_errors"
    assert "Slack unavailable" in result["errors"][0]

    report_path = result["report_path"]

    assert report_path is not None

    from pathlib import Path

    saved_report = Path(report_path)

    assert saved_report.exists()
    assert saved_report.read_text(encoding="utf-8").find("Amazon") >= 0


def test_delivery_node_uses_local_fallback_without_slack(tmp_path):
    result = delivery_node(
        make_state(),
        slack_client=None,
        report_dir=tmp_path,
    )

    assert result["delivery_status"] == "local_fallback"
    assert result["status"] == "completed_with_errors"
    assert "not configured" in result["errors"][0]


def test_delivery_node_records_failure_when_both_destinations_fail(
    tmp_path,
    monkeypatch,
):
    import market_intel.nodes.delivery as delivery_module

    slack_client = Mock()
    slack_client.send_message.side_effect = SlackDeliveryError("Slack unavailable")

    def fail_save(**kwargs):
        raise OSError("Disk unavailable")

    monkeypatch.setattr(
        delivery_module,
        "save_local_report",
        fail_save,
    )

    result = delivery_node(
        make_state(),
        slack_client=slack_client,
        report_dir=tmp_path,
    )

    assert result["delivery_status"] == "failed"
    assert result["status"] == "failed"
    assert any("Slack unavailable" in error for error in result["errors"])
    assert any("Disk unavailable" in error for error in result["errors"])


def test_delivery_node_skips_when_summary_is_missing():
    state = make_state()
    state["summary"] = None

    result = delivery_node(
        state,
        slack_client=Mock(),
    )

    assert result["delivery_status"] == "skipped"
    assert result["report_path"] is None
