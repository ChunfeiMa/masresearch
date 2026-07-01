"""Tavily web-search source agent — blogs, solutions, product launches.

Runs a couple of queries per topic scoped to recent days. Requires TAVILY_API_KEY;
without it the source is a no-op (recorded once to run stats). Results are
de-duplicated by URL within the run before handing off to the graph.
"""

from __future__ import annotations

from ..config import TOPICS, real_key, settings
from ..models import RawItem, SourceType
from ..state import PipelineState

_QUERIES_PER_TOPIC = 2
_RESULTS_PER_QUERY = 5


def fetch_tavily(state: PipelineState) -> PipelineState:
    stats = state.get("stats")
    key = real_key(settings.tavily_api_key)
    if not key:
        if stats is not None:
            stats.errors.append("tavily: no TAVILY_API_KEY set (source skipped)")
        return {"raw": []}

    from tavily import TavilyClient

    client = TavilyClient(api_key=key)
    days = max(1, settings.lookback_hours // 24)
    seen_urls: set[str] = set()
    items: list[RawItem] = []

    for topic_key, cfg in TOPICS.items():
        for query in cfg["queries"][:_QUERIES_PER_TOPIC]:
            try:
                resp = client.search(
                    query=query,
                    topic="news",
                    days=days,
                    max_results=_RESULTS_PER_QUERY,
                    search_depth="basic",
                )
            except Exception as exc:
                if stats is not None:
                    stats.errors.append(f"tavily {topic_key}: {type(exc).__name__}: {exc}")
                continue

            for r in resp.get("results", []):
                url = (r.get("url") or "").strip()
                title = (r.get("title") or "").strip()
                if not url or not title or url in seen_urls:
                    continue
                seen_urls.add(url)
                items.append(
                    RawItem(
                        source_type=SourceType.WEB,
                        source_name="tavily:web",
                        title=title,
                        url=url,
                        raw_summary=(r.get("content") or "").strip()[:2000],
                        topic_hints=[topic_key],
                    ).finalize_id()
                )

    return {"raw": items}
