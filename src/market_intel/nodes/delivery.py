"""LangGraph node for Slack delivery and local fallback."""

from pathlib import Path

from market_intel.state import AgentState
from market_intel.tools.reporting import (
    build_report_markdown,
    save_local_report,
)
from market_intel.tools.slack import SlackWebhookClient


def delivery_node(
    state: AgentState,
    *,
    slack_client: SlackWebhookClient | None,
    report_dir: str | Path = "reports",
) -> dict:
    """Deliver an executive report to Slack or save it locally."""

    summary = state["summary"]

    if not summary:
        return {
            "delivery_status": "skipped",
            "report_path": None,
        }

    report = build_report_markdown(
        run_id=state["run_id"],
        summary=summary,
        facts=state["new_facts"],
    )

    try:
        if slack_client is None:
            raise RuntimeError("SLACK_WEBHOOK_URL is not configured.")

        slack_client.send_message(report)

        return {
            "delivery_status": "slack",
            "report_path": None,
        }

    except Exception as slack_error:  # noqa: BLE001
        errors = [
            *state["errors"],
            f"Slack delivery failed: {slack_error}",
        ]

        try:
            report_path = save_local_report(
                report=report,
                run_id=state["run_id"],
                report_dir=report_dir,
            )

            return {
                "delivery_status": "local_fallback",
                "report_path": str(report_path),
                "status": "completed_with_errors",
                "errors": errors,
            }

        except Exception as fallback_error:  # noqa: BLE001
            return {
                "delivery_status": "failed",
                "report_path": None,
                "status": "failed",
                "errors": [
                    *errors,
                    f"Local report fallback failed: {fallback_error}",
                ],
            }
