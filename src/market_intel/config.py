import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class NewsConfig:
    lookback_days: int
    max_articles_per_competitor: int
    language: str


@dataclass(frozen=True)
class MemoryConfig:
    similarity_threshold: float


@dataclass(frozen=True)
class SummaryConfig:
    max_words: int


@dataclass(frozen=True)
class ScheduleConfig:
    day: str
    hour: int
    minute: int
    timezone: str


@dataclass(frozen=True)
class AppConfig:
    competitors: tuple[str, ...]
    news: NewsConfig
    memory: MemoryConfig
    summary: SummaryConfig
    schedule: ScheduleConfig
    database_path: Path
    report_dir: Path
    news_api_key: str | None
    slack_webhook_url: str | None


def _require_mapping(value: object, name: str) -> dict:
    if not isinstance(value, dict):
        raise TypeError(f"Configuration section '{name}' must be a mapping.")
    return value


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"'{name}' must be a positive integer.")
    return value


def load_config(
    config_path: str | Path = "config.yaml",
    env_path: str | Path = ".env",
) -> AppConfig:
    """Load, validate, and return application configuration."""

    load_dotenv(dotenv_path=env_path, override=False)

    path = Path(config_path)

    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    root = _require_mapping(raw, "root")

    competitors = root.get("competitors")
    if (
        not isinstance(competitors, list)
        or not competitors
        or not all(isinstance(item, str) and item.strip() for item in competitors)
    ):
        raise ValueError("'competitors' must be a non-empty list of names.")

    normalized_competitors = tuple(item.strip() for item in competitors)

    if len(set(normalized_competitors)) != len(normalized_competitors):
        raise ValueError("'competitors' must not contain duplicates.")

    news = _require_mapping(root.get("news"), "news")
    memory = _require_mapping(root.get("memory"), "memory")
    summary = _require_mapping(root.get("summary"), "summary")
    schedule = _require_mapping(root.get("schedule"), "schedule")
    reporting = _require_mapping(
        root.get("reporting", {"output_dir": "reports"}),
        "reporting",
    )

    lookback_days = _positive_int(news.get("lookback_days"), "news.lookback_days")
    max_articles = _positive_int(
        news.get("max_articles_per_competitor"),
        "news.max_articles_per_competitor",
    )
    max_words = _positive_int(summary.get("max_words"), "summary.max_words")

    language = news.get("language")
    if not isinstance(language, str) or not language.strip():
        raise ValueError("'news.language' must be a non-empty string.")

    threshold = memory.get("similarity_threshold")
    if (
        isinstance(threshold, bool)
        or not isinstance(threshold, (int, float))
        or not 0 <= threshold <= 1
    ):
        raise ValueError("'memory.similarity_threshold' must be between 0 and 1.")

    day = schedule.get("day")
    if not isinstance(day, str) or day.lower() not in {
        "mon",
        "tue",
        "wed",
        "thu",
        "fri",
        "sat",
        "sun",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }:
        raise ValueError("'schedule.day' must be a valid weekday.")

    hour = schedule.get("hour")
    minute = schedule.get("minute")

    if isinstance(hour, bool) or not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError("'schedule.hour' must be between 0 and 23.")

    if isinstance(minute, bool) or not isinstance(minute, int) or not 0 <= minute <= 59:
        raise ValueError("'schedule.minute' must be between 0 and 59.")

    timezone = schedule.get("timezone", "UTC")
    if not isinstance(timezone, str) or not timezone.strip():
        raise ValueError("'schedule.timezone' must be a non-empty string.")

    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Unknown schedule timezone: {timezone}") from exc
    report_output_dir = os.getenv(
        "REPORT_DIR",
        reporting.get("output_dir", "reports"),
    )

    if not isinstance(report_output_dir, str) or not report_output_dir.strip():
        raise ValueError("'reporting.output_dir' must be a non-empty string.")
    return AppConfig(
        competitors=normalized_competitors,
        news=NewsConfig(
            lookback_days=lookback_days,
            max_articles_per_competitor=max_articles,
            language=language.strip(),
        ),
        memory=MemoryConfig(similarity_threshold=float(threshold)),
        summary=SummaryConfig(max_words=max_words),
        schedule=ScheduleConfig(
            day=day.lower(),
            hour=hour,
            minute=minute,
            timezone=timezone,
        ),
        database_path=Path(os.getenv("DATABASE_PATH", "db/facts.sqlite")),
        report_dir=Path(report_output_dir),
        news_api_key=os.getenv("NEWS_API_KEY"),
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
    )
