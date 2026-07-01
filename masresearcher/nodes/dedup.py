"""Dedup node — drops items already stored, and duplicates within this run.

Two layers:
  1. Exact dedup by stable id (url+title hash) — always on.
  2. Near-duplicate dedup by embedding cosine similarity — when OpenAI embeddings
     are available. Collapses the same paper surfaced by multiple sources
     (arXiv + HuggingFace + a blog write-up) into one item.

Embeddings for kept items are passed forward in state so persist can store them
for future runs to compare against.
"""

from __future__ import annotations

from .. import embeddings as emb
from ..config import settings
from ..state import PipelineState
from ..store import Store

# Cosine similarity at/above this is treated as the same item.
SIM_THRESHOLD = 0.90


def _embed_text(item) -> str:
    return f"{item.title}\n{item.raw_summary}".strip()


def dedup(state: PipelineState) -> PipelineState:
    raw = state.get("raw", [])
    for item in raw:
        item.finalize_id()

    # (1) In-run + cross-run exact dedup by id.
    unique: dict[str, object] = {}
    for item in raw:
        unique.setdefault(item.id, item)

    store = Store()
    already = store.seen_ids(list(unique.keys()))
    candidates = [item for item in unique.values() if item.id not in already]

    # (2) Vector near-duplicate dedup (optional).
    fresh: list = []
    emb_map: dict[str, bytes] = {}
    if emb.available() and candidates:
        try:
            vecs = emb.embed_texts([_embed_text(c) for c in candidates])
            existing = [emb.from_bytes(b) for b in store.load_embeddings()]
            kept_vecs: list = []
            for cand, vec in zip(candidates, vecs):
                against = existing + kept_vecs
                if emb.max_similarity(vec, against) >= SIM_THRESHOLD:
                    continue  # near-duplicate of a stored or already-kept item
                fresh.append(cand)
                kept_vecs.append(vec)
                emb_map[cand.id] = emb.to_bytes(vec)
        except Exception as exc:
            # Embedding failure shouldn't sink the run — fall back to exact dedup.
            stats = state.get("stats")
            if stats is not None:
                stats.errors.append(f"dedup embeddings: {type(exc).__name__}: {exc}")
            fresh = candidates
            emb_map = {}
    else:
        fresh = candidates

    stats = state.get("stats")
    if stats is not None:
        stats.fetched = len(raw)
        stats.duplicates_filtered = len(raw) - len(fresh)

    return {"fresh": fresh, "embeddings": emb_map}
