"""SQLite persistence + dedup memory.

Phase 0/1: exact dedup by stable id (url+title hash). The `embedding` column and
`find_similar` hook are stubbed for Phase 2 vector-similarity dedup (fastembed),
so we can add near-duplicate detection without a schema migration.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime

from .config import DB_PATH, STATE_DIR
from .models import EnrichedItem, RunStats

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id           TEXT PRIMARY KEY,
    source_type  TEXT NOT NULL,
    source_name  TEXT NOT NULL,
    title        TEXT NOT NULL,
    url          TEXT NOT NULL,
    published_at TEXT,
    enriched_at  TEXT NOT NULL,
    topics       TEXT NOT NULL,       -- json array
    novelty      REAL DEFAULT 0,
    impact       REAL DEFAULT 0,
    payload      TEXT NOT NULL,       -- full EnrichedItem json
    embedding    BLOB                 -- reserved for Phase 2 vector dedup
);
CREATE INDEX IF NOT EXISTS idx_items_enriched ON items(enriched_at);

CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    payload     TEXT NOT NULL
);
"""


class Store:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with closing(self._conn()) as c:
            c.executescript(SCHEMA)
            c.commit()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- Dedup -----------------------------------------------------------

    def seen_ids(self, ids: list[str]) -> set[str]:
        """Return the subset of `ids` already stored (exact dedup)."""
        if not ids:
            return set()
        placeholders = ",".join("?" * len(ids))
        with closing(self._conn()) as c:
            rows = c.execute(
                f"SELECT id FROM items WHERE id IN ({placeholders})", ids
            ).fetchall()
        return {r["id"] for r in rows}

    # --- Writes ----------------------------------------------------------

    def upsert_item(self, item: EnrichedItem, embedding: bytes | None = None) -> None:
        with closing(self._conn()) as c:
            c.execute(
                """INSERT OR REPLACE INTO items
                   (id, source_type, source_name, title, url, published_at,
                    enriched_at, topics, novelty, impact, payload, embedding)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    item.id,
                    item.source_type.value,
                    item.source_name,
                    item.title,
                    item.url,
                    item.published_at.isoformat() if item.published_at else None,
                    item.enriched_at.isoformat(),
                    json.dumps(item.topics),
                    item.novelty_score,
                    item.impact_score,
                    item.model_dump_json(),
                    embedding,
                ),
            )
            c.commit()

    def load_embeddings(self, limit: int = 5000) -> list[bytes]:
        """Return stored embedding blobs (most recent first) for dedup compare."""
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT embedding FROM items WHERE embedding IS NOT NULL "
                "ORDER BY enriched_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [r["embedding"] for r in rows]

    def save_run(self, stats: RunStats) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR REPLACE INTO runs (run_id, started_at, finished_at, payload) VALUES (?,?,?,?)",
                (
                    stats.run_id,
                    stats.started_at.isoformat(),
                    stats.finished_at.isoformat() if stats.finished_at else None,
                    stats.model_dump_json(),
                ),
            )
            c.commit()

    # --- Reads (used by the JSON exporter) -------------------------------

    def recent_items(self, limit: int = 500) -> list[EnrichedItem]:
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT payload FROM items ORDER BY enriched_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [EnrichedItem.model_validate_json(r["payload"]) for r in rows]

    def recent_runs(self, limit: int = 48) -> list[RunStats]:
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT payload FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [RunStats.model_validate_json(r["payload"]) for r in rows]
