"""Classify node — refine topics + set novelty/impact scores via the LLM.

Runs after summarize. Overrides the keyword-guessed topics with the model's
choice (intersected with the allowed set) and replaces the placeholder 0.5
scores used for dashboard ranking. Per-item failures keep the prior values.
"""

from __future__ import annotations

from .. import llm
from ..config import TOPIC_KEYS
from ..models import EnrichedItem
from ..state import PipelineState


def _classify_one(item: EnrichedItem, stats) -> EnrichedItem:
    try:
        res = llm.classify(item.title, item.abstract or item.tldr)
        topics = [t for t in res.topics if t in TOPIC_KEYS]
        if topics:
            item.topics = topics
        item.novelty_score = res.novelty_score
        item.impact_score = res.impact_score
    except Exception as exc:
        if stats is not None:
            stats.errors.append(f"classify {item.id}: {type(exc).__name__}: {exc}")
    return item


def classify(state: PipelineState) -> PipelineState:
    items = state.get("enriched", [])
    if not llm.available() or not items:
        return {}
    stats = state.get("stats")
    updated = llm.map_parallel(lambda it: _classify_one(it, stats), items)

    # Recompute topic tallies now that topics are authoritative.
    if stats is not None:
        stats.by_topic = {}
        for e in updated:
            for t in e.topics:
                stats.by_topic[t] = stats.by_topic.get(t, 0) + 1

    return {"enriched": updated}
