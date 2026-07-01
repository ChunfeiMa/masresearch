"""Source agents — each fetches candidates and returns list[RawItem].

Phase roadmap:
  - demo.py       -> Phase 0 placeholder (a couple of synthetic items) so the
                     graph runs end-to-end with no network/keys.
  - arxiv.py      -> Phase 1 (arXiv API over TOPICS[*].arxiv_categories)
  - rss.py        -> Phase 2 (curated AI-lab blogs via feedparser)
  - tavily.py     -> Phase 2 (web search for blogs / solutions / launches)
  - github_hf.py  -> Phase 2 (GitHub Trending + HuggingFace papers/models)

Each source is wired as its own LangGraph branch and appends to state["raw"]
via the list reducer, so they run in parallel.
"""
