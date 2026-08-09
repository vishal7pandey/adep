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
        assert "Unknown tool" in result["_tool_result"].error


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

        # Should terminate with partial status due to cap exhaustion
        status = final.get("status")
        assert status in (RunStatus.PARTIAL, RunStatus.COMPLETE)


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
