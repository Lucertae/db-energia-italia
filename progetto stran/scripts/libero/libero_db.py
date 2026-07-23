"""SQLite store for OPS DESK libero series (ciccio tailnet)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS series_meta (
    id TEXT PRIMARY KEY,
    label TEXT,
    source TEXT,
    unit TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS series_daily (
    id TEXT NOT NULL,
    ymd INTEGER NOT NULL,
    val REAL NOT NULL,
    PRIMARY KEY (id, ymd)
);
CREATE INDEX IF NOT EXISTS idx_series_daily_id ON series_daily(id);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    return conn


def upsert_series(conn: sqlite3.Connection, sid: str, label: str, source: str,
                  unit: str, rows: list[tuple[int, float]]) -> int:
    if not rows:
        return 0
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        "INSERT OR REPLACE INTO series_meta(id,label,source,unit,updated_at) VALUES(?,?,?,?,?)",
        (sid, label, source, unit, now),
    )
    conn.executemany(
        "INSERT OR REPLACE INTO series_daily(id,ymd,val) VALUES(?,?,?)",
        [(sid, ymd, val) for ymd, val in rows],
    )
    conn.commit()
    return len(rows)
