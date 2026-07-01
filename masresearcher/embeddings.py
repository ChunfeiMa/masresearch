"""Local vector embeddings for near-duplicate dedup (Phase 2).

Uses OpenAI embeddings (text-embedding-3-small by default) when an OpenAI key is
configured. Anthropic has no embeddings API, so vector dedup is simply disabled
for that provider and the pipeline falls back to exact id dedup.
"""

from __future__ import annotations

import numpy as np

from .config import real_key, settings

_DIM_DTYPE = np.float32


def available() -> bool:
    return bool(real_key(settings.openai_api_key))


def _client():
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    """Return L2-normalized vectors so cosine similarity == dot product."""
    if not texts:
        return []
    raw = _client().embed_documents(texts)
    out = []
    for v in raw:
        arr = np.asarray(v, dtype=_DIM_DTYPE)
        norm = np.linalg.norm(arr)
        out.append(arr / norm if norm else arr)
    return out


def to_bytes(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=_DIM_DTYPE).tobytes()


def from_bytes(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=_DIM_DTYPE)


def max_similarity(vec: np.ndarray, corpus: list[np.ndarray]) -> float:
    """Highest cosine similarity between `vec` and any vector in `corpus`
    (all assumed L2-normalized)."""
    if not corpus:
        return 0.0
    mat = np.vstack(corpus)
    return float(np.max(mat @ vec))
