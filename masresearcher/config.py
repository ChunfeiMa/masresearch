"""Central configuration and topic definitions.

Settings are read from environment variables (and a local .env in dev). In the
GitHub Actions pipeline the same variables come from repo secrets.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

# Repo-root-relative paths. Data + state are committed to the `data` branch.
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STATE_DIR = ROOT / "state"
DB_PATH = STATE_DIR / "seen.sqlite"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")

    langsmith_tracing: bool = Field(default=False, alias="LANGSMITH_TRACING")
    langsmith_api_key: str = Field(default="", alias="LANGSMITH_API_KEY")
    langsmith_project: str = Field(default="masresearcher", alias="LANGSMITH_PROJECT")

    model_deep: str = Field(default="claude-opus-4-8", alias="MAS_MODEL_DEEP")
    model_fast: str = Field(default="claude-haiku-4-5-20251001", alias="MAS_MODEL_FAST")

    max_items_per_run: int = Field(default=40, alias="MAS_MAX_ITEMS_PER_RUN")
    lookback_hours: int = Field(default=24, alias="MAS_LOOKBACK_HOURS")


settings = Settings()


def wire_langsmith() -> None:
    """Export LangSmith env vars so LangGraph/LangChain auto-trace the run."""
    if not settings.langsmith_tracing or not settings.langsmith_api_key:
        return
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project


# --- Topics --------------------------------------------------------------

# Each topic drives query expansion in the planner and classification later.
# `queries` seed the source agents; `keywords` help lightweight relevance scoring.
TOPICS: dict[str, dict] = {
    "physical_ai": {
        "label": "Physical AI",
        "arxiv_categories": ["cs.RO", "cs.AI", "cs.LG"],
        "queries": [
            "physical AI",
            "embodied AI",
            "robot foundation model",
            "vision-language-action model",
            "humanoid robot learning",
        ],
        "keywords": ["robot", "embodied", "manipulation", "locomotion", "vla", "sim2real"],
    },
    "multi_agent": {
        "label": "Multi-Agent Systems",
        "arxiv_categories": ["cs.MA", "cs.AI", "cs.LG"],
        "queries": [
            "multi-agent system LLM",
            "agent orchestration",
            "multi-agent collaboration",
            "agentic workflow",
            "LLM agent tool use",
        ],
        "keywords": ["multi-agent", "orchestration", "coordination", "agentic", "tool use"],
    },
    "vision_ai": {
        "label": "Vision AI",
        "arxiv_categories": ["cs.CV", "cs.AI", "cs.LG"],
        "queries": [
            "vision language model",
            "open vocabulary detection",
            "video understanding",
            "multimodal foundation model",
            "image segmentation foundation model",
        ],
        "keywords": ["vision", "vlm", "segmentation", "detection", "multimodal", "video"],
    },
}

TOPIC_KEYS = list(TOPICS.keys())
