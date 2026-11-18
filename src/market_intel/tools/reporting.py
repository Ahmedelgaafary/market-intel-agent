"""Markdown executive-report generation and local persistence."""

import re
from datetime import UTC, datetime
from pathlib import Path

from market_intel.schemas import Fact


def build_report_markdown(
    *,
    run_id: str,
    summary: str,
    facts: list[Fact],
    generated_at: datetime | None = None,
) -> str:
    """Build a source-attributed Markdown executive report."""

    timestamp = generated_at or datetime.now(UTC)

    fact_sections = []

    for fact in facts:
        fact_sections.append(
            f"### {fact.competitor} — {fact.category}\n"
            f"- **Date:** {fact.date.isoformat()}\n"
            f"- **Development:** {fact.fact}\n"
            f"- **Source:** {fact.source_url}"
        )

    developments = "\n\n".join(fact_sections)

    return (
        "# Weekly Competitor Intelligence Report\n\n"
        f"- **Run ID:** `{run_id}`\n"
        f"- **Generated:** {timestamp.isoformat()}\n\n"
        "## Executive Summary\n\n"
        f"{summary}\n\n"
        "## New Developments\n\n"
        f"{developments}\n"
    )


def save_local_report(
    *,
    report: str,
    run_id: str,
    report_dir: str | Path = "reports",
) -> Path:
    """Save a report as a Markdown file."""

    safe_run_id = re.sub(r"[^a-zA-Z0-9_-]", "_", run_id)

    if not re.search(r"[a-zA-Z0-9]", run_id):
        raise ValueError("run_id must contain at least one valid character.")

    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / f"{safe_run_id}.md"
    report_path.write_text(report, encoding="utf-8")

    return report_path
