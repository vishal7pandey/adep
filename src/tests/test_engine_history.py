"""Tests for the new-engine run history store (ADE-37): SQLite-backed, no global lock.

Every test uses a real temp SQLite file under tmp_path (db_path is an explicit parameter,
no monkeypatching needed) — never the real .adep/ history DB.
"""

from __future__ import annotations

import asyncio

import pytest

from src.engine import history


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "history.db"
    history.init_db(path)
    return path


# --- AC1 ---------------------------------------------------------------------------------------


def test_init_db_creates_tables_and_is_idempotent(tmp_path):
    path = tmp_path / "fresh.db"
    history.init_db(path)

    conn = history._get_conn(path)
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    conn.close()
    assert {"runs", "events"} <= tables

    history.init_db(path)  # no-op, must not raise


# --- AC2 ---------------------------------------------------------------------------------------


def test_full_run_lifecycle_records_events_in_order(db_path):
    history.start_run(
        "run-1",
        "doc-1",
        filename="plant.pdf",
        skill_id="pid",
        mode="extraction",
        page_count=2,
        db_path=db_path,
    )
    history.record_event("run-1", "agent.thought", {"text": "planning"}, step=1, db_path=db_path)
    history.record_event("run-1", "tool.call", {"tool": "survey_layout"}, step=2, db_path=db_path)
    history.record_event("run-1", "tool.result", {"tool": "survey_layout"}, step=3, db_path=db_path)
    history.complete_run("run-1", answer="done", num_turns=3, total_cost_usd=0.1, db_path=db_path)

    run = history.get_run("run-1", db_path=db_path)
    assert run["status"] == "completed"
    assert run["answer"] == "done"
    assert run["num_turns"] == 3
    assert run["total_cost_usd"] == 0.1

    events = history.get_run_events("run-1", db_path=db_path)
    assert [e["event_type"] for e in events] == ["agent.thought", "tool.call", "tool.result"]
    assert [e["step"] for e in events] == [1, 2, 3]


def test_get_run_and_events_on_nonexistent_run_id(db_path):
    assert history.get_run("no-such-run", db_path=db_path) is None
    assert history.get_run_events("no-such-run", db_path=db_path) == []


# --- AC3 ---------------------------------------------------------------------------------------


def test_error_run_sets_status_and_message(db_path):
    history.start_run("run-err", "doc-1", db_path=db_path)
    history.error_run("run-err", "VLM call failed: timeout", db_path=db_path)

    run = history.get_run("run-err", db_path=db_path)
    assert run["status"] == "error"
    assert run["error"] == "VLM call failed: timeout"
    assert run["completed_at"] is not None


# --- AC4 ---------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_wrappers_match_sync_results(db_path):
    await history.async_start_run("run-async", "doc-2", filename="x.pdf", db_path=db_path)
    await history.async_record_event("run-async", "tool.call", {"tool": "ocr"}, 1, db_path=db_path)
    await history.async_complete_run("run-async", answer="ok", num_turns=1, db_path=db_path)

    sync_run = history.get_run("run-async", db_path=db_path)
    async_run = await history.async_get_run("run-async", db_path=db_path)
    assert sync_run == async_run

    sync_events = history.get_run_events("run-async", db_path=db_path)
    async_events = await history.async_get_run_events("run-async", db_path=db_path)
    assert sync_events == async_events

    all_runs = await history.async_list_runs(db_path=db_path)
    assert any(r["run_id"] == "run-async" for r in all_runs)


# --- AC5 ---------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_async_writes_do_not_lose_data(db_path):
    async def one_run(i: int) -> None:
        run_id = f"concurrent-run-{i}"
        await history.async_start_run(run_id, f"doc-{i}", db_path=db_path)
        await history.async_record_event(run_id, "tool.call", {"n": i}, 1, db_path=db_path)
        await history.async_complete_run(run_id, answer=f"result-{i}", num_turns=1, db_path=db_path)

    await asyncio.gather(*(one_run(i) for i in range(10)))

    for i in range(10):
        run = history.get_run(f"concurrent-run-{i}", db_path=db_path)
        assert run is not None
        assert run["status"] == "completed"
        assert run["answer"] == f"result-{i}"
        events = history.get_run_events(f"concurrent-run-{i}", db_path=db_path)
        assert len(events) == 1
        assert events[0]["data"]["n"] == i


# --- AC6: no shared lock anywhere in the module -------------------------------------------------


def test_module_defines_no_shared_lock():
    lock_instances = [
        name for name in vars(history) if "lock" in type(getattr(history, name)).__name__.lower()
    ]
    assert lock_instances == [], f"found lock-like module attributes: {lock_instances}"
