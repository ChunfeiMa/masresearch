"""Persist node — writes enriched items to SQLite.

The run record itself is saved by run.py after finished_at is set.
"""

from __future__ import annotations

from ..state import PipelineState
from ..store import Store


def persist(state: PipelineState) -> PipelineState:
    store = Store()
    emb_map = state.get("embeddings", {})
    for item in state.get("enriched", []):
        store.upsert_item(item, embedding=emb_map.get(item.id))
    return {}
