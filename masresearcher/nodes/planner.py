"""Planner node — expands the three topics into concrete per-topic queries.

Kept deterministic (no LLM) for Phase 0 so runs are cheap and reproducible.
Phase 3 can optionally have Claude propose fresh queries based on trends.
"""

from __future__ import annotations

from ..config import TOPICS
from ..state import PipelineState


def plan(state: PipelineState) -> PipelineState:
    queries = {key: list(cfg["queries"]) for key, cfg in TOPICS.items()}
    return {"queries": queries}
