"""Enrichment node — turns fresh RawItems into EnrichedItems.

Phase 1: when ANTHROPIC_API_KEY is set, each item is summarized by Claude into
structured hierarchical content. Without a key (or if a call fails), it falls
back to a deterministic stub so the pipeline never hard-stops. Honors
settings.max_items_per_run as a cost guard.

Phase 3 will add real classification (topics/scores) and the Mermaid diagram;
for now topics come from keyword hints and scores default to 0.5.
"""

from __future__ import annotations

from .. import llm
from ..config import TOPICS, settings
from ..models import EnrichedItem, RawItem
from ..state import PipelineState


def _guess_topics(item: RawItem) -> list[str]:
    if item.topic_hints:
        return item.topic_hints
    text = f"{item.title} {item.raw_summary}".lower()
    hits = [k for k, cfg in TOPICS.items() if any(kw in text for kw in cfg["keywords"])]
    return hits or ["multi_agent"]


def _base(item: RawItem, topics: list[str]) -> EnrichedItem:
    return EnrichedItem(
        id=item.id,
        source_type=item.source_type,
        source_name=item.source_name,
        title=item.title,
        url=item.url,
        authors=item.authors,
        published_at=item.published_at,
        topics=topics,
        novelty_score=0.5,  # refined in Phase 3
        impact_score=0.5,
    )


def _stub_enrich(item: RawItem, topics: list[str]) -> EnrichedItem:
    e = _base(item, topics)
    e.tldr = (item.raw_summary[:200] + "…") if item.raw_summary else item.title
    e.abstract = item.raw_summary
    return e


def _llm_enrich(item: RawItem, topics: list[str]) -> EnrichedItem:
    s = llm.summarize(item)
    e = _base(item, topics)
    e.tldr = s.tldr
    e.abstract = s.abstract
    e.introduction = s.introduction
    e.key_contributions = s.key_contributions
    e.why_it_matters = s.why_it_matters
    e.tags = s.tags
    return e


def enrich(state: PipelineState) -> PipelineState:
    fresh = state.get("fresh", [])[: settings.max_items_per_run]
    stats = state.get("stats")
    use_llm = llm.available()

    enriched: list[EnrichedItem] = []
    for item in fresh:
        topics = _guess_topics(item)
        if use_llm:
            try:
                enriched.append(_llm_enrich(item, topics))
                continue
            except Exception as exc:  # per-item fallback; keep the run going
                if stats is not None:
                    stats.errors.append(f"enrich {item.id}: {exc}")
        enriched.append(_stub_enrich(item, topics))

    if stats is not None:
        stats.enriched = len(enriched)
        for e in enriched:
            stats.by_source[e.source_name] = stats.by_source.get(e.source_name, 0) + 1
            for t in e.topics:
                stats.by_topic[t] = stats.by_topic.get(t, 0) + 1

    return {"enriched": enriched}
