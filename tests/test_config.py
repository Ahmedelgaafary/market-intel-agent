import pytest

from market_intel.config import load_config


def write_config(tmp_path, content):
    path = tmp_path / "config.yaml"
    path.write_text(content, encoding="utf-8")
    return path


VALID_CONFIG = """
competitors:
  - Microsoft
  - Google
  - Amazon

news:
  lookback_days: 7
  max_articles_per_competitor: 10
  language: en

memory:
  similarity_threshold: 0.85

summary:
  max_words: 300

schedule:
  day: monday
  hour: 9
  minute: 0
  timezone: Africa/Cairo
"""


def test_loads_valid_configuration(tmp_path, monkeypatch):
    config_path = write_config(tmp_path, VALID_CONFIG)
    monkeypatch.setenv("NEWS_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "facts.sqlite"))

    config = load_config(config_path, tmp_path / "missing.env")

    assert config.competitors == ("Microsoft", "Google", "Amazon")
    assert config.news.lookback_days == 7
    assert config.news.max_articles_per_competitor == 10
    assert config.memory.similarity_threshold == 0.85
    assert config.summary.max_words == 300
    assert config.schedule.day == "monday"
    assert config.schedule.hour == 9
    assert config.schedule.minute == 0
    assert config.schedule.timezone == "Africa/Cairo"
    assert config.news_api_key == "test-key"


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "missing.yaml", tmp_path / "missing.env")


def test_empty_competitors_are_rejected(tmp_path):
    content = VALID_CONFIG.replace(
        "  - Microsoft\n  - Google\n  - Amazon",
        "  - Microsoft",
    ).replace("competitors:\n  - Microsoft", "competitors: []")

    path = write_config(tmp_path, content)

    with pytest.raises(ValueError, match="competitors"):
        load_config(path, tmp_path / "missing.env")


def test_duplicate_competitors_are_rejected(tmp_path):
    content = VALID_CONFIG.replace(
        "  - Amazon",
        "  - Microsoft",
    )
    path = write_config(tmp_path, content)

    with pytest.raises(ValueError, match="duplicates"):
        load_config(path, tmp_path / "missing.env")


def test_invalid_similarity_threshold_is_rejected(tmp_path):
    content = VALID_CONFIG.replace("0.85", "1.5")
    path = write_config(tmp_path, content)

    with pytest.raises(ValueError, match="similarity_threshold"):
        load_config(path, tmp_path / "missing.env")


def test_invalid_schedule_time_is_rejected(tmp_path):
    content = VALID_CONFIG.replace("hour: 9", "hour: 25")
    path = write_config(tmp_path, content)

    with pytest.raises(ValueError, match="schedule.hour"):
        load_config(path, tmp_path / "missing.env")


def test_invalid_timezone_is_rejected(tmp_path):
    content = VALID_CONFIG.replace("Africa/Cairo", "Invalid/Timezone")
    path = write_config(tmp_path, content)

    with pytest.raises(ValueError, match="timezone"):
        load_config(path, tmp_path / "missing.env")
