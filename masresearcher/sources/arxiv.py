"""arXiv source agent.

Queries the arXiv API per topic (category filter × topic query terms), keeps
submissions within the lookback window, and returns normalized RawItems.
Runs as one LangGraph branch; needs no API key.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import arxiv
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import TOPICS, settings
from ..models import RawItem, SourceType
from ..state import PipelineState

# Cap results fetched per topic before dedup/lookback filtering, to bound API load.
_MAX_PER_TOPIC = 30


def _build_query(cfg: dict) -> str:
    cats = " OR ".join(f"cat:{c}" for c in cfg["arxiv_categories"])
    terms = " OR ".join(f'all:"{q}"' for q in cfg["queries"])
    return f"({cats}) AND ({terms})"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
def _search(query: str) -> list[arxiv.Result]:
    client = arxiv.Client(page_size=_MAX_PER_TOPIC, delay_seconds=3, num_retries=2)
    search = arxiv.Search(
        query=query,
        max_results=_MAX_PER_TOPIC,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    return list(client.results(search))


def fetch_arxiv(state: PipelineState) -> PipelineState:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.lookback_hours)
    stats = state.get("stats")
    items: list[RawItem] = []
    seen_ids: set[str] = set()

    for topic_key, cfg in TOPICS.items():
        try:
            results = _search(_build_query(cfg))
        except Exception as exc:
            # A topic failing shouldn't sink the source, but record it so a
            # silently-dropped topic is visible in the run stats / dashboard.
            if stats is not None:
                stats.errors.append(f"arxiv {topic_key}: {type(exc).__name__}: {exc}")
            continue

        for r in results:
            published = r.published
            if published and published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            if published and published < cutoff:
                continue

            arxiv_id = r.get_short_id()
            if arxiv_id in seen_ids:
                # Same paper matched two topics — record both hints, keep one item.
                for it in items:
                    if it.url == r.entry_id and topic_key not in it.topic_hints:
                        it.topic_hints.append(topic_key)
                continue
            seen_ids.add(arxiv_id)

            items.append(
                RawItem(
                    source_type=SourceType.ARXIV,
                    source_name=f"arxiv:{arxiv_id.split('v')[0]}",
                    title=r.title.strip().replace("\n", " "),
                    url=r.entry_id,
                    authors=[a.name for a in r.authors][:12],
                    published_at=published,
                    raw_summary=r.summary.strip().replace("\n", " "),
                    topic_hints=[topic_key],
                ).finalize_id()
            )

    return {"raw": items}
