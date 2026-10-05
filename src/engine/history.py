"""Run history store for the new engine (ADE-37): a durable per-run record, no global lock.

Ported from ade2's src/ade2/history.py (read in full as part of ADE-30), with one deliberate
change: there is no module-level threading.Lock. ade2 wrapped every synchronous sqlite3 call in
one shared lock, which the async wrappers only offloaded via asyncio.to_thread rather than
removed — so concurrent runs still had every DB write serialized against each other. Here, each
call opens and closes its own short-lived connection; SQLite's own file-level locking is what
actually protects concurrent writers, same as ade2 ultimately relied on anyway.

init_db() is NOT called at import time (ade2 called it at module load, which touches disk just
from importing the module). Callers run it explicitly once at startup.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Sibling to ade's existing DocumentStore DB (src/config.py: store_db_path = ".adep/store.db") —
# a deliberately separate file; this module never touches that existing store.
DEFAULT_DB_PATH = Path(".adep/engine_history.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    filename TEXT,
    skill_id TEXT,
    mode TEXT,
    page_count INTEGER,
    status TEXT DEFAULT 'running',
    answer TEXT,
    num_turns INTEGER,
    total_cost_usd REAL,
    error TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    step INTEGER,
    data TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);
"""


def _resolve(db_path: Path | str | None) -> Path:
    return Path(db_path) if db_path is not None else DEFAULT_DB_PATH


def _get_conn(db_path: Path | str | None = None) -> sqlite3.Connection:
    path = _resolve(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path | str | None = None) -> None:
    """Create the tables if they don't exist yet. Safe to call more than once."""
    conn = _get_conn(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def start_run(
    run_id: str,
    document_id: str,
    filename: str = "",
    skill_id: str = "",
    mode: str = "extraction",
    page_count: int = 1,
    db_path: Path | str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    logger.info(
        "Run started: run_id=%s, doc_id=%s, skill=%s, mode=%s", run_id, document_id, skill_id, mode
    )
    conn = _get_conn(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO runs "
            "(run_id, document_id, filename, skill_id, mode, page_count, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'running', ?)",
            (run_id, document_id, filename, skill_id, mode, page_count, ts),
        )
        conn.commit()
    finally:
        conn.close()


def record_event(
    run_id: str,
    event_type: str,
    data: dict,
    step: int | None = None,
    db_path: Path | str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    conn = _get_conn(db_path)
    try:
        conn.execute(
            "INSERT INTO events (run_id, event_type, step, data, timestamp) VALUES (?, ?, ?, ?, ?)",
            (run_id, event_type, step, json.dumps(data, default=str), ts),
        )
        conn.commit()
    finally:
        conn.close()


def complete_run(
    run_id: str,
    answer: str = "",
    num_turns: int = 0,
    total_cost_usd: float | None = None,
    db_path: Path | str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    logger.info("Run completed: run_id=%s, turns=%d, cost=%s", run_id, num_turns, total_cost_usd)
    conn = _get_conn(db_path)
    try:
        conn.execute(
            "UPDATE runs SET status='completed', answer=?, num_turns=?, total_cost_usd=?, "
            "completed_at=? WHERE run_id=?",
            (answer, num_turns, total_cost_usd, ts, run_id),
        )
        conn.commit()
    finally:
        conn.close()


def error_run(run_id: str, error: str, db_path: Path | str | None = None) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    logger.error("Run failed: run_id=%s, error=%s", run_id, error)
    conn = _get_conn(db_path)
    try:
        conn.execute(
            "UPDATE runs SET status='error', error=?, completed_at=? WHERE run_id=?",
            (error, ts, run_id),
        )
        conn.commit()
    finally:
        conn.close()


def list_runs(limit: int = 50, db_path: Path | str | None = None) -> list[dict]:
    conn = _get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT run_id, document_id, filename, skill_id, mode, page_count, status, num_turns, "
            "total_cost_usd, error, created_at, completed_at FROM runs "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_run(run_id: str, db_path: Path | str | None = None) -> dict | None:
    conn = _get_conn(db_path)
    try:
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_run_events(run_id: str, db_path: Path | str | None = None) -> list[dict]:
    conn = _get_conn(db_path)
    try:
        rows = conn.execute(
            "SELECT event_type, step, data, timestamp FROM events WHERE run_id=? ORDER BY id ASC",
            (run_id,),
        ).fetchall()
        return [
            {
                "event_type": r["event_type"],
                "step": r["step"],
                "data": json.loads(r["data"]),
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]
    finally:
        conn.close()


# --- Async wrappers ------------------------------------------------------------------------------
# Run the synchronous functions in a thread via asyncio.to_thread so they don't block the event
# loop when called from async FastAPI/agent code. No shared lock: each call's own short-lived
# connection is independent, so concurrent calls can proceed without serializing on each other
# beyond whatever SQLite's own file locking requires.


async def async_start_run(
    run_id: str,
    document_id: str,
    filename: str = "",
    skill_id: str = "",
    mode: str = "extraction",
    page_count: int = 1,
    db_path: Path | str | None = None,
) -> None:
    await asyncio.to_thread(
        start_run, run_id, document_id, filename, skill_id, mode, page_count, db_path
    )


async def async_record_event(
    run_id: str,
    event_type: str,
    data: dict,
    step: int | None = None,
    db_path: Path | str | None = None,
) -> None:
    await asyncio.to_thread(record_event, run_id, event_type, data, step, db_path)


async def async_complete_run(
    run_id: str,
    answer: str = "",
    num_turns: int = 0,
    total_cost_usd: float | None = None,
    db_path: Path | str | None = None,
) -> None:
    await asyncio.to_thread(complete_run, run_id, answer, num_turns, total_cost_usd, db_path)


async def async_error_run(run_id: str, error: str, db_path: Path | str | None = None) -> None:
    await asyncio.to_thread(error_run, run_id, error, db_path)


async def async_list_runs(limit: int = 50, db_path: Path | str | None = None) -> list[dict]:
    return await asyncio.to_thread(list_runs, limit, db_path)


async def async_get_run(run_id: str, db_path: Path | str | None = None) -> dict | None:
    return await asyncio.to_thread(get_run, run_id, db_path)


async def async_get_run_events(run_id: str, db_path: Path | str | None = None) -> list[dict]:
    return await asyncio.to_thread(get_run_events, run_id, db_path)
