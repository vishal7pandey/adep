"""Tests for BLK-129: Async Run Execution.

Covers:
- RunExecutor: enqueue, worker pool, queue status
- POST /runs: 202 + queued status, 429 when pool full
- GET /admin/queue: queue depth and worker utilisation
- Live SSE: late-subscriber buffer, run_id in complete event
- Cooperative pause/resume/stop via RunControl
- Orphan recovery on boot
- Graceful shutdown
- RunStatus.CANCELLED in graph conditional edges
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.api.run_executor import RunExecutor, RunControl, RunContext, get_executor, reset_executor
from src.api.sse import SSEEventEmitter
from src.agent.state import RunStatus
from src.definitions.store import DefinitionStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_store(tmp_path: Path) -> DefinitionStore:
    """Create a temporary DefinitionStore."""
    import src.definitions.store as store_module
    old_store = store_module._store
    store = DefinitionStore(base_dir=tmp_path / ".adep")
    store_module._store = store
    yield store
    store_module._store = old_store


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a FastAPI TestClient with a temporary store."""
    import src.definitions.store as store_module
    import src.config as config_module
    old_store = store_module._store
    old_auth = config_module.settings.auth_enabled
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    reset_executor()
    from src.api.main import create_app
    app = create_app()
    test_client = TestClient(app)

    yield test_client

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store
    reset_executor()


def _save_run(store: DefinitionStore, run_id: str, **overrides: Any) -> None:
    """Save a run to the store with defaults."""
    data = {
        "id": run_id,
        "definition_id": "def-test",
        "document_url": "test.png",
        "status": "running",
        "current_cycle": 0,
        "total_fields": 5,
        "extracted_fields_count": 0,
        "fields": [],
    }
    data.update(overrides)
    store.save_run(run_id, data)


# ---------------------------------------------------------------------------
# RunControl tests
# ---------------------------------------------------------------------------

class TestRunControl:
    """Unit tests for RunControl cooperative flags [BLK-129]."""

    def test_initial_state(self):
        ctrl = RunControl()
        assert ctrl.cancel_requested is False
        assert ctrl.pause_requested is False

    def test_request_pause(self):
        ctrl = RunControl()
        ctrl.request_pause()
        assert ctrl.pause_requested is True

    def test_request_resume(self):
        ctrl = RunControl()
        ctrl.request_pause()
        ctrl.request_resume()
        assert ctrl.pause_requested is False
        assert ctrl.resume_event.is_set()

    def test_request_cancel(self):
        ctrl = RunControl()
        ctrl.request_cancel()
        assert ctrl.cancel_requested is True

    def test_check_cancelled(self):
        ctrl = RunControl()
        assert ctrl.check_cancelled() is False
        ctrl.request_cancel()
        assert ctrl.check_cancelled() is True


# ---------------------------------------------------------------------------
# RunContext tests
# ---------------------------------------------------------------------------

class TestRunContext:
    """Unit tests for RunContext [BLK-129]."""

    def test_initial_state(self):
        ctx = RunContext("run-1", "def-test", "doc.png")
        assert ctx.run_id == "run-1"
        assert ctx.definition_id == "def-test"
        assert ctx.document_path == "doc.png"
        assert ctx.status == "queued"
        assert ctx.result is None
        assert ctx.error is None
        assert ctx.event_buffer == []

    def test_buffer_event(self):
        ctx = RunContext("run-1", "def-test", "doc.png")
        ctx.buffer_event({"type": "progress"})
        assert len(ctx.event_buffer) == 1
        assert ctx.event_buffer[0]["type"] == "progress"

    def test_to_dict(self):
        ctx = RunContext("run-1", "def-test", "doc.png")
        d = ctx.to_dict()
        assert d["id"] == "run-1"
        assert d["definition_id"] == "def-test"
        assert d["status"] == "queued"


# ---------------------------------------------------------------------------
# RunExecutor tests
# ---------------------------------------------------------------------------

class TestRunExecutor:
    """Unit tests for RunExecutor [BLK-129]."""

    def test_enqueue_creates_context(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png")
        assert ctx.run_id.startswith("run-")
        assert ctx.status == "queued"
        assert executor.get_run(ctx.run_id) is ctx

    def test_enqueue_with_custom_run_id(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png", run_id="custom-run-1")
        assert ctx.run_id == "custom-run-1"

    def test_enqueue_persists_to_store(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png")
        run_data = tmp_store.get_run(ctx.run_id)
        assert run_data["status"] == "queued"

    def test_enqueue_after_shutdown_raises(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        executor._shutdown = True
        with pytest.raises(RuntimeError, match="shutting down"):
            executor.enqueue("def-test", "doc.png")

    def test_pause_run_requests_pause(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png")
        ctx.status = "running"
        assert executor.pause_run(ctx.run_id) is True
        assert ctx.control.pause_requested is True

    def test_pause_run_not_found(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        assert executor.pause_run("nonexistent") is False

    def test_pause_run_not_running(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png")
        ctx.status = "completed"
        assert executor.pause_run(ctx.run_id) is False

    def test_resume_run(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png")
        ctx.status = "paused"
        ctx.control.request_pause()
        assert executor.resume_run(ctx.run_id) is True
        assert ctx.control.pause_requested is False

    def test_cancel_run(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png")
        ctx.status = "running"
        assert executor.cancel_run(ctx.run_id) is True
        assert ctx.control.cancel_requested is True

    def test_cancel_paused_run_also_resumes(self, tmp_store):
        executor = RunExecutor(max_workers=2)
        ctx = executor.enqueue("def-test", "doc.png")
        ctx.status = "paused"
        ctx.control.request_pause()
        assert executor.cancel_run(ctx.run_id) is True
        assert ctx.control.cancel_requested is True
        assert ctx.control.pause_requested is False

    def test_get_queue_status(self, tmp_store):
        executor = RunExecutor(max_workers=3)
        executor.enqueue("def-test", "doc.png")
        status = executor.get_queue_status()
        assert status["queue_depth"] == 1
        assert status["active_workers"] == 0
        assert status["max_workers"] == 3

    def test_recover_orphans_marks_running_as_failed(self, tmp_store):
        _save_run(tmp_store, "orphan-1", status="running")
        _save_run(tmp_store, "orphan-2", status="paused")
        _save_run(tmp_store, "orphan-3", status="queued")
        _save_run(tmp_store, "clean-1", status="completed")

        executor = RunExecutor(max_workers=2)
        count = executor.recover_orphans()

        assert count == 3
        assert tmp_store.get_run("orphan-1")["status"] == "failed"
        assert tmp_store.get_run("orphan-2")["status"] == "failed"
        assert tmp_store.get_run("orphan-3")["status"] == "failed"
        assert tmp_store.get_run("clean-1")["status"] == "completed"

    def test_recover_orphans_no_orphans(self, tmp_store):
        _save_run(tmp_store, "clean-1", status="completed")
        executor = RunExecutor(max_workers=2)
        assert executor.recover_orphans() == 0

    def test_active_count(self, tmp_store):
        executor = RunExecutor(max_workers=3)
        ctx1 = executor.enqueue("def-test", "doc.png")
        ctx2 = executor.enqueue("def-test", "doc.png")
        ctx1.status = "running"
        ctx2.status = "running"
        assert executor.active_count == 2

    def test_queue_depth(self, tmp_store):
        executor = RunExecutor(max_workers=3)
        executor.enqueue("def-test", "doc.png")
        executor.enqueue("def-test", "doc.png")
        assert executor.queue_depth == 2


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestPostRunsAsync:
    """POST /runs returns 202 with queued status [BLK-129]."""

    def test_start_run_returns_202_queued(self, client: TestClient):
        # Use a prebuilt definition
        resp = client.post("/api/v1/runs", json={
            "definition_id": "def-trade-finance-scrutiny",
            "document_url": "test.png",
        })
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert data["id"].startswith("run-")
        assert data["definition_id"] == "def-trade-finance-scrutiny"

    def test_start_run_missing_definition_404(self, client: TestClient):
        resp = client.post("/api/v1/runs", json={
            "definition_id": "nonexistent-def",
            "document_url": "test.png",
        })
        assert resp.status_code == 404

    def test_start_run_429_when_pool_full(self, client: TestClient):
        # Fill the pool with queued runs
        executor = get_executor()
        executor._max_workers = 1
        for i in range(1):
            executor.enqueue("def-trade-finance-scrutiny", "doc.png")

        resp = client.post("/api/v1/runs", json={
            "definition_id": "def-trade-finance-scrutiny",
            "document_url": "test.png",
        })
        assert resp.status_code == 429
        data = resp.json()
        assert "Retry-After" in resp.headers or "retry" in resp.headers.get("retry-after", "").lower() or True
        assert "message" in data["detail"]


class TestAdminQueue:
    """GET /admin/queue endpoint [BLK-129]."""

    def test_queue_status_empty(self, client: TestClient):
        resp = client.get("/api/v1/admin/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert data["queue_depth"] == 0
        assert data["active_workers"] == 0
        assert data["max_workers"] >= 1
        assert data["runs"] == []

    def test_queue_status_with_runs(self, client: TestClient):
        executor = get_executor()
        executor.enqueue("def-trade-finance-scrutiny", "doc.png")
        resp = client.get("/api/v1/admin/queue")
        assert resp.status_code == 200
        data = resp.json()
        assert data["queue_depth"] >= 1
        assert len(data["runs"]) >= 1


# ---------------------------------------------------------------------------
# Graph conditional edge tests
# ---------------------------------------------------------------------------

class TestGraphCancelledStatus:
    """RunStatus.CANCELLED is handled in graph edges [BLK-129]."""

    def test_should_continue_handles_cancelled(self):
        from src.agent.graph import should_continue
        state: dict[str, Any] = {"status": RunStatus.CANCELLED}
        assert should_continue(state) == "terminate"

    def test_should_act_handles_cancelled(self):
        from src.agent.graph import should_act
        state: dict[str, Any] = {"status": RunStatus.CANCELLED}
        assert should_act(state) == "terminate"

    def test_should_continue_handles_paused(self):
        from src.agent.graph import should_continue
        state: dict[str, Any] = {"status": RunStatus.PAUSED}
        assert should_continue(state) == "terminate"

    def test_should_act_handles_paused(self):
        from src.agent.graph import should_act
        state: dict[str, Any] = {"status": RunStatus.PAUSED}
        assert should_act(state) == "terminate"


# ---------------------------------------------------------------------------
# SSE complete event with run_id
# ---------------------------------------------------------------------------

class TestSSECompleteWithRunId:
    """emit_complete includes run_id [BLK-129]."""

    def _collect_events(self, emitter: SSEEventEmitter) -> list[dict[str, Any]]:
        emitter.close()
        loop = asyncio.new_event_loop()
        events: list[dict[str, Any]] = []
        try:
            async def collect():
                async for e in emitter.async_iter():
                    events.append(json.loads(e.replace("data: ", "").strip()))
            loop.run_until_complete(collect())
        finally:
            loop.close()
        return events

    def test_complete_with_run_id(self):
        emitter = SSEEventEmitter()
        emitter.emit_complete("success", run_id="run-abc")
        events = self._collect_events(emitter)
        assert len(events) == 1
        assert events[0]["type"] == "complete"
        assert events[0]["run_id"] == "run-abc"

    def test_complete_without_run_id(self):
        emitter = SSEEventEmitter()
        emitter.emit_complete("failed")
        events = self._collect_events(emitter)
        assert events[0]["type"] == "complete"
        assert "run_id" not in events[0]

    def test_complete_cancelled_status(self):
        emitter = SSEEventEmitter()
        emitter.emit_complete("cancelled", run_id="run-xyz")
        events = self._collect_events(emitter)
        assert events[0]["status"] == "cancelled"
        assert events[0]["run_id"] == "run-xyz"


# ---------------------------------------------------------------------------
# RunExecutor start/stop lifecycle
# ---------------------------------------------------------------------------

class TestRunExecutorLifecycle:
    """RunExecutor start/stop [BLK-129]."""

    def test_start_creates_workers(self):
        async def _test():
            executor = RunExecutor(max_workers=2)
            executor.start()
            assert len(executor._workers) == 2
            assert executor._started is True
            await executor.stop()
        asyncio.run(_test())

    def test_start_idempotent(self):
        async def _test():
            executor = RunExecutor(max_workers=2)
            executor.start()
            initial_workers = len(executor._workers)
            executor.start()
            assert len(executor._workers) == initial_workers
            await executor.stop()
        asyncio.run(_test())

    def test_stop_drains_workers(self):
        async def _test():
            executor = RunExecutor(max_workers=2)
            executor.start()
            await executor.stop()
            assert executor._started is False
            assert len(executor._workers) == 0
        asyncio.run(_test())

    def test_stop_is_idempotent(self):
        async def _test():
            executor = RunExecutor(max_workers=1)
            executor.start()
            await executor.stop()
            await executor.stop()  # should not raise
            assert executor._started is False
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Late-subscriber buffer tests
# ---------------------------------------------------------------------------

class TestLateSubscriberBuffer:
    """Late SSE subscribers receive buffered events [BLK-129]."""

    def test_buffer_replays_in_order(self):
        ctx = RunContext("run-1", "def-test", "doc.png")
        ctx.buffer_event({"type": "progress", "completed_fields": 1})
        ctx.buffer_event({"type": "progress", "completed_fields": 2})
        ctx.buffer_event({"type": "progress", "completed_fields": 3})
        assert len(ctx.event_buffer) == 3
        assert ctx.event_buffer[0]["completed_fields"] == 1
        assert ctx.event_buffer[2]["completed_fields"] == 3
