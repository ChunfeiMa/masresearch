# MASResearcher

Autonomous multi-agent research feed for **Physical AI**, **Multi-Agent Systems**, and **Vision AI**.

Every hour a LangGraph pipeline discovers new papers, blogs, solutions, and repos across those three topics, enriches each with a structured summary + concept diagram using Claude, and publishes static JSON that a hierarchical UI renders (dashboard → topic → abstract → detail). The whole thing runs on GitHub — Actions cron for the pipeline, Pages for the site — so there's no server to run.

```
GitHub Actions (hourly cron)
  └─ LangGraph:  planner → [arxiv | rss | tavily | github/hf] → dedup → summarize → classify → diagram → persist
       ├─ Claude (Opus deep / Haiku cheap) · Tavily search · LangSmith tracing
       └─ writes data/*.json + state/seen.sqlite  → `data` branch
GitHub Pages
  └─ Next.js static site reads data/*.json
```

## Status

- **Phase 0 (scaffold)** ✅ — package layout, config, schemas, SQLite store, LangGraph skeleton, JSON exporter, CI drafts.
- **Phase 1 (arXiv + LLM summaries)** ✅ — live arXiv source (category × topic-query search, lookback filtered, per-topic failures recorded to run stats) and **provider-agnostic** structured summaries (tldr → abstract → introduction → contributions → why-it-matters + tags). Works with **OpenAI** (`OPENAI_API_KEY`, e.g. `gpt-5.4-mini`) or **Anthropic** (`ANTHROPIC_API_KEY`) — whichever key is set (OpenAI wins if both). Falls back to a stub per-item when no key or on error, so runs never hard-stop.

- **Phase 2 (multi-source + vector dedup)** ✅ — three more parallel source branches: curated **RSS** blogs (feedparser), **Tavily** web search (news-scoped, needs `TAVILY_API_KEY`), and **GitHub repo search + HuggingFace daily papers** (unauthenticated). Added **near-duplicate dedup** via OpenAI `text-embedding-3-small` (cosine ≥ 0.90) so the same paper surfaced across sources collapses to one item; embeddings persist for future-run comparison. Every source records failures to run stats instead of failing the run.

- **Phase 3 (classify + diagrams)** ✅ — two more LLM agents as their own nodes: a **classifier** (assigns topics from the fixed set + novelty/impact scores 0-1 for ranking) and a **diagram agent** (emits a concise, validated Mermaid `flowchart` concept diagram per item). Per-item LLM calls run concurrently (thread pool) so the summarize → classify → diagram chain stays fast. Chain: `dedup → enrich → classify → diagram → persist`.

Roadmap: **P4** Next.js hierarchical UI (dashboard → topic → abstract → detail + Mermaid render) · **P5** enable Actions cron + Pages.

## Layout

```
masresearcher/        Python pipeline
  config.py           settings + TOPICS
  models.py           Pydantic schemas (RawItem, EnrichedItem, RunStats)
  state.py            LangGraph state
  store.py            SQLite + dedup memory
  graph.py            StateGraph assembly
  nodes/              planner, dedup, enrich, persist
  sources/            demo (P0); arxiv/rss/tavily/github_hf (P1+)
  export_json.py      SQLite → data/*.json
  run.py              entrypoint (python -m masresearcher.run)
web/                  Next.js static UI (P4)
.github/workflows/    pipeline.yml (cron), deploy.yml (Pages)
```

## Local dev

Requires Python **3.11+** (LangGraph). On macOS: `brew install python@3.11`.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env        # set OPENAI_API_KEY (or ANTHROPIC_API_KEY); Tavily/LangSmith optional
python -m masresearcher.run # writes data/*.json + state/seen.sqlite
```

Phase 0 runs with no keys (demo source, stub enrichment) so you can verify the plumbing.
