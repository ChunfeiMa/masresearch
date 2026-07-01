"""LLM-backed enrichment (provider-agnostic).

summarize() turns a RawItem's raw abstract into the structured, hierarchical
content the UI renders (tldr → abstract → introduction → contributions). It uses
LangChain structured output so we get a validated object back and let the model
retry on schema mismatch. The provider is chosen by which API key is set
(OpenAI preferred; Anthropic otherwise) — see config.Settings.llm_provider.

Classification (topics/scores) and the Mermaid diagram are Phase 3; this module
exposes just the summary for Phase 1.
"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import settings
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


_SYSTEM = (
    "You are a research analyst curating a daily feed on Physical AI, Multi-Agent "
    "Systems, and Vision AI. Summarize the given item faithfully and concisely for a "
    "technical audience. Do not invent results not present in the text."
)


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


def _client():
    return _base_model().with_structured_output(SummaryResult)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20), reraise=True)
def summarize(item: RawItem) -> SummaryResult:
    llm = _client()
    prompt = (
        f"Title: {item.title}\n"
        f"Source: {item.source_name}\n"
        f"Authors: {', '.join(item.authors) or 'n/a'}\n\n"
        f"Abstract / content:\n{item.raw_summary or '(no abstract provided)'}"
    )
    return llm.invoke([("system", _SYSTEM), ("human", prompt)])


def available() -> bool:
    return settings.llm_provider is not None
