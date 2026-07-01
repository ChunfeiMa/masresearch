"""Citations node — attach forward citations to paper items.

For items that map to an arXiv id (arXiv or HuggingFace-papers sources), look up
who cites them via Semantic Scholar. Processed with low concurrency to respect
the shared rate limit. Non-paper items (web/RSS/GitHub) are left untouched.
"""

from __future__ import annotations

from .. import citations as cite
from .. import llm
from ..models import EnrichedItem
from ..state import PipelineState


def _citations_one(item: EnrichedItem, stats) -> EnrichedItem:
    arxiv_id = cite.arxiv_id_from_url(item.url)
    if not arxiv_id:
        return item  # not a paper we can resolve
    item.arxiv_id = arxiv_id
    try:
        count, citing = cite.fetch_citations(arxiv_id)
        item.citation_count = count
        item.citations = citing
    except Exception as exc:
        if stats is not None:
            stats.errors.append(f"citations {item.id}: {type(exc).__name__}: {exc}")
    return item


def citations(state: PipelineState) -> PipelineState:
    items = state.get("enriched", [])
    if not items:
        return {}
    stats = state.get("stats")
    # workers=2 keeps us gentle on the unauthenticated Semantic Scholar pool.
    updated = llm.map_parallel(lambda it: _citations_one(it, stats), items, workers=2)
    return {"enriched": updated}
