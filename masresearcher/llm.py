"""LLM-backed enrichment (provider-agnostic).

Three agents, each a structured-output call the pipeline runs as its own node:
  - summarize() : raw abstract -> hierarchical UI content (tldr..contributions)
  - classify()  : assign topics (from the fixed set) + novelty/impact scores
  - diagram()   : a concise Mermaid concept diagram

LangChain structured output validates each result and lets the model retry on
schema mismatch. The provider is chosen by which API key is set (OpenAI
preferred; Anthropic otherwise) — see config.Settings.llm_provider.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import TOPIC_KEYS, TOPICS, settings
from .models import RawItem


class SummaryResult(BaseModel):
    """Structured summary Claude must return for each item."""

    tldr: str = Field(description="One punchy sentence a busy researcher can skim.")
    abstract: str = Field(description="2-4 sentence plain-language rewrite of the abstract.")
    introduction: str = Field(
        description="A short paragraph (3-6 sentences) framing the problem and approach."
    )
    key_contributions: list[str] = Field(
        description="3-5 bullet points of concrete contributions or findings."
    )
    why_it_matters: str = Field(
        description="1-2 sentences on practical significance for Physical AI, "
        "Multi-Agent Systems, or Vision AI."
    )
    tags: list[str] = Field(description="3-6 short lowercase topical tags.")


class ClassifyResult(BaseModel):
    """Topic assignment + salience scores for ranking on the dashboard."""

    topics: list[str] = Field(
        description="Subset of the allowed topic keys this item genuinely fits."
    )
    novelty_score: float = Field(
        description="0.0-1.0: how novel/original the idea is vs prior work.", ge=0, le=1
    )
    impact_score: float = Field(
        description="0.0-1.0: likely practical impact on the field.", ge=0, le=1
    )


class DiagramResult(BaseModel):
    """A small Mermaid diagram capturing the item's core concept."""

    mermaid: str = Field(
        description="Valid Mermaid source, a `flowchart TD` with 4-8 nodes capturing "
        "the core method/pipeline. No markdown code fences."
    )


_SYSTEM = (
    "You are a research analyst curating a daily feed on Physical AI, Multi-Agent "
    "Systems, and Vision AI. Summarize the given item faithfully and concisely for a "
    "technical audience. Do not invent results not present in the text."
)

_TOPIC_MENU = "\n".join(f"  - {k}: {TOPICS[k]['label']}" for k in TOPIC_KEYS)


def _base_model() -> BaseChatModel:
    """Pick the chat model from whichever provider key is configured."""
    provider = settings.llm_provider
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        # Note: no temperature override — some GPT-5-family models only accept the
        # default. max_tokens left to the model default so reasoning isn't truncated.
        return ChatOpenAI(
            model=settings.openai_model_primary,
            api_key=settings.openai_api_key,
        )
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.model_deep,
            api_key=settings.anthropic_api_key,
            max_tokens=1200,
            temperature=0.2,
        )
    raise RuntimeError("No LLM provider key configured (OPENAI_API_KEY or ANTHROPIC_API_KEY).")


def _client(schema):
    return _base_model().with_structured_output(schema)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
def summarize(item: RawItem) -> SummaryResult:
    prompt = (
        f"Title: {item.title}\n"
        f"Source: {item.source_name}\n"
        f"Authors: {', '.join(item.authors) or 'n/a'}\n\n"
        f"Abstract / content:\n{item.raw_summary or '(no abstract provided)'}"
    )
    return _client(SummaryResult).invoke([("system", _SYSTEM), ("human", prompt)])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
def classify(title: str, text: str) -> ClassifyResult:
    prompt = (
        "Classify this item. Choose only from these topic keys "
        f"(return the key, not the label):\n{_TOPIC_MENU}\n\n"
        "Pick every topic that genuinely applies (often just one). Then score "
        "novelty and impact from 0 to 1.\n\n"
        f"Title: {title}\n\nContent:\n{text[:3000]}"
    )
    return _client(ClassifyResult).invoke([("system", _SYSTEM), ("human", prompt)])


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
def diagram(title: str, text: str, repair_error: str = "", prev: str = "") -> DiagramResult:
    prompt = (
        "Draw a concise Mermaid `flowchart TD` (4-8 nodes) that illustrates the core "
        "method, pipeline, or idea of this item so a reader grasps it at a glance. "
        "Use short node labels. Wrap any label containing spaces or punctuation in "
        'double quotes (e.g. A["Vision-Language model"]). Do not use reserved words '
        "(end, graph, class) as node ids. Output only Mermaid source, no code fences.\n\n"
        f"Title: {title}\n\nContent:\n{text[:3000]}"
    )
    if repair_error:
        prompt += (
            f"\n\nYour previous diagram was INVALID Mermaid:\n{prev}\n\n"
            f"Parser error: {repair_error}\nReturn a corrected, valid version."
        )
    return _client(DiagramResult).invoke([("system", _SYSTEM), ("human", prompt)])


def available() -> bool:
    return settings.llm_provider is not None


T = TypeVar("T")
R = TypeVar("R")


def map_parallel(fn: Callable[[T], R], items: list[T], workers: int = 8) -> list[R]:
    """Run fn over items concurrently (LLM calls are I/O-bound), preserving order."""
    if not items:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(items))) as ex:
        return list(ex.map(fn, items))
