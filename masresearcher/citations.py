"""Fetch forward citations (papers that cite an item) from Semantic Scholar.

Google Scholar has no API and blocks scraping; Semantic Scholar is the standard
free alternative and supports arXiv-id lookup. Used server-side in the pipeline
(polite rate-limiting + optional API key) so the static UI needs no API calls.
"""

from __future__ import annotations

import re
import time

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import real_key, settings
from .models import Citation

_S2 = "https://api.semanticscholar.org/graph/v1"
_ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", re.I)
_HF_RE = re.compile(r"huggingface\.co/papers/(\d{4}\.\d{4,5})", re.I)


def arxiv_id_from_url(url: str) -> str:
    """Extract a bare arXiv id (e.g. 2401.01234) from an arXiv or HF-papers URL."""
    for rx in (_ARXIV_RE, _HF_RE):
        m = rx.search(url or "")
        if m:
            return m.group(1)
    return ""


class _Rate(Exception):
    pass


def _headers() -> dict:
    key = real_key(settings.semantic_scholar_api_key)
    return {"x-api-key": key} if key else {}


@retry(
    retry=retry_if_exception_type(_Rate),
    stop=stop_after_attempt(4),
    wait=wait_exponential(min=3, max=30),
    reraise=False,
)
def _get(path: str, params: dict) -> dict | None:
    resp = httpx.get(f"{_S2}{path}", params=params, headers=_headers(), timeout=25)
    if resp.status_code == 429:
        raise _Rate()
    if resp.status_code == 404:
        return None  # paper not indexed
    resp.raise_for_status()
    return resp.json()


def fetch_citations(arxiv_id: str, limit: int = 40) -> tuple[int | None, list[Citation]]:
    """Return (citation_count, citing_papers). count is None if the lookup fails."""
    if not arxiv_id:
        return None, []
    pid = f"arXiv:{arxiv_id}"

    try:
        meta = _get(f"/paper/{pid}", {"fields": "citationCount"})
    except Exception:
        meta = None
    if meta is None:
        return None, []
    count = meta.get("citationCount")

    citing: list[Citation] = []
    if count:
        try:
            data = _get(
                f"/paper/{pid}/citations",
                {"fields": "title,year,authors,externalIds,url", "limit": min(limit, 100)},
            )
        except Exception:
            data = None
        for row in (data or {}).get("data", []):
            cp = row.get("citingPaper") or {}
            title = (cp.get("title") or "").strip()
            if not title:
                continue
            ext = cp.get("externalIds") or {}
            citing.append(
                Citation(
                    title=title,
                    url=cp.get("url") or "",
                    year=cp.get("year"),
                    authors=[a.get("name", "") for a in (cp.get("authors") or [])][:6],
                    arxiv_id=ext.get("ArXiv") or "",
                )
            )
        time.sleep(0.3)  # be polite to the shared unauthenticated pool

    return count, citing
