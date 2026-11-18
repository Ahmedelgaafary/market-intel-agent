from datetime import UTC, date, datetime

from market_intel.schemas import Fact
from market_intel.tools.reporting import (
    build_report_markdown,
    save_local_report,
)


def make_fact():
    return Fact(
        competitor="Google",
        fact="Google announced a new cloud infrastructure initiative.",
        category="strategy",
        date=date(2026, 11, 12),
        source_url="https://example.com/google-news",
    )


def test_build_report_markdown_includes_summary_and_sources():
    report = build_report_markdown(
        run_id="test-run-001",
        summary="Google announced a cloud initiative.",
        facts=[make_fact()],
        generated_at=datetime(2026, 11, 18, tzinfo=UTC),
    )

    assert "# Weekly Competitor Intelligence Report" in report
    assert "test-run-001" in report
    assert "Executive Summary" in report
    assert "Google announced a cloud initiative." in report
    assert "Google" in report
    assert "https://example.com/google-news" in report


def test_save_local_report_creates_markdown_file(tmp_path):
    report_path = save_local_report(
        report="# Test report",
        run_id="test-run-001",
        report_dir=tmp_path / "reports",
    )

    assert report_path.exists()
    assert report_path.name == "test-run-001.md"
    assert report_path.read_text(encoding="utf-8") == "# Test report"


def test_save_local_report_sanitizes_run_id(tmp_path):
    report_path = save_local_report(
        report="# Test report",
        run_id="test/run:001",
        report_dir=tmp_path,
    )

    assert report_path.name == "test_run_001.md"


def test_save_local_report_rejects_invalid_run_id(tmp_path):
    import pytest

    with pytest.raises(ValueError, match="valid character"):
        save_local_report(
            report="# Test report",
            run_id="///",
            report_dir=tmp_path,
        )
