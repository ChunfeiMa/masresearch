"""LangGraph state passed between nodes."""

from __future__ import annotations

from typing import Annotated, TypedDict

from .models import EnrichedItem, RawItem, RunStats


def _extend(a: list, b: list) -> list:
    """Reducer so parallel source branches can each append to `raw`."""
    return (a or []) + (b or [])


class PipelineState(TypedDict, total=False):
    run_id: str
    queries: dict[str, list[str]]        # topic_key -> expanded queries
    raw: Annotated[list[RawItem], _extend]  # accumulated across source branches
    fresh: list[RawItem]                 # after dedup
    enriched: list[EnrichedItem]
    stats: RunStats
