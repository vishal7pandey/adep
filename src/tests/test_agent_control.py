"""Tests for Agent Control Endpoints [BLK-046, TS].

Tests cover:
- Pause/resume lifecycle
- Emergency stop with partial results
- Rollback to previous cycle
- SSE events for control actions
- Edge cases (already paused, already stopped, invalid rollback)
- 404 for missing runs
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.sse import SSEEventEmitter
from src.definitions.store import DefinitionStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """Create a FastAPI TestClient with a temporary store."""
    import src.definitions.store as store_module
    import src.config as config_module
    old_store = store_module._store
    old_auth = config_module.settings.auth_enabled
    store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
    config_module.settings.auth_enabled = False

    from src.api.main import create_app
    app = create_app()
    test_client = TestClient(app)

    yield test_client

    config_module.settings.auth_enabled = old_auth
    store_module._store = old_store


def _save_run(run_id: str, **overrides: Any) -> None:
    """Save a run to the test store with defaults."""
    import src.definitions.store as store_module
    data = {
        "id": run_id,
        "definition_id": "def-test",
        "document_url": "test.png",
        "status": "running",
        "current_cycle": 5,
        "total_fields": 7,
        "extracted_fields_count": 3,
        "fields": [
            {"id": "invoice_number", "name": "invoice_number", "value": "INV-001", "confidence": 0.95},
        ],
    }
    data.update(overrides)
    store_module._store.save_run(run_id, data)


class TestPauseEndpoint:
    """POST /runs/{id}/pause"""

    def test_pause_running_run(self, client: TestClient):
        _save_run("run-1", status="running")
        resp = client.post("/api/v1/runs/run-1/pause")
        assert resp.status_code == 202  # [BLK-129] cooperative pause is async
        data = resp.json()
        assert data["paused"] is True
        assert data["cycle"] == 5

    def test_pause_already_paused(self, client: TestClient):
        _save_run("run-2", status="paused")
        resp = client.post("/api/v1/runs/run-2/pause")
        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is False
        assert "already paused" in data["message"].lower()

    def test_pause_completed_run(self, client: TestClient):
        _save_run("run-3", status="completed")
        resp = client.post("/api/v1/runs/run-3/pause")
        assert resp.status_code == 200
        data = resp.json()
        assert data["paused"] is False

    def test_pause_missing_run_404(self, client: TestClient):
        resp = client.post("/api/v1/runs/nonexistent/pause")
        assert resp.status_code == 404

    def test_pause_updates_status_in_store(self, client: TestClient):
        _save_run("run-4", status="running")
        client.post("/api/v1/runs/run-4/pause")
        import src.definitions.store as store_module
        updated = store_module._store.get_run("run-4")
        assert updated["status"] == "paused"


class TestResumeEndpoint:
    """POST /runs/{id}/resume"""

    def test_resume_paused_run(self, client: TestClient):
        _save_run("run-1", status="paused")
        resp = client.post("/api/v1/runs/run-1/resume")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resumed"] is True
        assert data["cycle"] == 5

    def test_resume_running_run(self, client: TestClient):
        _save_run("run-2", status="running")
        resp = client.post("/api/v1/runs/run-2/resume")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resumed"] is False

    def test_resume_completed_run(self, client: TestClient):
        _save_run("run-3", status="completed")
        resp = client.post("/api/v1/runs/run-3/resume")
        assert resp.status_code == 200
        data = resp.json()
        assert data["resumed"] is False

    def test_resume_missing_run_404(self, client: TestClient):
        resp = client.post("/api/v1/runs/nonexistent/resume")
        assert resp.status_code == 404

    def test_resume_updates_status_in_store(self, client: TestClient):
        _save_run("run-4", status="paused")
        client.post("/api/v1/runs/run-4/resume")
        import src.definitions.store as store_module
        updated = store_module._store.get_run("run-4")
        assert updated["status"] == "running"


class TestStopEndpoint:
    """POST /runs/{id}/stop"""

    def test_stop_running_run(self, client: TestClient):
        _save_run("run-1", status="running", fields=[
            {"id": "f1", "name": "f1", "value": "v1", "confidence": 0.9},
        ])
        resp = client.post("/api/v1/runs/run-1/stop")
        assert resp.status_code == 202  # [BLK-129] cooperative cancel is async
        data = resp.json()
        assert data["cancelled"] is True
        assert data["cycle"] == 5
        assert len(data["partial_result"]) == 1

    def test_stop_paused_run(self, client: TestClient):
        _save_run("run-2", status="paused")
        resp = client.post("/api/v1/runs/run-2/stop")
        assert resp.status_code == 202  # [BLK-129]
        data = resp.json()
        assert data["cancelled"] is True

    def test_stop_already_stopped(self, client: TestClient):
        _save_run("run-3", status="cancelled")
        resp = client.post("/api/v1/runs/run-3/stop")
        assert resp.status_code == 200  # [BLK-129] no-op returns 200
        data = resp.json()
        assert data["cancelled"] is False

    def test_stop_completed_run(self, client: TestClient):
        _save_run("run-4", status="completed")
        resp = client.post("/api/v1/runs/run-4/stop")
        assert resp.status_code == 200  # [BLK-129] no-op returns 200
        data = resp.json()
        assert data["cancelled"] is False

    def test_stop_missing_run_404(self, client: TestClient):
        resp = client.post("/api/v1/runs/nonexistent/stop")
        assert resp.status_code == 404

    def test_stop_preserves_partial_results(self, client: TestClient):
        fields = [
            {"id": "f1", "name": "f1", "value": "v1", "confidence": 0.9},
            {"id": "f2", "name": "f2", "value": "v2", "confidence": 0.8},
        ]
        _save_run("run-5", status="running", fields=fields)
        resp = client.post("/api/v1/runs/run-5/stop")
        data = resp.json()
        assert len(data["partial_result"]) == 2


class TestRollbackEndpoint:
    """POST /runs/{id}/rollback"""

    def test_rollback_to_earlier_cycle(self, client: TestClient):
        _save_run("run-1", status="running", current_cycle=10)
        resp = client.post("/api/v1/runs/run-1/rollback", json={"to_cycle": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back"] is True
        assert data["from_cycle"] == 10
        assert data["to_cycle"] == 3
        assert data["attempted_preserved"] is True

    def test_rollback_to_same_cycle_fails(self, client: TestClient):
        _save_run("run-2", status="running", current_cycle=5)
        resp = client.post("/api/v1/runs/run-2/rollback", json={"to_cycle": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back"] is False

    def test_rollback_to_future_cycle_fails(self, client: TestClient):
        _save_run("run-3", status="running", current_cycle=3)
        resp = client.post("/api/v1/runs/run-3/rollback", json={"to_cycle": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back"] is False

    def test_rollback_negative_cycle_400(self, client: TestClient):
        _save_run("run-4", status="running", current_cycle=5)
        resp = client.post("/api/v1/runs/run-4/rollback", json={"to_cycle": -1})
        assert resp.status_code == 400

    def test_rollback_missing_run_404(self, client: TestClient):
        resp = client.post("/api/v1/runs/nonexistent/rollback", json={"to_cycle": 0})
        assert resp.status_code == 404

    def test_rollback_updates_store(self, client: TestClient):
        _save_run("run-5", status="running", current_cycle=8)
        client.post("/api/v1/runs/run-5/rollback", json={"to_cycle": 2})
        import src.definitions.store as store_module
        updated = store_module._store.get_run("run-5")
        assert updated["status"] == "paused"
        assert updated["rolled_back_from"] == 8
        assert updated["rolled_back_to"] == 2

    def test_rollback_to_cycle_zero(self, client: TestClient):
        _save_run("run-6", status="running", current_cycle=5)
        resp = client.post("/api/v1/runs/run-6/rollback", json={"to_cycle": 0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back"] is True
        assert data["to_cycle"] == 0


class TestPauseResumeLifecycle:
    """Full pause → resume lifecycle test."""

    def test_pause_then_resume(self, client: TestClient):
        _save_run("lifecycle-1", status="running")
        # Pause
        resp = client.post("/api/v1/runs/lifecycle-1/pause")
        assert resp.json()["paused"] is True
        # Resume
        resp = client.post("/api/v1/runs/lifecycle-1/resume")
        assert resp.json()["resumed"] is True
        # Verify store
        import src.definitions.store as store_module
        run = store_module._store.get_run("lifecycle-1")
        assert run["status"] == "running"

    def test_pause_then_stop(self, client: TestClient):
        _save_run("lifecycle-2", status="running")
        # Pause
        client.post("/api/v1/runs/lifecycle-2/pause")
        # Stop while paused
        resp = client.post("/api/v1/runs/lifecycle-2/stop")
        assert resp.json()["cancelled"] is True
        # Verify store — status is 'cancelled' [BLK-129]
        import src.definitions.store as store_module
        run = store_module._store.get_run("lifecycle-2")
        assert run["status"] == "cancelled"


class TestSSEControlEvents:
    """Tests for SSE control event emitters [BLK-046]."""

    def _collect_events(self, emitter: SSEEventEmitter) -> list[dict[str, Any]]:
        """Collect all events from an emitter."""
        emitter.close()
        loop = asyncio.new_event_loop()
        events = []
        try:
            async def collect():
                async for e in emitter.async_iter():
                    events.append(e)
            loop.run_until_complete(collect())
        finally:
            loop.close()
        return [json.loads(e.replace("data: ", "").strip()) for e in events]

    def test_emit_paused(self):
        emitter = SSEEventEmitter()
        emitter.emit_paused(cycle=5)
        events = self._collect_events(emitter)
        assert len(events) == 1
        assert events[0]["type"] == "paused"
        assert events[0]["cycle"] == 5

    def test_emit_resumed(self):
        emitter = SSEEventEmitter()
        emitter.emit_resumed(cycle=5)
        events = self._collect_events(emitter)
        assert events[0]["type"] == "resumed"
        assert events[0]["cycle"] == 5

    def test_emit_stopped(self):
        emitter = SSEEventEmitter()
        emitter.emit_stopped(cycle=3, partial_result={"field": "value"})
        events = self._collect_events(emitter)
        assert events[0]["type"] == "stopped"
        assert events[0]["cycle"] == 3
        assert events[0]["partial_result"] == {"field": "value"}

    def test_emit_stopped_no_partial(self):
        emitter = SSEEventEmitter()
        emitter.emit_stopped(cycle=3)
        events = self._collect_events(emitter)
        assert events[0]["type"] == "stopped"
        assert events[0]["partial_result"] is None

    def test_emit_rolled_back(self):
        emitter = SSEEventEmitter()
        emitter.emit_rolled_back(from_cycle=10, to_cycle=3)
        events = self._collect_events(emitter)
        assert events[0]["type"] == "rolled_back"
        assert events[0]["from_cycle"] == 10
        assert events[0]["to_cycle"] == 3


class TestCompactEndpoint:
    """POST /runs/{id}/compact [BLK-244]"""

    def test_compact_completed_run_returns_false(self, client: TestClient):
        _save_run("compact-1", status="completed", current_cycle=5)
        resp = client.post("/api/v1/runs/compact-1/compact")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compaction_triggered"] is False
        assert "already completed" in data["message"].lower()

    def test_compact_running_run_signals_executor(self, client: TestClient):
        _save_run("compact-2", status="running", current_cycle=3)
        # Reset executor singleton so we get a fresh instance
        from src.api.run_executor import reset_executor, get_executor
        reset_executor()
        executor = get_executor()

        # Manually register a run context so the executor knows about it
        from src.api.run_executor import RunContext
        ctx = RunContext("compact-2", "def-test", "test.png")
        ctx.status = "running"
        executor._runs["compact-2"] = ctx

        resp = client.post("/api/v1/runs/compact-2/compact")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compaction_triggered"] is True
        assert ctx.control.compact_requested is True

        # Cleanup
        reset_executor()

    def test_compact_missing_run_404(self, client: TestClient):
        resp = client.post("/api/v1/runs/nonexistent/compact")
        assert resp.status_code == 404

    def test_compact_run_not_in_executor_returns_false(self, client: TestClient):
        """Run exists in store but not in executor (e.g. sync run) — should return false."""
        from src.api.run_executor import reset_executor
        reset_executor()
        _save_run("compact-3", status="running", current_cycle=3)
        resp = client.post("/api/v1/runs/compact-3/compact")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compaction_triggered"] is False
        reset_executor()


class TestRollbackLiveIntegration:
    """Rollback endpoint integration with executor [BLK-244]"""

    def test_rollback_running_run_signals_executor(self, client: TestClient):
        _save_run("rb-live-1", status="running", current_cycle=10)
        from src.api.run_executor import reset_executor, get_executor, RunContext
        reset_executor()
        executor = get_executor()
        ctx = RunContext("rb-live-1", "def-test", "test.png")
        ctx.status = "running"
        executor._runs["rb-live-1"] = ctx

        resp = client.post("/api/v1/runs/rb-live-1/rollback", json={"to_cycle": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back"] is True
        assert data["live_rollback"] is True
        assert ctx.control.rollback_requested is True
        assert ctx.control.rollback_to_cycle == 3
        reset_executor()

    def test_rollback_run_not_in_executor(self, client: TestClient):
        """Run exists in store but not in executor — live_rollback should be false."""
        from src.api.run_executor import reset_executor
        reset_executor()
        _save_run("rb-live-2", status="running", current_cycle=8)
        resp = client.post("/api/v1/runs/rb-live-2/rollback", json={"to_cycle": 2})
        assert resp.status_code == 200
        data = resp.json()
        assert data["rolled_back"] is True
        assert data["live_rollback"] is False
        reset_executor()

    def test_rollback_response_has_live_rollback_field(self, client: TestClient):
        """Every rollback response should include the live_rollback field [BLK-244]."""
        from src.api.run_executor import reset_executor
        reset_executor()
        _save_run("rb-live-3", status="running", current_cycle=5)
        resp = client.post("/api/v1/runs/rb-live-3/rollback", json={"to_cycle": 1})
        data = resp.json()
        assert "live_rollback" in data
        reset_executor()


class TestRollbackStateRestoration:
    """Verify that rollback_requested is consumed and state is actually restored [SCRUM-396, SCRUM-407].

    Calls the real should_continue_with_control function — not a copy of the logic.
    A regression in the actual rollback branch will be caught by this test.
    """

    def test_rollback_consumer_restores_state(self):
        """When should_continue_with_control sees rollback_requested, it must
        truncate trace, reset total_cycles, prune extraction, and clear the flag."""
        from src.api.run_executor import RunControl
        from src.agent.graph import should_continue_with_control
        from src.agent.state import AgentState, TraceEntry, RunStatus
        from src.tools.base import FieldValue, ToolResult

        control = RunControl()
        control.request_rollback(to_cycle=2)

        # Build a minimal state with 5 cycles of trace and extraction
        trace = []
        for i in range(1, 6):
            trace.append(TraceEntry(
                step=i,
                thought=f"Step {i}",
                tool_name="ocr",
                tool_args={},
                result=ToolResult(ok=True, data=f"result-{i}"),
            ))

        extraction = {
            "field_1": FieldValue(name="field_1", value="v1", confidence=0.9, grounding=None),
            "field_2": FieldValue(name="field_2", value="v2", confidence=0.8, grounding=None),
            "field_3": FieldValue(name="field_3", value="v3", confidence=0.7, grounding=None),
        }
        # Simulate step tracking on extraction values
        extraction["field_1"]._step = 1  # type: ignore[attr-defined]
        extraction["field_2"]._step = 2  # type: ignore[attr-defined]
        extraction["field_3"]._step = 4  # type: ignore[attr-defined]

        state: AgentState = {
            "trace": trace,
            "total_cycles": 5,
            "extraction": extraction,
            "compaction_summary": "some summary",
            "status": RunStatus.PLANNING,
        }

        # Exercise the real code path [SCRUM-407]
        assert control.rollback_requested is True
        assert control.rollback_to_cycle == 2

        result = should_continue_with_control(state, control)

        # Assertions that would have caught the original bug
        assert control.rollback_requested is False, "Flag was not cleared after rollback"
        assert control.rollback_to_cycle == -1, "Cycle was not reset after rollback"
        assert state["total_cycles"] == 2, "total_cycles was not restored to rollback_to_cycle"
        assert len(state["trace"]) == 2, "Trace was not truncated to rollback_to_cycle"
        assert all(e.step <= 2 for e in state["trace"]), "Trace contains entries past rollback point"
        assert "field_3" not in state["extraction"], "Extraction was not pruned past rollback point"
        assert "field_1" in state["extraction"], "Extraction before rollback point was incorrectly pruned"
        assert "field_2" in state["extraction"], "Extraction at rollback point was incorrectly pruned"
        assert state["compaction_summary"] == "", "Compaction summary was not cleared"

    def test_rollback_with_no_control_returns_should_continue(self):
        """should_continue_with_control with no control delegates to should_continue."""
        from src.agent.graph import should_continue_with_control
        from src.agent.state import AgentState, RunStatus

        state: AgentState = {
            "trace": [],
            "total_cycles": 0,
            "extraction": {},
            "compaction_summary": "",
            "status": RunStatus.PLANNING,
        }
        result = should_continue_with_control(state, None)
        assert result in ("plan", "compact", "terminate")

    def test_cancel_requested_terminates(self):
        """should_continue_with_control returns terminate when cancel is requested."""
        from src.api.run_executor import RunControl
        from src.agent.graph import should_continue_with_control
        from src.agent.state import AgentState, RunStatus

        control = RunControl()
        control.cancel_requested = True

        state: AgentState = {
            "trace": [],
            "total_cycles": 0,
            "extraction": {},
            "compaction_summary": "",
            "status": RunStatus.PLANNING,
        }
        result = should_continue_with_control(state, control)
        assert result == "terminate"
        assert state["status"] == RunStatus.CANCELLED

    def test_compact_requested_sets_flag(self):
        """should_continue_with_control consumes compact_requested and sets _compact_requested."""
        from src.api.run_executor import RunControl
        from src.agent.graph import should_continue_with_control
        from src.agent.state import AgentState, RunStatus

        control = RunControl()
        control.compact_requested = True

        state: AgentState = {
            "trace": [],
            "total_cycles": 0,
            "extraction": {},
            "compaction_summary": "",
            "status": RunStatus.PLANNING,
        }
        result = should_continue_with_control(state, control)
        assert state.get("_compact_requested") is True
        assert control.compact_requested is False
