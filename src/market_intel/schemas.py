from datetime import UTC, date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

FactCategory = Literal[
    "product_launch",
    "pricing",
    "hiring",
    "partnership",
    "leadership",
    "financial",
    "strategy",
    "other",
]


class Article(BaseModel):
    """Normalized article retrieved from a news provider."""

    model_config = ConfigDict(str_strip_whitespace=True)

    competitor: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=500)
    source_url: HttpUrl
    published_at: datetime | None = None
    description: str | None = None
    content: str | None = None

    @classmethod
    def from_provider(
        cls,
        *,
        competitor: str,
        title: str,
        source_url: str,
        published_at: datetime | None = None,
        description: str | None = None,
        content: str | None = None,
    ) -> "Article":
        """Create an article from normalized provider fields."""
        return cls(
            competitor=competitor,
            title=title,
            source_url=source_url,
            published_at=published_at,
            description=description,
            content=content,
        )


class Fact(BaseModel):
    """A structured, source-attributed competitor development."""

    model_config = ConfigDict(str_strip_whitespace=True)

    competitor: str = Field(min_length=1, max_length=200)
    fact: str = Field(min_length=10, max_length=2000)
    category: FactCategory = "other"
    date: date
    source_url: HttpUrl


class RunResult(BaseModel):
    """Audit summary for one agent execution."""

    run_id: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal[
        "running",
        "completed",
        "completed_with_errors",
        "failed",
        "no_updates",
    ] = "running"

    articles_fetched: int = Field(default=0, ge=0)
    facts_extracted: int = Field(default=0, ge=0)
    new_facts: int = Field(default=0, ge=0)
    errors: list[str] = Field(default_factory=list)

    def mark_completed(self) -> None:
        """Record the completion timestamp in UTC."""
        self.completed_at = datetime.now(UTC)


def utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""
    return datetime.now(UTC)