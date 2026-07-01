"""GitHub + HuggingFace source agent.

Two lightweight, unauthenticated fetches (best-effort, each failure recorded):
  - HuggingFace daily papers  (https://huggingface.co/api/daily_papers)
  - GitHub repository search   (recently-created repos matching topic terms)

Both return RawItems tagged with the matching topic(s).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from ..config import TOPICS, match_topics, settings
from ..models import RawItem, SourceType
from ..state import PipelineState

_HF_PAPERS = "https://huggingface.co/api/daily_papers"
_GH_SEARCH = "https://api.github.com/search/repositories"
_UA = {"User-Agent": "MASResearcher/0.1"}


def _hf_papers(cutoff: datetime, stats) -> list[RawItem]:
    items: list[RawItem] = []
    try:
        resp = httpx.get(_HF_PAPERS, headers=_UA, timeout=20)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        if stats is not None:
            stats.errors.append(f"hf_papers: {type(exc).__name__}: {exc}")
        return items

    for row in data if isinstance(data, list) else []:
        paper = row.get("paper", row)
        title = (paper.get("title") or "").strip()
        summary = (paper.get("summary") or "").strip()
        pid = paper.get("id") or ""
        if not title or not pid:
            continue
        topics = match_topics(f"{title} {summary}")
        if not topics:
            continue
        items.append(
            RawItem(
                source_type=SourceType.HUGGINGFACE,
                source_name="hf:daily_papers",
                title=title,
                url=f"https://huggingface.co/papers/{pid}",
                raw_summary=summary[:2000],
                topic_hints=topics,
            ).finalize_id()
        )
    return items


def _github_repos(cutoff: datetime, stats) -> list[RawItem]:
    items: list[RawItem] = []
    since = cutoff.date().isoformat()
    for topic_key, cfg in TOPICS.items():
        terms = " OR ".join(f'"{q}"' for q in cfg["queries"][:2])
        q = f"({terms}) created:>{since}"
        try:
            resp = httpx.get(
                _GH_SEARCH,
                headers=_UA,
                params={"q": q, "sort": "stars", "order": "desc", "per_page": 5},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            if stats is not None:
                stats.errors.append(f"github {topic_key}: {type(exc).__name__}: {exc}")
            continue

        for repo in data.get("items", []):
            name = repo.get("full_name") or ""
            url = repo.get("html_url") or ""
            if not name or not url:
                continue
            desc = repo.get("description") or ""
            items.append(
                RawItem(
                    source_type=SourceType.GITHUB,
                    source_name="github:trending",
                    title=name,
                    url=url,
                    raw_summary=f"{desc} (★{repo.get('stargazers_count', 0)})",
                    topic_hints=[topic_key],
                ).finalize_id()
            )
    return items


def fetch_github_hf(state: PipelineState) -> PipelineState:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.lookback_hours)
    stats = state.get("stats")
    items = _hf_papers(cutoff, stats) + _github_repos(cutoff, stats)
    return {"raw": items}
