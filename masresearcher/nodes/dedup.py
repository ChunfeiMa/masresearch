"""Dedup node — drops items already stored, and duplicates within this run.

Phase 0/1: exact dedup by stable id (url+title hash) via the Store.
Phase 2: add near-duplicate detection using local embeddings + find_similar().
"""

from __future__ import annotations

from ..state import PipelineState
from ..store import Store


def dedup(state: PipelineState) -> PipelineState:
    raw = state.get("raw", [])
    for item in raw:
        item.finalize_id()

    # In-run dedup (same id surfaced by two sources)
    unique: dict[str, object] = {}
    for item in raw:
        unique.setdefault(item.id, item)

    store = Store()
    already = store.seen_ids(list(unique.keys()))
    fresh = [item for item in unique.values() if item.id not in already]

    stats = state.get("stats")
    if stats is not None:
        stats.fetched = len(raw)
        stats.duplicates_filtered = len(raw) - len(fresh)

    return {"fresh": fresh}
