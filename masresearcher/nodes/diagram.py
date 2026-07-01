"""Diagram node — attach a concise Mermaid concept diagram to each item.

Runs last in the enrichment chain. Sanitizes the model output (strips stray code
fences) and validates it looks like a Mermaid diagram; on failure the item keeps
an empty mermaid string and the UI simply omits the diagram.
"""

from __future__ import annotations

import re

from .. import llm, mermaid_check
from ..models import EnrichedItem
from ..state import PipelineState

_FENCE = re.compile(r"^```(?:mermaid)?|```$", re.MULTILINE)
_VALID_START = ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram")


def _clean(mermaid: str) -> str:
    m = _FENCE.sub("", mermaid or "").strip()
    return m if m.startswith(_VALID_START) else ""


def _diagram_one(item: EnrichedItem, stats) -> EnrichedItem:
    try:
        res = llm.diagram(item.title, item.abstract or item.tldr)
        item.mermaid = _clean(res.mermaid)
    except Exception as exc:
        if stats is not None:
            stats.errors.append(f"diagram {item.id}: {type(exc).__name__}: {exc}")
    return item


def _repair_one(item: EnrichedItem, error: str, stats) -> EnrichedItem:
    try:
        res = llm.diagram(item.title, item.abstract or item.tldr,
                          repair_error=error, prev=item.mermaid)
        item.mermaid = _clean(res.mermaid)
    except Exception as exc:
        if stats is not None:
            stats.errors.append(f"diagram-repair {item.id}: {type(exc).__name__}: {exc}")
    return item


def diagram(state: PipelineState) -> PipelineState:
    items = state.get("enriched", [])
    if not llm.available() or not items:
        return {}
    stats = state.get("stats")
    updated = llm.map_parallel(lambda it: _diagram_one(it, stats), items)

    # Validate generated diagrams; repair invalid ones once, then drop any that
    # still don't parse so only renderable Mermaid reaches the UI. No-op when the
    # Node validator isn't installed (validate() reports everything valid).
    results = mermaid_check.validate([(e.id, e.mermaid) for e in updated if e.mermaid])
    invalid = [e for e in updated if e.mermaid and not results.get(e.id, (True, ""))[0]]
    if invalid:
        repaired = llm.map_parallel(
            lambda e: _repair_one(e, results.get(e.id, (True, ""))[1], stats), invalid
        )
        recheck = mermaid_check.validate([(e.id, e.mermaid) for e in repaired if e.mermaid])
        dropped = 0
        for e in repaired:
            if e.mermaid and not recheck.get(e.id, (True, ""))[0]:
                e.mermaid = ""
                dropped += 1
        if stats is not None:
            stats.errors.append(
                f"diagram: {len(invalid)} invalid, {len(invalid) - dropped} repaired, {dropped} dropped"
            )

    return {"enriched": updated}
