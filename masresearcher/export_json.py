"""Export the SQLite store to static JSON the UI reads from GitHub Pages.

Writes to data/:
  - items.json      full enriched items (L1/L2/L3 content)
  - stats.json      dashboard aggregates + recent-run trend (L0)
  - meta.json       last-updated timestamp + counts
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .config import DATA_DIR, TOPICS
from .store import Store


def export_all() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    store = Store()

    items = store.recent_items(limit=1000)
    runs = store.recent_runs(limit=48)

    items_json = [i.model_dump(mode="json") for i in items]
    _write("items.json", items_json)

    by_topic: dict[str, int] = {k: 0 for k in TOPICS}
    by_source: dict[str, int] = {}
    for i in items:
        for t in i.topics:
            by_topic[t] = by_topic.get(t, 0) + 1
        by_source[i.source_name] = by_source.get(i.source_name, 0) + 1

    stats = {
        "topics": {k: {"label": TOPICS[k]["label"], "count": by_topic.get(k, 0)} for k in TOPICS},
        "by_source": by_source,
        "total_items": len(items),
        "runs": [r.model_dump(mode="json") for r in runs],
    }
    _write("stats.json", stats)

    _write(
        "meta.json",
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "total_items": len(items),
            "topics": [TOPICS[k]["label"] for k in TOPICS],
        },
    )


def _write(name: str, payload) -> None:
    (DATA_DIR / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False))
