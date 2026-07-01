"""RSS source agent — curated AI-lab / research blogs.

Parses each feed in config.RSS_FEEDS, keeps entries within the lookback window
that match at least one topic, and returns them as RawItems. No API key needed.
Feed-level failures are recorded to run stats, never fatal.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import feedparser

from ..config import RSS_FEEDS, match_topics, settings
from ..models import RawItem, SourceType
from ..state import PipelineState

_MAX_PER_FEED = 25


def _entry_dt(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_rss(state: PipelineState) -> PipelineState:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.lookback_hours)
    stats = state.get("stats")
    items: list[RawItem] = []

    for feed in RSS_FEEDS:
        try:
            parsed = feedparser.parse(feed["url"])
        except Exception as exc:
            if stats is not None:
                stats.errors.append(f"rss {feed['name']}: {type(exc).__name__}: {exc}")
            continue

        for entry in parsed.entries[:_MAX_PER_FEED]:
            published = _entry_dt(entry)
            if published and published < cutoff:
                continue

            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            if not title or not link:
                continue

            topics = match_topics(f"{title} {summary}")
            if not topics:
                continue  # keep the feed on-topic

            items.append(
                RawItem(
                    source_type=SourceType.RSS,
                    source_name=f"rss:{feed['name']}",
                    title=title,
                    url=link,
                    published_at=published,
                    raw_summary=summary.strip()[:2000],
                    topic_hints=topics,
                ).finalize_id()
            )

    return {"raw": items}
