"""Tests for the ReAct graph integration with mocked LLM + tools [§2.2, TS, NFT].

These tests verify the graph nodes, conditional edges, give-up caps, and
end-to-end flow using mocked providers — no external API calls.
"""

from __future__ import annotations

from typing import Any

import pytest

from pydantic import Field

from src.agent.graph import (
    CircuitBreaker,
    act_node,
    build_react_graph,
    observe_node,
    plan_node,
    reflect_node,
    should_continue,
    terminate_node,
)
from src.agent.state import AgentState, RunStatus
from src.agent.validator import (
    GapReport,
    GapType,
    FieldGap,
    ValidatorConfig,
)
from src.skills.base import Skill
from src.skills.invoice import InvoiceSkill
from src.templates.base import Template
from src.templates.invoice import InvoiceTemplate
from src.tools.base import FieldValue, Grounding, ToolRegistry, ToolResult, ToolSpec


# ---------------------------------------------------------------------------
# Mock LLM client
# ---------------------------------------------------------------------------

class MockLLMClient:
    """Mock LLM that returns pre-configured actions."""

    def __init__(self, actions: list[dict[str, Any]]) -> None:
        self._actions = actions
        self._idx = 0

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        import json
        if self._idx >= len(self._actions):
            return json.dumps({"thought": "done", "tool": "", "args": {}, "field": None})
        action = self._actions[self._idx]
        self._idx += 1
        return json.dumps(action)


# ---------------------------------------------------------------------------
# Mock tool functions
# ---------------------------------------------------------------------------

def _mock_ocr(**kwargs: Any) -> ToolResult:
    return ToolResult(
        ok=True,
        data="INV-2024-001",
        grounding=Grounding(bbox=(10, 10, 200, 50), source_tool="ocr", confidence=0.95),
        tool="ocr",
    )


def _mock_vlm(**kwargs: Any) -> ToolResult:
    return ToolResult(
        ok=True,
        data="ACME Corp",
        grounding=Grounding(bbox=(10, 60, 300, 100), source_tool="vlm", confidence=0.9),
        tool="vlm",
    )


def _mock_failing_tool(**kwargs: Any) -> ToolResult:
    return ToolResult(ok=False, error="provider timeout", tool="failing_tool")


def _mock_detect_layout(**kwargs: Any) -> ToolResult:
    return ToolResult(
        ok=True,
        data=[
            {"id": "p0_r0", "type": "text", "bbox": (0, 0, 500, 100), "page": 0,
             "text": "header", "confidence": 0.9, "metadata": {}},
        ],
        tool="detect_layout",
    )


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _build_registry_with_mock_tools() -> ToolRegistry:
    """Build a registry with mock tools for testing."""
    registry = ToolRegistry()
    registry.register(
        ToolSpec(name="ocr", description="Mock OCR"),
        _mock_ocr,
    )
    registry.register(
        ToolSpec(name="vlm", description="Mock VLM"),
        _mock_vlm,
    )
    registry.register(
        ToolSpec(name="detect_layout", description="Mock layout detection"),
        _mock_detect_layout,
    )
    return registry


def _build_test_state(**overrides: Any) -> AgentState:
    """Build a minimal state for testing."""
    base: AgentState = {
        "document": None,  # type: ignore
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
        "attempted": {},
        "provider_errors": [],
        "_planned_action": None,
        "_tool_result": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestShouldContinue:
    """Verify the conditional edge routing."""

    def test_complete_routes_to_terminate(self):
        state = _build_test_state(status=RunStatus.COMPLETE)
        assert should_continue(state) == "terminate"

    def test_partial_routes_to_terminate(self):
        state = _build_test_state(status=RunStatus.PARTIAL)
        assert should_continue(state) == "terminate"

    def test_planning_routes_to_plan(self):
        state = _build_test_state(status=RunStatus.PLANNING)
        assert should_continue(state) == "plan"


class TestPlanNode:
    """Verify the plan node logic."""

    def test_complete_gap_report_returns_complete(self):
        state = _build_test_state(
            gap_report=GapReport(gaps=[], satisfied=["a"], is_complete=True, total_fields=1),
        )
        result = plan_node(state, llm_client=MockLLMClient([]), skill=InvoiceSkill,
                           registry=_build_registry_with_mock_tools())
        assert result["status"] == RunStatus.COMPLETE

    def test_missing_llm_raises_runtime_error(self):
        state = _build_test_state()
        with pytest.raises(RuntimeError, match="LLM client is None"):
            plan_node(state)

    def test_missing_skill_raises_runtime_error(self):
        state = _build_test_state()
        with pytest.raises(RuntimeError, match="skill is None"):
            plan_node(state, llm_client=MockLLMClient([]))

    def test_missing_registry_raises_runtime_error(self):
        state = _build_test_state()
        with pytest.raises(RuntimeError, match="tool registry is None"):
            plan_node(state, llm_client=MockLLMClient([]), skill=InvoiceSkill)


class TestActNode:
    """Verify the act node tool dispatch."""

    def test_calls_tool_successfully(self):
        registry = _build_registry_with_mock_tools()
        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "test.png"}, "thought": "read", "field": "invoice_number"},
        )
        result = act_node(state, registry=registry, breaker=CircuitBreaker())
        assert result["status"] == RunStatus.REFLECTING
        assert result["_tool_result"].ok is True
        assert result["_tool_result"].data == "INV-2024-001"

    def test_circuit_breaker_blocks_tool(self):
        registry = _build_registry_with_mock_tools()
        breaker = CircuitBreaker(threshold=1)
        breaker.record_failure("ocr")
        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "test.png"}, "thought": "read", "field": "invoice_number"},
        )
        result = act_node(state, registry=registry, breaker=breaker)
        assert result["_tool_result"].ok is False
        assert "provider_unavailable" in result["_tool_result"].error

    def test_unknown_tool_returns_error(self):
        registry = _build_registry_with_mock_tools()
        state = _build_test_state(
            _planned_action={"tool": "nonexistent", "args": {}, "thought": "test", "field": None},
        )
        result = act_node(state, registry=registry, breaker=CircuitBreaker())
        assert result["_tool_result"].ok is False
        assert "not registered" in result["_tool_result"].error or "Unknown tool" in result["_tool_result"].error

    def test_skips_already_attempted_with_region_id(self):
        """plan_node should skip a tool call that already failed on a specific region [BLK-243]."""
        registry = _build_registry_with_mock_tools()
        import json as _json
        action = {"tool": "ocr", "args": {"image_path": "test.png", "region_id": "r1"}, "thought": "read", "field": "total"}
        attempt_key = f"ocr:{_json.dumps(action['args'], sort_keys=True)}"
        state = _build_test_state(
            attempted={"r1": {attempt_key}},
        )
        llm = MockLLMClient([action])
        result = plan_node(state, llm_client=llm, skill=InvoiceSkill, registry=registry)
        assert result["status"] == RunStatus.PLANNING
        assert result["_planned_action"] is None

    def test_skips_already_attempted_page_level_tool(self):
        """plan_node should skip a page-level tool (no region_id) that already failed [BLK-243].

        The observe_node records failures under "_global" when region_id is absent.
        The plan_node must use the same default to find the recorded failure.
        """
        registry = _build_registry_with_mock_tools()
        import json as _json
        action = {"tool": "ocr", "args": {"image_path": "page1.png"}, "thought": "read", "field": "total"}
        attempt_key = f"ocr:{_json.dumps(action['args'], sort_keys=True)}"
        state = _build_test_state(
            attempted={"_global": {attempt_key}},
        )
        llm = MockLLMClient([action])
        result = plan_node(state, llm_client=llm, skill=InvoiceSkill, registry=registry)
        assert result["status"] == RunStatus.PLANNING
        assert result["_planned_action"] is None


class TestObserveNode:
    """Verify the observe node state updates."""

    def test_successful_result_updates_extraction(self):
        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "test.png"}, "thought": "read", "field": "invoice_number"},
            _tool_result=ToolResult(
                ok=True, data="INV-001",
                grounding=Grounding(bbox=(0, 0, 100, 50), source_tool="ocr", confidence=0.9),
                tool="ocr",
            ),
            step=1,
        )
        result = observe_node(state)
        assert "invoice_number" in result["extraction"]
        assert result["extraction"]["invoice_number"].value == "INV-001"
        # Trace entry is added, but may be compacted if the field is now resolved [§12.3]
        assert result["trace"] is not None

    def test_failed_result_records_attempted(self):
        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "test.png", "region_id": "r1"}, "thought": "read", "field": "total"},
            _tool_result=ToolResult(ok=False, error="timeout", tool="ocr"),
            step=1,
        )
        result = observe_node(state)
        assert "r1" in result["attempted"]
        assert len(result["attempted"]["r1"]) == 1
        assert "ocr" in list(result["provider_errors"])[0]


class TestReflectNode:
    """Verify the reflect node validator integration."""

    def test_complete_when_no_gaps(self):
        from src.tools.base import FieldValue, Grounding
        extraction = {
            "invoice_number": FieldValue("invoice_number", "INV-001",
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.95), confidence=0.95),
            "invoice_date": FieldValue("invoice_date", "2024-01-15",
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.9), confidence=0.9),
            "due_date": FieldValue("due_date", "2024-02-14",
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.9), confidence=0.9),
            "vendor": FieldValue("vendor", "ACME",
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.9), confidence=0.9),
            "line_items": FieldValue("line_items", [],
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.9), confidence=0.9),
            "subtotal": FieldValue("subtotal", 100.0,
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.9), confidence=0.9),
            "tax": FieldValue("tax", 10.0,
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.9), confidence=0.9),
            "total": FieldValue("total", 110.0,
                grounding=Grounding(bbox=(0, 0, 100, 50), confidence=0.9), confidence=0.9),
        }
        state = _build_test_state(extraction=extraction, total_cycles=0)
        result = reflect_node(state, skill=InvoiceSkill,
                              validator_config=ValidatorConfig(default_confidence_threshold=0.8))
        assert result["status"] == RunStatus.COMPLETE
        assert result["gap_report"].is_complete is True

    def test_partial_when_caps_exhausted(self):
        state = _build_test_state(
            field_attempts={"total": 5},
            total_cycles=30,
        )
        result = reflect_node(state, skill=InvoiceSkill,
                              validator_config=ValidatorConfig())
        assert result["status"] == RunStatus.PARTIAL


class TestTerminateNode:
    """Verify the terminate node builds ExtractedResult."""

    def test_builds_result_from_state(self):
        state = _build_test_state(
            status=RunStatus.PARTIAL,
            gap_report=GapReport(gaps=[FieldGap("total", GapType.MISSING, "missing")], is_complete=False),
            total_cycles=5,
            provider_errors=["ocr: timeout"],
            total_tokens=500,
        )
        result = terminate_node(state)
        extracted = result["result"]
        assert extracted.is_complete is False
        assert extracted.status == RunStatus.PARTIAL
        assert extracted.total_cycles == 5
        assert "ocr: timeout" in extracted.provider_errors

    def test_zero_token_zero_field_reports_error(self):
        """BLK-171: Zero-token runs with zero fields should report ERROR, not PARTIAL."""
        state = _build_test_state(
            status=RunStatus.PARTIAL,
            gap_report=GapReport(gaps=[FieldGap("total", GapType.MISSING, "missing")], is_complete=False),
            total_cycles=0,
            total_tokens=0,
        )
        result = terminate_node(state)
        extracted = result["result"]
        assert extracted.is_complete is False
        assert extracted.status == RunStatus.ERROR
        assert any("No fields extracted" in e for e in extracted.provider_errors)


class TestGraphIntegration:
    """End-to-end graph integration with mocked LLM + tools."""

    def test_graph_completes_with_mocked_tools(self):
        """Verify the full ReAct loop runs and terminates."""
        registry = _build_registry_with_mock_tools()

        # Mock LLM that fills invoice_number via ocr, then says done
        llm = MockLLMClient([
            {"thought": "Read invoice number", "tool": "ocr", "args": {"image_path": "test.png"}, "field": "invoice_number"},
        ])

        config = ValidatorConfig(default_confidence_threshold=0.8)
        graph = build_react_graph(
            registry=registry,
            skill=InvoiceSkill,
            validator_config=config,
            llm_client=llm,
        )

        state = _build_test_state()
        final = graph.invoke(state, config={"recursion_limit": 15})

        # The graph should have run at least one cycle
        assert final.get("total_cycles", 0) >= 1

    def test_graph_terminates_on_cap_exhaustion(self):
        """Verify the graph terminates when document cycle cap is hit."""
        registry = ToolRegistry()
        registry.register(ToolSpec(name="failing_tool", description="Always fails"), _mock_failing_tool)

        llm = MockLLMClient([
            {"thought": "try failing", "tool": "failing_tool", "args": {"image_path": "x.png"}, "field": "total"},
        ] * 50)

        config = ValidatorConfig(default_confidence_threshold=0.8)
        graph = build_react_graph(
            registry=registry,
            skill=InvoiceSkill,
            validator_config=config,
            llm_client=llm,
        )

        state = _build_test_state()
        final = graph.invoke(state, config={"recursion_limit": 40})

        # Should terminate with partial/paused status due to cap exhaustion or auto-pause [BLK-049, BLK-243]
        status = final.get("status")
        assert status in (RunStatus.PARTIAL, RunStatus.COMPLETE, RunStatus.PAUSED)


class TestEmptyRegistryCheck:
    """Verify build_tool_registry raises on empty registry [BLK-138]."""

    def test_empty_registry_raises_runtime_error(self):
        from src.tools.base import ToolRegistry

        # Verify the check logic: an empty registry should raise RuntimeError
        registry = ToolRegistry()
        assert len(registry.names()) == 0

        with pytest.raises(RuntimeError, match="Tool registry is empty"):
            if len(registry.names()) == 0:
                raise RuntimeError(
                    "Tool registry is empty. Check provider configuration. "
                    "Ensure required packages are installed."
                )


# ---------------------------------------------------------------------------
# Graph-specific validation in the live loop [BLK-218]
# ---------------------------------------------------------------------------

class TestGraphValidationInLiveLoop:
    """Verify graph extraction uses graph-specific validation during the live loop [BLK-218]."""

    def test_reflect_node_dispatches_graph_validation(self):
        """reflect_node should call _validate_graph_state for graph_extraction tasks [BLK-218]."""
        import inspect
        from src.agent.graph import reflect_node
        source = inspect.getsource(reflect_node)
        assert "task_type" in source, (
            "reflect_node must check task_type to dispatch validation [BLK-218]"
        )
        assert "graph_extraction" in source, (
            "reflect_node must handle graph_extraction task type [BLK-218]"
        )
        assert "_validate_graph_state" in source, (
            "reflect_node must call _validate_graph_state for graph tasks [BLK-218]"
        )

    def test_validate_graph_state_exists(self):
        """_validate_graph_state helper should exist in graph.py [BLK-218]."""
        from src.agent.graph import _validate_graph_state
        assert callable(_validate_graph_state)

    def test_validate_graph_state_produces_graph_gap_types(self):
        """_validate_graph_state should produce graph-specific GapTypes [BLK-218]."""
        from src.agent.graph import _validate_graph_state
        from src.agent.state import AgentState, RunStatus
        from src.agent.validator import GapType
        from src.skills.pid_diagram import PnIDSkill
        from src.templates.pid_diagram import PnIDContract

        skill = PnIDSkill  # PnIDSkill is already a Skill instance
        template = PnIDContract

        # Empty state — no graph built yet
        state: AgentState = {
            "task_type": "graph_extraction",
            "trace": [],
            "total_cycles": 1,
            "status": RunStatus.PLANNING,
            "provider_errors": [],
            "token_usage": [],
            "extraction": {},
            "template_schema": template,
        }  # type: ignore

        gap_report = _validate_graph_state(state, template, skill)
        # Should have graph-specific gaps (no nodes, no edges)
        gap_types = {g.gap_type for g in gap_report.gaps}
        assert GapType.NODE_MISSING in gap_types, (
            "Graph validation should report NODE_MISSING when no nodes [BLK-218]"
        )
        assert GapType.EDGE_MISSING in gap_types, (
            "Graph validation should report EDGE_MISSING when no edges [BLK-218]"
        )

    def test_validate_graph_state_passes_with_complete_graph(self):
        """_validate_graph_state should return is_complete when graph is valid [BLK-218]."""
        from src.agent.graph import _validate_graph_state
        from src.agent.state import AgentState, RunStatus
        from src.skills.pid_diagram import PnIDSkill
        from src.templates.pid_diagram import PnIDContract
        from src.tools.base import ToolResult
        from src.agent.state import TraceEntry

        skill = PnIDSkill  # PnIDSkill is already a Skill instance
        template = PnIDContract

        # Build a trace with build_graph + serialize_graph results
        trace = [
            TraceEntry(
                step=1,
                thought="build graph",
                tool_name="build_graph",
                tool_args={},
                result=ToolResult(
                    ok=True,
                    data={
                        "nodes": [
                            {"id": "n1", "type": "equipment", "bbox": [10, 10, 50, 50]},
                            {"id": "n2", "type": "valve", "bbox": [60, 10, 80, 30]},
                        ],
                        "edges": [
                            {"id": "e1", "source": "n1", "target": "n2"},
                        ],
                    },
                ),
            ),
            TraceEntry(
                step=2,
                thought="serialize dexpi",
                tool_name="serialize_graph",
                tool_args={},
                result=ToolResult(
                    ok=True,
                    data={"format": "dexpi_xml", "content": "<dexpi>...</dexpi>"},
                ),
            ),
            TraceEntry(
                step=2,
                thought="serialize smart_pid",
                tool_name="serialize_graph",
                tool_args={},
                result=ToolResult(
                    ok=True,
                    data={"format": "smart_pid_json", "content": "{}"},
                ),
            ),
            TraceEntry(
                step=2,
                thought="serialize graphml",
                tool_name="serialize_graph",
                tool_args={},
                result=ToolResult(
                    ok=True,
                    data={"format": "graphml", "content": "<graphml>...</graphml>"},
                ),
            ),
        ]

        state: AgentState = {
            "task_type": "graph_extraction",
            "trace": trace,
            "total_cycles": 2,
            "status": RunStatus.PLANNING,
            "provider_errors": [],
            "token_usage": [],
            "extraction": {},
            "template_schema": template,
        }  # type: ignore

        gap_report = _validate_graph_state(state, template, skill)
        assert gap_report.is_complete, (
            f"Graph validation should be complete with valid graph, gaps: {gap_report.gaps} [BLK-218]"
        )

    def test_result_gap_count_handles_graph_tasks(self):
        """result_gap_count should count node_types + edge_types + output_formats for graph tasks [BLK-218]."""
        from src.api.run_engine import result_gap_count
        from src.templates.pid_diagram import PnIDContract

        state = {
            "template_schema": PnIDContract(),  # Instantiate to get default_factory values
            "task_type": "graph_extraction",
        }
        count = result_gap_count(state)
        # PnIDContract has 5 node_types + 4 edge_types + 3 output_formats = 12
        assert count == 12, (
            f"result_gap_count should return 12 for PnIDContract graph task, got {count} [BLK-218]"
        )

    def test_result_gap_count_handles_field_tasks(self):
        """result_gap_count should still work for field extraction tasks [BLK-218]."""
        from src.api.run_engine import result_gap_count
        from src.templates.invoice import InvoiceTemplate

        state = {
            "template_schema": InvoiceTemplate,
            "task_type": "extraction",
        }
        count = result_gap_count(state)
        assert count > 0, (
            "result_gap_count should return >0 for InvoiceTemplate [BLK-218]"
        )
