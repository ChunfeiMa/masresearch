"""Phase 0 placeholder source.

Emits a couple of synthetic RawItems so the pipeline produces visible output
before real fetchers land. Replaced by arxiv.py etc. in Phase 1+.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..models import RawItem, SourceType
from ..state import PipelineState

_DEMO = [
    RawItem(
        source_type=SourceType.ARXIV,
        source_name="demo:seed",
        title="A Vision-Language-Action Model for Generalist Humanoid Control",
        url="https://arxiv.org/abs/0000.00001",
        authors=["Placeholder et al."],
        published_at=datetime(2026, 6, 30, tzinfo=timezone.utc),
        raw_summary=(
            "We present a demo placeholder item illustrating the Physical AI topic. "
            "This is synthetic seed data used only until real sources are wired."
        ),
        topic_hints=["physical_ai"],
    ),
    RawItem(
        source_type=SourceType.WEB,
        source_name="demo:seed",
        title="Orchestrating LLM Agents: Patterns for Reliable Multi-Agent Systems",
        url="https://example.com/blog/multi-agent-patterns",
        authors=["Placeholder Blog"],
        published_at=datetime(2026, 6, 29, tzinfo=timezone.utc),
        raw_summary=(
            "A demo placeholder for the Multi-Agent Systems topic covering orchestration "
            "patterns, tool use, and coordination. Synthetic seed data."
        ),
        topic_hints=["multi_agent"],
    ),
]


def fetch_demo(state: PipelineState) -> PipelineState:
    items = [i.finalize_id() for i in _DEMO]
    return {"raw": items}
