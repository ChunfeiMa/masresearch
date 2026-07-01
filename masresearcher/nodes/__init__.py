"""LangGraph nodes.

Phase 0 ships the planner (real) plus pass-through stubs for the enrichment
nodes so the graph compiles and runs end-to-end. Phases 1-3 replace the stubs:
  - sources/*      -> real fetchers (arXiv done in P1)
  - dedup          -> exact now, vector-similarity in P2
  - summarize      -> Claude structured summary (P1/P3)
  - classify       -> topics/tags/scores (P3)
  - diagram        -> Mermaid concept diagram (P3)
"""
