"""Pydantic schemas shared across the pipeline and emitted to the UI as JSON."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class SourceType(str, Enum):
    ARXIV = "arxiv"
    RSS = "rss"
    WEB = "web"
    GITHUB = "github"
    HUGGINGFACE = "huggingface"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def stable_id(url: str, title: str) -> str:
    """Deterministic id from url+title — used for exact-dedup and JSON keys."""
    h = hashlib.sha1(f"{url.strip().lower()}::{title.strip().lower()}".encode())
    return h.hexdigest()[:16]


class RawItem(BaseModel):
    """A candidate discovered by a source agent, before enrichment."""

    id: str = ""
    source_type: SourceType
    source_name: str  # e.g. "arxiv:cs.RO", "rss:huggingface-blog"
    title: str
    url: str
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    raw_summary: str = ""  # abstract / snippet from the source
    fetched_at: datetime = Field(default_factory=_now)
    topic_hints: list[str] = Field(default_factory=list)  # topic keys guessed at fetch time

    def finalize_id(self) -> "RawItem":
        if not self.id:
            self.id = stable_id(self.url, self.title)
        return self


class EnrichedItem(BaseModel):
    """A RawItem after the summarize / classify / diagram nodes."""

    id: str
    source_type: SourceType
    source_name: str
    title: str
    url: str
    authors: list[str] = Field(default_factory=list)
    published_at: datetime | None = None

    # Hierarchical UI content (L2/L3)
    tldr: str = ""
    abstract: str = ""
    introduction: str = ""
    key_contributions: list[str] = Field(default_factory=list)
    why_it_matters: str = ""

    # Classification & ranking (for L0/L1 stats and sorting)
    topics: list[str] = Field(default_factory=list)  # topic keys
    tags: list[str] = Field(default_factory=list)
    novelty_score: float = 0.0  # 0..1
    impact_score: float = 0.0  # 0..1

    # Mermaid source rendered client-side into a concept diagram
    mermaid: str = ""

    enriched_at: datetime = Field(default_factory=_now)


class RunStats(BaseModel):
    """Per-run summary that feeds the dashboard header + trend sparklines."""

    run_id: str
    started_at: datetime
    finished_at: datetime | None = None
    fetched: int = 0
    duplicates_filtered: int = 0
    enriched: int = 0
    by_source: dict[str, int] = Field(default_factory=dict)
    by_topic: dict[str, int] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
