"""Pipeline entrypoint — invoked locally and by the GitHub Actions cron.

    python -m masresearcher.run
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

from .config import wire_langsmith
from .export_json import export_all
from .graph import build_graph
from .models import RunStats
from .store import Store


def _run_id() -> str:
    # Timestamp-based; avoids random ids so runs sort chronologically.
    return datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")


def main() -> int:
    wire_langsmith()

    started = datetime.now(timezone.utc)
    stats = RunStats(run_id=_run_id(), started_at=started)

    graph = build_graph()
    graph.invoke({"run_id": stats.run_id, "stats": stats})

    stats.finished_at = datetime.now(timezone.utc)
    Store().save_run(stats)

    export_all()

    print(
        f"[{stats.run_id}] fetched={stats.fetched} "
        f"new={stats.enriched} dupes={stats.duplicates_filtered} "
        f"topics={stats.by_topic}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
