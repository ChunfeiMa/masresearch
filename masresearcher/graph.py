"""LangGraph assembly.

    planner ─▶ [ source branches ] ─▶ dedup ─▶ enrich ─▶ classify ─▶ diagram ─▶ citations ─▶ persist

Source branches fan out in parallel and append to state["raw"] via the list
reducer in state.py. Phase 0 wires a single demo source; adding a real source is
just `builder.add_node(...)` + two edges (planner→src, src→dedup).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from .nodes.citations import citations
from .nodes.classify import classify
from .nodes.dedup import dedup
from .nodes.diagram import diagram
from .nodes.enrich import enrich
from .nodes.persist import persist
from .nodes.planner import plan
from .sources.arxiv import fetch_arxiv
from .sources.github_hf import fetch_github_hf
from .sources.rss import fetch_rss
from .sources.tavily import fetch_tavily
from .state import PipelineState

# Register source nodes here; each gets edges planner→node→dedup automatically.
# All fan out in parallel from the planner and append to state["raw"].
SOURCE_NODES = {
    "src_arxiv": fetch_arxiv,
    "src_rss": fetch_rss,
    "src_tavily": fetch_tavily,
    "src_github_hf": fetch_github_hf,
}


def build_graph():
    builder = StateGraph(PipelineState)

    builder.add_node("planner", plan)
    for name, fn in SOURCE_NODES.items():
        builder.add_node(name, fn)
    builder.add_node("dedup", dedup)
    builder.add_node("enrich", enrich)
    builder.add_node("classify", classify)
    builder.add_node("diagram", diagram)
    builder.add_node("citations", citations)
    builder.add_node("persist", persist)

    builder.add_edge(START, "planner")
    for name in SOURCE_NODES:
        builder.add_edge("planner", name)
        builder.add_edge(name, "dedup")
    builder.add_edge("dedup", "enrich")
    builder.add_edge("enrich", "classify")
    builder.add_edge("classify", "diagram")
    builder.add_edge("diagram", "citations")
    builder.add_edge("citations", "persist")
    builder.add_edge("persist", END)

    return builder.compile()
