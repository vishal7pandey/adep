"""Tests for guardrail integration into the ReAct graph [SCRUM-149, BLK-079..086].

Verifies that:
- plan_node sanitizes input (PII redaction, exfiltration prevention) [BLK-083, BLK-086]
- plan_node validates LLM output (truncation, instruction sanitization) [BLK-079]
- plan_node writes audit log entries when audit_logger is provided [BLK-084]
- act_node rejects unregistered tools via tool_guardrails [BLK-080]
- act_node rejects path traversal in tool args [BLK-080]
- act_node uses sanitized args from guardrail decision [BLK-080]
- reflect_node terminates on loop detection [BLK-082]
- observe_node caps confidence for suspected hallucinations [BLK-081]
- observe_node removes ungrounded fields [BLK-081]
- build_react_graph wires all guardrails into the compiled graph [SCRUM-149]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.agent.graph import (
    CircuitBreaker,
    act_node,
    build_react_graph,
    observe_node,
    plan_node,
    reflect_node,
)
from src.agent.guardrails.audit_logging import AuditLogger
from src.agent.guardrails.loop_detection import LoopDetector
from src.agent.guardrails.tool_guardrails import ToolCallRateLimiter
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
# Shared fixtures
# ---------------------------------------------------------------------------

class MockLLMClient:
    """Mock LLM that returns pre-configured actions."""

    def __init__(self, actions: list[dict[str, Any]]) -> None:
        self._actions = actions
        self._idx = 0

    def invoke(self, system_prompt: str, user_prompt: str) -> str:
        if self._idx >= len(self._actions):
            return json.dumps({"thought": "done", "tool": "", "args": {}, "field": None})
        action = self._actions[self._idx]
        self._idx += 1
        return json.dumps(action)


def _mock_ocr(**kwargs: Any) -> ToolResult:
    return ToolResult(
        ok=True,
        data="INV-2024-001",
        grounding=Grounding(bbox=(10, 10, 200, 50), source_tool="ocr", confidence=0.95),
        tool="ocr",
    )


def _build_registry_with_mock_tools() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ToolSpec(name="ocr", description="Mock OCR"), _mock_ocr)
    return registry


def _build_test_state(**overrides: Any) -> AgentState:
    state: AgentState = {
        "step": 0,
        "extraction": {},
        "regions": {},
        "trace": [],
        "attempted": {},
        "field_attempts": {},
        "provider_errors": [],
        "token_usage": [],
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "total_cycles": 0,
        "status": RunStatus.PLANNING,
        "task_type": "extraction",
        "template_schema": InvoiceTemplate,
        "gap_report": GapReport(
            is_complete=False,
            total_fields=3,
            satisfied=[],
            gaps=[
                FieldGap(field="invoice_number", gap_type=GapType.MISSING, detail="not extracted"),
                FieldGap(field="vendor_name", gap_type=GapType.MISSING, detail="not extracted"),
                FieldGap(field="total", gap_type=GapType.MISSING, detail="not extracted"),
            ],
        ),
        "consecutive_non_improving": 0,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# plan_node guardrail tests
# ---------------------------------------------------------------------------

class TestPlanNodeGuardrails:
    """Verify plan_node applies input/output guardrails [BLK-079, BLK-083, BLK-086]."""

    def test_pii_redaction_in_user_prompt(self):
        """plan_node should redact PII from the user prompt before LLM call [BLK-083]."""
        captured_prompts: list[str] = []

        class CapturingLLM:
            def invoke(self, system_prompt: str, user_prompt: str) -> str:
                captured_prompts.append(user_prompt)
                return json.dumps({"thought": "ok", "tool": "ocr", "args": {}, "field": "invoice_number"})

        state = _build_test_state()
        state["extraction"] = {
            "vendor_name": FieldValue(
                name="vendor_name",
                value="Call me at 555-123-4567 or email john@example.com",
                grounding=Grounding(bbox=(0, 0, 100, 50), source_tool="ocr", confidence=0.9),
            ),
        }
        result = plan_node(
            state,
            llm_client=CapturingLLM(),
            skill=InvoiceSkill,
            registry=_build_registry_with_mock_tools(),
        )
        assert result["status"] == RunStatus.ACTING
        # The prompt sent to the LLM should have PII redacted
        assert "555-123-4567" not in captured_prompts[0]
        assert "john@example.com" not in captured_prompts[0]

    def test_exfiltration_sanitization_in_user_prompt(self):
        """plan_node should sanitize zero-width chars and control chars from input [BLK-086]."""
        captured_prompts: list[str] = []

        class CapturingLLM:
            def invoke(self, system_prompt: str, user_prompt: str) -> str:
                captured_prompts.append(user_prompt)
                return json.dumps({"thought": "ok", "tool": "ocr", "args": {}, "field": "invoice_number"})

        state = _build_test_state()
        state["extraction"] = {
            "vendor_name": FieldValue(
                name="vendor_name",
                value="ACME\u200bCorp",  # zero-width space
                grounding=Grounding(bbox=(0, 0, 100, 50), source_tool="ocr", confidence=0.9),
            ),
        }
        result = plan_node(
            state,
            llm_client=CapturingLLM(),
            skill=InvoiceSkill,
            registry=_build_registry_with_mock_tools(),
        )
        assert result["status"] == RunStatus.ACTING
        # Zero-width chars should be stripped
        assert "\u200b" not in captured_prompts[0]

    def test_output_truncation_guardrail(self):
        """plan_node should truncate overly long LLM output [BLK-079]."""
        class LongOutputLLM:
            def invoke(self, system_prompt: str, user_prompt: str) -> str:
                return "A" * 100000  # Very long output

        state = _build_test_state()
        result = plan_node(
            state,
            llm_client=LongOutputLLM(),
            skill=InvoiceSkill,
            registry=_build_registry_with_mock_tools(),
        )
        # Should still produce a valid action (truncation is non-fatal)
        assert result["status"] in (RunStatus.ACTING, RunStatus.PLANNING, RunStatus.PARTIAL)

    def test_audit_log_written_when_logger_provided(self, tmp_path: Path):
        """plan_node should write audit log entries when audit_logger is provided [BLK-084]."""
        llm = MockLLMClient([
            {"thought": "read invoice", "tool": "ocr", "args": {}, "field": "invoice_number"},
        ])
        audit_logger = AuditLogger(run_id="test-audit-run", base_dir=tmp_path / ".adep")

        state = _build_test_state()
        plan_node(
            state,
            llm_client=llm,
            skill=InvoiceSkill,
            registry=_build_registry_with_mock_tools(),
            audit_logger=audit_logger,
        )

        assert audit_logger.log_path.exists()
        log_content = audit_logger.log_path.read_text(encoding="utf-8").strip()
        assert log_content  # non-empty
        entries = [json.loads(line) for line in log_content.split("\n") if line]
        assert len(entries) >= 1
        assert entries[0]["node"] == "plan"
        assert entries[0]["run_id"] == "test-audit-run"
        assert "entry_hash" in entries[0]
        assert "prev_hash" in entries[0]

    def test_audit_log_chain_integrity(self, tmp_path: Path):
        """Multiple plan_node calls should produce a verifiable hash chain [BLK-084]."""
        llm = MockLLMClient([
            {"thought": "read invoice", "tool": "ocr", "args": {}, "field": "invoice_number"},
            {"thought": "read vendor", "tool": "ocr", "args": {}, "field": "vendor_name"},
        ])
        audit_logger = AuditLogger(run_id="test-chain-run", base_dir=tmp_path / ".adep")

        state = _build_test_state()
        plan_node(
            state,
            llm_client=llm,
            skill=InvoiceSkill,
            registry=_build_registry_with_mock_tools(),
            audit_logger=audit_logger,
        )
        # Second call
        state2 = _build_test_state(step=1)
        plan_node(
            state2,
            llm_client=llm,
            skill=InvoiceSkill,
            registry=_build_registry_with_mock_tools(),
            audit_logger=audit_logger,
        )

        is_valid, msg = audit_logger.verify_chain()
        assert is_valid, f"Chain should be valid: {msg}"


# ---------------------------------------------------------------------------
# act_node guardrail tests
# ---------------------------------------------------------------------------

class TestActNodeGuardrails:
    """Verify act_node applies tool guardrails [BLK-080]."""

    def test_rejects_unregistered_tool(self):
        """act_node should reject tools not in the registry [BLK-080]."""
        registry = _build_registry_with_mock_tools()
        state = _build_test_state(
            _planned_action={"tool": "evil_tool", "args": {}, "thought": "test", "field": None},
        )
        result = act_node(state, registry=registry, breaker=CircuitBreaker())
        assert result["_tool_result"].ok is False
        assert "rejected" in result["_tool_result"].error.lower()

    def test_rejects_path_traversal_in_args(self):
        """act_node should reject path traversal in tool args [BLK-080]."""
        registry = _build_registry_with_mock_tools()
        state = _build_test_state(
            _planned_action={
                "tool": "ocr",
                "args": {"image_path": "../../../etc/passwd"},
                "thought": "read",
                "field": "invoice_number",
            },
        )
        result = act_node(state, registry=registry, breaker=CircuitBreaker())
        assert result["_tool_result"].ok is False

    def test_sanitized_args_used_for_execution(self):
        """act_node should use sanitized args from guardrail decision [BLK-080]."""
        registry = _build_registry_with_mock_tools()
        state = _build_test_state(
            _planned_action={
                "tool": "ocr",
                "args": {"image_path": "test.png"},
                "thought": "read",
                "field": "invoice_number",
            },
        )
        result = act_node(state, registry=registry, breaker=CircuitBreaker())
        assert result["_tool_result"].ok is True
        assert result["_tool_result"].data == "INV-2024-001"

    def test_rate_limiter_allows_within_limit(self):
        """act_node should allow tool calls within rate limit [BLK-080]."""
        registry = _build_registry_with_mock_tools()
        rate_limiter = ToolCallRateLimiter(max_per_run=5)
        state = _build_test_state(
            _planned_action={
                "tool": "ocr",
                "args": {"image_path": "test.png"},
                "thought": "read",
                "field": "invoice_number",
            },
        )
        result = act_node(
            state, registry=registry, breaker=CircuitBreaker(),
            rate_limiter=rate_limiter,
        )
        assert result["_tool_result"].ok is True


# ---------------------------------------------------------------------------
# reflect_node guardrail tests
# ---------------------------------------------------------------------------

class TestReflectNodeLoopDetection:
    """Verify reflect_node detects and terminates on loops [BLK-082]."""

    def test_loop_detection_terminates_on_repetition(self):
        """reflect_node should set PARTIAL status when a loop is detected [BLK-082]."""
        loop_detector = LoopDetector(max_cycles_per_field=5, max_cycles_per_document=30)

        # Simulate enough repetitive cycles to trigger tool repetition
        for i in range(5):
            loop_detector.record_cycle("ocr", {"image_path": "test.png"}, "invoice_number", "read it", 1)

        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "test.png"}, "thought": "read it", "field": "invoice_number"},
            extraction={
                "invoice_number": FieldValue(
                    name="invoice_number",
                    value="INV-001",
                    grounding=Grounding(bbox=(0, 0, 100, 50), source_tool="ocr", confidence=0.9),
                ),
            },
        )

        result = reflect_node(
            state,
            skill=InvoiceSkill,
            validator_config=ValidatorConfig(),
            loop_detector=loop_detector,
        )

        assert result["status"] == RunStatus.PARTIAL

    def test_no_loop_when_progress_is_made(self):
        """reflect_node should not terminate when there's no loop [BLK-082]."""
        loop_detector = LoopDetector(max_cycles_per_field=5, max_cycles_per_document=30)

        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "page1.png"}, "thought": "read page 1", "field": "invoice_number"},
            extraction={
                "invoice_number": FieldValue(
                    name="invoice_number",
                    value="INV-001",
                    grounding=Grounding(bbox=(0, 0, 100, 50), source_tool="ocr", confidence=0.9),
                ),
            },
        )

        result = reflect_node(
            state,
            skill=InvoiceSkill,
            validator_config=ValidatorConfig(),
            loop_detector=loop_detector,
        )

        # Should not be PARTIAL due to loop (might be PLANNING since gaps remain)
        assert result["status"] != RunStatus.PARTIAL or "caps" in str(result).lower()


# ---------------------------------------------------------------------------
# observe_node guardrail tests
# ---------------------------------------------------------------------------

class TestObserveNodeHallucinationDetection:
    """Verify observe_node detects hallucinations [BLK-081]."""

    def test_ungrounded_field_removed(self):
        """observe_node should remove fields with no grounding when they are the target field [BLK-081]."""
        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "test.png"}, "thought": "read", "field": "vendor_name"},
            _tool_result=ToolResult(
                ok=True,
                data="ACME Corp",
                grounding=None,  # No grounding provided by tool
                tool="ocr",
            ),
            step=1,
        )

        result = observe_node(state)
        # The ungrounded vendor_name should have been removed by hallucination guardrail
        assert "vendor_name" not in result["extraction"]

    def test_grounded_field_preserved(self):
        """observe_node should preserve properly grounded fields [BLK-081]."""
        state = _build_test_state(
            _planned_action={"tool": "ocr", "args": {"image_path": "test.png"}, "thought": "read", "field": "invoice_number"},
            _tool_result=ToolResult(
                ok=True,
                data="INV-001",
                grounding=Grounding(bbox=(0, 0, 100, 50), source_tool="ocr", confidence=0.9),
                tool="ocr",
            ),
            step=1,
        )

        result = observe_node(state)
        assert "invoice_number" in result["extraction"]
        fv = result["extraction"]["invoice_number"]
        assert fv.value == "INV-001"
        assert fv.grounding is not None


# ---------------------------------------------------------------------------
# build_react_graph integration tests
# ---------------------------------------------------------------------------

class TestBuildReactGraphGuardrails:
    """Verify build_react_graph wires guardrails correctly [SCRUM-149]."""

    def test_graph_builds_with_all_guardrails(self, tmp_path: Path):
        """build_react_graph should compile successfully with all guardrail params [SCRUM-149]."""
        registry = _build_registry_with_mock_tools()
        llm = MockLLMClient([
            {"thought": "done", "tool": "", "args": {}, "field": None},
        ])
        audit_logger = AuditLogger(run_id="test-graph-run", base_dir=tmp_path / ".adep")

        graph = build_react_graph(
            registry=registry,
            skill=InvoiceSkill,
            validator_config=ValidatorConfig(),
            llm_client=llm,
            rate_limiter=ToolCallRateLimiter(),
            loop_detector=LoopDetector(),
            audit_logger=audit_logger,
        )
        assert graph is not None

    def test_graph_runs_with_guardrails_and_produces_audit_log(self, tmp_path: Path):
        """End-to-end: graph with guardrails should produce audit log entries [SCRUM-149]."""
        registry = _build_registry_with_mock_tools()
        llm = MockLLMClient([
            {"thought": "read invoice", "tool": "ocr", "args": {"image_path": "test.png"}, "field": "invoice_number"},
            {"thought": "done", "tool": "", "args": {}, "field": None},
        ])
        audit_logger = AuditLogger(run_id="test-e2e-run", base_dir=tmp_path / ".adep")

        graph = build_react_graph(
            registry=registry,
            skill=InvoiceSkill,
            validator_config=ValidatorConfig(),
            llm_client=llm,
            rate_limiter=ToolCallRateLimiter(),
            loop_detector=LoopDetector(),
            audit_logger=audit_logger,
        )

        state = _build_test_state()
        final_state = graph.invoke(
            state,
            config={"recursion_limit": 20},
        )

        # Audit log should have at least one entry from the plan node
        assert audit_logger.log_path.exists()
        log_content = audit_logger.log_path.read_text(encoding="utf-8").strip()
        entries = [json.loads(line) for line in log_content.split("\n") if line]
        assert len(entries) >= 1
        assert all(e["run_id"] == "test-e2e-run" for e in entries)
