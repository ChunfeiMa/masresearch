"""Persist node — writes enriched items to SQLite.

The run record itself is saved by run.py after finished_at is set.
"""

from __future__ import annotations

from ..state import PipelineState
from ..store import Store


def persist(state: PipelineState) -> PipelineState:
    store = Store()
    for item in state.get("enriched", []):
        store.upsert_item(item)
    return {}
