"""Enrichment node — turns fresh RawItems into EnrichedItems.

Phase 0 STUB: deterministic pass-through (no LLM) so the pipeline runs offline
and produces valid JSON for the UI. Phase 1/3 replaces the body with real Claude
calls (structured summary -> classify -> Mermaid diagram), respecting
settings.max_items_per_run as a cost guard.
"""

from __future__ import annotations

from ..config import TOPICS, settings
from ..models import EnrichedItem, RawItem
from ..state import PipelineState


def _stub_enrich(item: RawItem) -> EnrichedItem:
    topics = item.topic_hints or _guess_topics(item)
    return EnrichedItem(
        id=item.id,
        source_type=item.source_type,
        source_name=item.source_name,
        title=item.title,
        url=item.url,
        authors=item.authors,
        published_at=item.published_at,
        tldr=(item.raw_summary[:200] + "…") if item.raw_summary else item.title,
        abstract=item.raw_summary,
        introduction="",  # filled by Claude in P1
        key_contributions=[],
        why_it_matters="",
        topics=topics,
        tags=[],
        novelty_score=0.5,
        impact_score=0.5,
        mermaid="",  # filled by the diagram agent in P3
    )


def _guess_topics(item: RawItem) -> list[str]:
    text = f"{item.title} {item.raw_summary}".lower()
    hits = [k for k, cfg in TOPICS.items() if any(kw in text for kw in cfg["keywords"])]
    return hits or ["multi_agent"]


def enrich(state: PipelineState) -> PipelineState:
    fresh = state.get("fresh", [])[: settings.max_items_per_run]
    enriched = [_stub_enrich(item) for item in fresh]

    stats = state.get("stats")
    if stats is not None:
        stats.enriched = len(enriched)
        for e in enriched:
            stats.by_source[e.source_name] = stats.by_source.get(e.source_name, 0) + 1
            for t in e.topics:
                stats.by_topic[t] = stats.by_topic.get(t, 0) + 1

    return {"enriched": enriched}
