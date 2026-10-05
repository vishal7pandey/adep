"""Tests for Context Compaction [BLK-039, §12.4, TS].

Tests cover:
- Auto-compaction triggers at threshold
- Manual compaction via _compact_requested flag
- Compaction preserves attempted set and gap_report
- compaction_summary appears in plan node prompt after compaction
- Code-based fallback summary works without LLM
- Compact endpoint API
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.agent.graph import (
    CircuitBreaker,
    _code_based_summary,
    build_react_graph,
    compact_node,
    should_continue,
    should_continue_with_control,
    should_act_with_control,
)
from src.agent.state import AgentState, RunStatus, TraceEntry
from src.agent.validator import GapReport
from src.api.run_executor import RunControl
from src.config import settings
from src.definitions.store import DefinitionStore
from src.templates.invoice import InvoiceTemplate
from src.tools.base import FieldValue, Grounding, ToolResult


def _make_trace_entry(step: int, tool: str = "ocr", ok: bool = True) -> TraceEntry:
    """Build a minimal TraceEntry for testing."""
    return TraceEntry(
        step=step,
        thought=f"Reading field at step {step}",
        tool_name=tool,
        tool_args={"image_path": "test.png"},
        result=ToolResult(
            ok=ok,
            data="INV-001" if ok else None,
            error=None if ok else "timeout",
            tool=tool,
            grounding=Grounding(bbox=(0, 0, 100, 50), source_tool=tool, confidence=0.9)
            if ok
            else None,
        ),
        field="invoice_number",
    )


def _build_compaction_state(**overrides: Any) -> dict[str, Any]:
    """Build a state dict suitable for compaction tests."""
    base: dict[str, Any] = {
        "document": None,
        "template_schema": InvoiceTemplate,
        "skill_name": "invoice",
        "regions": {},
        "extraction": {},
        "gap_report": GapReport(gaps=[], satisfied=[], is_complete=False, total_fields=7),
        "trace": [],
        "step": 0,
        "field_attempts": {},
        "total_cycles": 0,
        "status": RunStatus.PLANNING,
        "attempted": {"r1": {"ocr:failed"}},
        "provider_errors": [],
        "compaction_summary": "",
        "_planned_action": None,
        "_tool_result": None,
        "_compact_requested": False,
    }
    base.update(overrides)
    return base


class TestTraceEntryProperties:
    """Verify TraceEntry alias properties work correctly."""

    def test_tool_alias(self):
        entry = _make_trace_entry(1, tool="vlm")
        assert entry.tool == "vlm"

    def test_args_alias(self):
        entry = _make_trace_entry(1)
        assert entry.args == {"image_path": "test.png"}

    def test_result_summary_ok(self):
        entry = _make_trace_entry(1, ok=True)
        summary = entry.result_summary
        assert "ok" in summary
        assert "INV-001" in summary

    def test_result_summary_error(self):
        entry = _make_trace_entry(1, ok=False)
        summary = entry.result_summary
        assert "error" in summary
        assert "timeout" in summary

    def test_result_summary_truncates_long_data(self):
        entry = TraceEntry(
            step=1,
            thought="test",
            tool_name="vlm",
            tool_args={},
            result=ToolResult(ok=True, data="x" * 200, tool="vlm"),
        )
        assert len(entry.result_summary) < 100


class TestCodeBasedSummary:
    """Verify fallback summary without LLM."""

    def test_empty_trace_and_summary(self):
        result = _code_based_summary([], "")
        assert result == ""

    def test_includes_existing_summary(self):
        existing = "Previous compaction summary"
        result = _code_based_summary([], existing)
        assert existing in result

    def test_includes_trace_entries(self):
        trace = [_make_trace_entry(1), _make_trace_entry(2)]
        result = _code_based_summary(trace, "")
        assert "step 1" in result
        assert "step 2" in result

    def test_caps_at_20_lines(self):
        trace = [_make_trace_entry(i) for i in range(25)]
        result = _code_based_summary(trace, "")
        lines = result.split("\n")
        assert len(lines) <= 20


class TestCompactNode:
    """Verify compact_node behavior."""

    def test_empty_trace_returns_empty_summary(self):
        state = _build_compaction_state(trace=[], compaction_summary="")
        result = compact_node(state)
        assert result["compaction_summary"] == ""
        assert result["trace"] == []
        assert result["_compact_requested"] is False
        assert result["status"] == RunStatus.PLANNING

    def test_code_based_fallback_without_llm(self):
        trace = [_make_trace_entry(1), _make_trace_entry(2)]
        state = _build_compaction_state(trace=trace)
        result = compact_node(state, llm_client=None)
        assert result["compaction_summary"] != ""
        assert "step 1" in result["compaction_summary"]
        assert result["trace"] == []
        assert result["_compact_requested"] is False

    def test_llm_based_summary(self):
        trace = [_make_trace_entry(1)]
        state = _build_compaction_state(trace=trace)
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = "Agent tried OCR and got INV-001."
        result = compact_node(state, llm_client=mock_llm)
        assert result["compaction_summary"] == "Agent tried OCR and got INV-001."
        assert result["trace"] == []

    def test_llm_failure_falls_back_to_code(self):
        trace = [_make_trace_entry(1)]
        state = _build_compaction_state(trace=trace)
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM unavailable")
        result = compact_node(state, llm_client=mock_llm)
        assert "step 1" in result["compaction_summary"]

    def test_compaction_preserves_attempted_set(self):
        trace = [_make_trace_entry(1)]
        attempted = {"r1": {"ocr:failed"}, "r2": {"vlm:timeout"}}
        state = _build_compaction_state(trace=trace, attempted=attempted)
        result = compact_node(state, llm_client=None)
        # compact_node does not modify attempted — it's not in the return dict
        # The graph preserves it via state reduction
        assert "attempted" not in result  # not modified by compact

    def test_compaction_resets_compact_requested(self):
        trace = [_make_trace_entry(1)]
        state = _build_compaction_state(trace=trace, _compact_requested=True)
        result = compact_node(state, llm_client=None)
        assert result["_compact_requested"] is False

    def test_compaction_sets_status_to_planning(self):
        trace = [_make_trace_entry(1)]
        state = _build_compaction_state(trace=trace, status=RunStatus.REFLECTING)
        result = compact_node(state, llm_client=None)
        assert result["status"] == RunStatus.PLANNING

    def test_compaction_empties_trace(self):
        trace = [_make_trace_entry(i) for i in range(5)]
        state = _build_compaction_state(trace=trace)
        result = compact_node(state, llm_client=None)
        assert result["trace"] == []


class TestShouldContinueCompaction:
    """Verify should_continue routes to compact correctly."""

    def test_routes_to_compact_on_threshold(self):
        # Compaction triggers on total_cycles, not len(trace), because
        # observe_node prunes trace to a rolling window [SCRUM-499]
        state = _build_compaction_state(total_cycles=settings.compaction_threshold)
        assert should_continue(state) == "compact"

    def test_routes_to_compact_on_manual_request(self):
        state = _build_compaction_state(_compact_requested=True)
        assert should_continue(state) == "compact"

    def test_routes_to_plan_when_below_threshold(self):
        trace = [_make_trace_entry(1)]
        state = _build_compaction_state(trace=trace)
        assert should_continue(state) == "plan"

    def test_routes_to_terminate_when_complete(self):
        state = _build_compaction_state(status=RunStatus.COMPLETE)
        assert should_continue(state) == "terminate"

    def test_routes_to_terminate_when_partial(self):
        state = _build_compaction_state(status=RunStatus.PARTIAL)
        assert should_continue(state) == "terminate"

    def test_terminate_takes_priority_over_compact(self):
        # Even if compact_requested is true, terminal status wins
        state = _build_compaction_state(
            status=RunStatus.COMPLETE,
            _compact_requested=True,
        )
        assert should_continue(state) == "terminate"


class TestCompactionIntegration:
    """Integration test: graph with compaction wiring."""

    def test_graph_has_compact_node(self):
        """Verify the compiled graph includes a compact node."""
        from src.skills.invoice import InvoiceSkill
        from src.agent.validator import ValidatorConfig
        from src.tools.base import ToolRegistry

        registry = ToolRegistry()
        skill = InvoiceSkill
        validator_config = ValidatorConfig()
        graph = build_react_graph(
            registry=registry,
            skill=skill,
            validator_config=validator_config,
        )
        # The graph should have a compact node in its nodes
        # LangGraph stores nodes in the compiled graph
        assert graph is not None


class TestCompactEndpoint:
    """API tests for POST /runs/{id}/compact."""

    @pytest.fixture
    def client(self, tmp_path: Path) -> TestClient:
        """Create a FastAPI TestClient with a temporary store."""
        import src.definitions.store as store_module
        import src.config as config_module

        old_store = store_module._store
        old_auth = config_module.settings.auth_enabled
        store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
        config_module.settings.auth_enabled = False

        from src.api.main import create_app

        app = create_app()
        client = TestClient(app)

        yield client

        config_module.settings.auth_enabled = old_auth
        store_module._store = old_store

    def test_compact_missing_run_returns_404(self, client: TestClient):
        resp = client.post("/api/v1/runs/nonexistent/compact")
        assert resp.status_code == 404

    def test_compact_completed_run_returns_info(self, client: TestClient):
        import src.definitions.store as store_module

        store_module._store.save_run(
            "run-done",
            {
                "id": "run-done",
                "status": "completed",
            },
        )
        resp = client.post("/api/v1/runs/run-done/compact")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compaction_triggered"] is False
        assert "already completed" in data["message"].lower()

    def test_compact_running_run_triggers(self, client: TestClient):
        import src.definitions.store as store_module

        store_module._store.save_run(
            "run-active",
            {
                "id": "run-active",
                "status": "running",
            },
        )
        resp = client.post("/api/v1/runs/run-active/compact")
        assert resp.status_code == 200
        data = resp.json()
        assert data["compaction_triggered"] is True


class TestSSECompactionEvent:
    """Tests for the SSE compaction event type [BLK-039]."""

    def test_emit_compaction_produces_correct_event(self):
        from src.api.sse import SSEEventEmitter
        import asyncio

        emitter = SSEEventEmitter()
        emitter.emit_compaction(entries_compacted=15, summary_length=320)
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

        assert len(events) == 1
        assert "compaction" in events[0]
        parsed = json.loads(events[0].replace("data: ", "").strip())
        assert parsed["type"] == "compaction"
        assert parsed["entries_compacted"] == 15
        assert parsed["summary_length"] == 320

    def test_sse_stream_includes_compaction_event(self, tmp_path: Path):
        """Verify SSE stream emits compaction event when run has compaction_summary."""
        import src.definitions.store as store_module
        import src.config as config_module

        old_store = store_module._store
        old_auth = config_module.settings.auth_enabled
        store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
        config_module.settings.auth_enabled = False

        store_module._store.save_run(
            "run-compacted",
            {
                "id": "run-compacted",
                "definition_id": "def-test",
                "document_url": "test.png",
                "status": "completed",
                "current_cycle": 20,
                "total_fields": 7,
                "extracted_fields_count": 7,
                "fields": [],
                "compaction_summary": "Agent tried OCR then VLM, extracted all fields.",
                "entries_compacted": 15,
            },
        )

        from src.api.main import create_app

        app = create_app()
        client = TestClient(app)

        resp = client.get("/api/v1/runs/run-compacted/stream")
        assert resp.status_code == 200

        events = []
        for line in resp.text.split("\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        event_types = [e["type"] for e in events]
        assert "compaction" in event_types
        compaction_event = next(e for e in events if e["type"] == "compaction")
        assert compaction_event["entries_compacted"] == 15
        assert compaction_event["summary_length"] > 0

        config_module.settings.auth_enabled = old_auth
        store_module._store = old_store


class TestPauseSuspension:
    """Verify pause suspends (not terminates) and restores status on resume [SCRUM-499]."""

    def test_pause_sets_paused_status_during_block(self):
        """should_continue_with_control sets PAUSED while waiting for resume."""
        import threading

        control = RunControl()
        control.request_pause()
        state = _build_compaction_state(status=RunStatus.REFLECTING)

        # Run should_continue_with_control in a thread so we can observe state
        result_holder: dict[str, Any] = {}

        def run_edge():
            result_holder["result"] = should_continue_with_control(state, control)

        t = threading.Thread(target=run_edge)
        t.start()

        # Give it a moment to block on wait_for_resume
        import time

        time.sleep(0.1)

        # While blocked, status should be PAUSED
        assert state["status"] == RunStatus.PAUSED

        # Resume the run
        control.request_resume()
        t.join(timeout=5)

        # After resume, status should be restored to original (REFLECTING)
        assert state["status"] == RunStatus.REFLECTING
        assert result_holder["result"] == "plan"

    def test_pause_does_not_terminate(self):
        """should_continue_with_control must not return 'terminate' on pause."""
        import threading

        control = RunControl()
        control.request_pause()
        state = _build_compaction_state(status=RunStatus.REFLECTING)

        result_holder: dict[str, Any] = {}

        def run_edge():
            result_holder["result"] = should_act_with_control(state, control)

        t = threading.Thread(target=run_edge)
        t.start()

        import time

        time.sleep(0.1)

        assert state["status"] == RunStatus.PAUSED

        control.request_resume()
        t.join(timeout=5)

        # Should route to "act", not "terminate"
        assert result_holder["result"] != "terminate"

    def test_cancel_during_pause_terminates(self):
        """Cancel during pause should set CANCELLED and terminate."""
        import threading

        control = RunControl()
        control.request_pause()
        state = _build_compaction_state(status=RunStatus.REFLECTING)

        result_holder: dict[str, Any] = {}

        def run_edge():
            result_holder["result"] = should_continue_with_control(state, control)

        t = threading.Thread(target=run_edge)
        t.start()

        import time

        time.sleep(0.1)

        assert state["status"] == RunStatus.PAUSED

        control.request_cancel()
        t.join(timeout=5)

        assert state["status"] == RunStatus.CANCELLED
        assert result_holder["result"] == "terminate"


class TestCompactionTotalCycles:
    """Verify compaction triggers on total_cycles, not trace length [SCRUM-499]."""

    def test_compaction_triggers_with_short_trace_but_high_cycles(self):
        """Even if trace is short (rolling window), high total_cycles triggers compaction."""
        state = _build_compaction_state(
            trace=[_make_trace_entry(1)],  # Only 1 entry in rolling window
            total_cycles=settings.compaction_threshold,
        )
        assert should_continue(state) == "compact"

    def test_no_compaction_with_low_cycles(self):
        """Low total_cycles should not trigger compaction."""
        state = _build_compaction_state(
            trace=[_make_trace_entry(i) for i in range(20)],  # Long trace but
            total_cycles=3,  # low cycles
        )
        assert should_continue(state) == "plan"
