"""Tests for OneFlow single-agent optimization mode [BLK-074, SCRUM-81]."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.agent.oneflow import (
    build_oneflow_graph,
    plan_and_act_node,
    observe_and_reflect_node,
    estimate_cost_savings,
    _oneflow_terminate,
)
from src.agent.graph import CircuitBreaker
from src.agent.state import AgentState, RunStatus
from src.agent.validator import ValidatorConfig
from src.agent.token_tracking import LLMResponse
from src.tools.base import ToolRegistry, ToolResult, ToolSpec, FieldValue


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_registry():
    """Create a mock tool registry."""
    registry = MagicMock(spec=ToolRegistry)
    spec = ToolSpec(
        name="ocr",
        description="Extract text from image",
    )
    registry.get.return_value = (spec, MagicMock())
    registry.specs.return_value = [spec]
    registry.call.return_value = ToolResult(
        ok=True,
        data={"invoice_number": FieldValue(name="invoice_number", value="INV-001", confidence=0.95)},
        tool="ocr",
    )
    return registry


@pytest.fixture
def mock_skill():
    """Create a mock skill."""
    skill = MagicMock()
    skill.name = "invoice_skill"
    skill.system_prompt = "Extract invoice fields."
    skill.probe_order = [{"region_type": "header", "rationale": "Header"}]
    skill.invariants = []
    skill.failure_actions = {"missing": "Re-probe"}
    skill.max_cycles_per_field = 5
    skill.max_cycles_per_document = 30
    return skill


@pytest.fixture
def initial_state():
    """Create initial agent state."""
    return {
        "step": 0,
        "status": RunStatus.PLANNING,
        "extraction": {},
        "regions": {},
        "attempted": {},
        "trace": [],
        "total_cycles": 0,
        "provider_errors": [],
        "document": "test_invoice.png",
        "document_state": None,
        "gap_report": None,
        "template": None,
    }


# ---------------------------------------------------------------------------
# Cost estimation tests
# ---------------------------------------------------------------------------


class TestCostEstimation:
    """Test OneFlow cost estimation."""

    def test_basic_estimation(self):
        result = estimate_cost_savings(num_cycles=10)
        assert result["standard_llm_calls"] == 20  # 2 per cycle
        assert result["oneflow_llm_calls"] == 10   # 1 per cycle
        assert result["call_reduction_percent"] == 50.0
        assert result["savings_usd"] > 0
        assert result["savings_percent"] > 0

    def test_high_volume_estimation(self):
        result = estimate_cost_savings(num_cycles=30)
        assert result["standard_llm_calls"] == 60
        assert result["oneflow_llm_calls"] == 30
        assert result["savings_percent"] == 50.0

    def test_custom_pricing(self):
        result = estimate_cost_savings(
            num_cycles=10,
            input_price_per_1k=0.01,
            output_price_per_1k=0.03,
        )
        assert result["savings_usd"] > 0
        assert result["standard_cost_usd"] > result["oneflow_cost_usd"]

    def test_zero_cycles(self):
        result = estimate_cost_savings(num_cycles=0)
        assert result["standard_cost_usd"] == 0
        assert result["oneflow_cost_usd"] == 0
        assert result["savings_percent"] == 0.0


# ---------------------------------------------------------------------------
# Plan and act node tests
# ---------------------------------------------------------------------------


class TestPlanAndActNode:
    """Test the combined plan_and_act node."""

    def test_complete_when_no_gaps(self, initial_state, mock_registry, mock_skill):
        from src.agent.validator import GapReport
        state = dict(initial_state)
        state["gap_report"] = GapReport(gaps=[], is_complete=True)

        result = plan_and_act_node(
            state,
            llm_client=MagicMock(),
            skill=mock_skill,
            registry=mock_registry,
        )
        assert result["status"] == RunStatus.COMPLETE

    def test_executes_tool_call(self, initial_state, mock_registry, mock_skill):
        mock_response = LLMResponse(content='{"thought": "Need to OCR the header", "tool": "ocr", "args": {"region": "header"}}')
        with patch("src.providers.llm.invoke_llm", return_value=mock_response):
            result = plan_and_act_node(
                initial_state,
                llm_client=MagicMock(),
                skill=mock_skill,
                registry=mock_registry,
                breaker=CircuitBreaker(),
            )

        assert result["status"] == RunStatus.PLANNING
        assert "extraction" in result
        assert "trace" in result
        assert len(result["trace"]) == 1
        mock_registry.call.assert_called_once()

    def test_handles_none_tool(self, initial_state, mock_registry, mock_skill):
        mock_response = LLMResponse(content='{"thought": "All done", "tool": "none", "args": {}}')
        with patch("src.providers.llm.invoke_llm", return_value=mock_response):
            result = plan_and_act_node(
                initial_state,
                llm_client=MagicMock(),
                skill=mock_skill,
                registry=mock_registry,
            )

        assert result["status"] == RunStatus.COMPLETE

    def test_none_tool_with_gaps_returns_partial(self, initial_state, mock_registry, mock_skill):
        """SCRUM-481: Agent says 'done' but gaps remain → PARTIAL, not COMPLETE."""
        from src.agent.validator import GapReport, FieldGap, GapType
        state = dict(initial_state)
        state["gap_report"] = GapReport(
            gaps=[FieldGap(field="total", gap_type=GapType.MISSING, detail="Not extracted")],
            is_complete=False,
        )
        mock_response = LLMResponse(content='{"thought": "All done", "tool": "none", "args": {}}')
        with patch("src.providers.llm.invoke_llm", return_value=mock_response):
            result = plan_and_act_node(
                state,
                llm_client=MagicMock(),
                skill=mock_skill,
                registry=mock_registry,
            )

        assert result["status"] == RunStatus.PARTIAL

    def test_handles_invalid_json(self, initial_state, mock_registry, mock_skill):
        with patch("src.providers.llm.invoke_llm", return_value=LLMResponse(content="not json")):
            result = plan_and_act_node(
                initial_state,
                llm_client=MagicMock(),
                skill=mock_skill,
                registry=mock_registry,
            )

        # Should not crash, just continue running
        assert result["status"] == RunStatus.PLANNING

    def test_handles_unknown_tool(self, initial_state, mock_registry, mock_skill):
        mock_registry.get.side_effect = KeyError("Tool not found")
        mock_response = LLMResponse(content='{"thought": "Try unknown tool", "tool": "nonexistent_tool", "args": {}}')
        with patch("src.providers.llm.invoke_llm", return_value=mock_response):
            result = plan_and_act_node(
                initial_state,
                llm_client=MagicMock(),
                skill=mock_skill,
                registry=mock_registry,
            )

        assert result["status"] == RunStatus.PLANNING

    def test_handles_tool_execution_error(self, initial_state, mock_registry, mock_skill):
        mock_registry.call.side_effect = Exception("Tool error")
        mock_response = LLMResponse(content='{"thought": "OCR the header", "tool": "ocr", "args": {}}')
        with patch("src.providers.llm.invoke_llm", return_value=mock_response):
            result = plan_and_act_node(
                initial_state,
                llm_client=MagicMock(),
                skill=mock_skill,
                registry=mock_registry,
                breaker=CircuitBreaker(),
            )

        assert result["status"] == RunStatus.PLANNING

    def test_requires_llm_client(self, initial_state, mock_registry, mock_skill):
        with pytest.raises(RuntimeError, match="OneFlow requires an LLM client"):
            plan_and_act_node(
                initial_state,
                llm_client=None,
                skill=mock_skill,
                registry=mock_registry,
            )

    def test_requires_skill(self, initial_state, mock_registry):
        with pytest.raises(RuntimeError, match="OneFlow requires a skill"):
            plan_and_act_node(
                initial_state,
                llm_client=MagicMock(),
                skill=None,
                registry=mock_registry,
            )

    def test_requires_registry(self, initial_state, mock_skill):
        with pytest.raises(RuntimeError, match="OneFlow requires a tool registry"):
            plan_and_act_node(
                initial_state,
                llm_client=MagicMock(),
                skill=mock_skill,
                registry=None,
            )


# ---------------------------------------------------------------------------
# Graph builder tests
# ---------------------------------------------------------------------------


class TestOneFlowGraphBuilder:
    """Test the OneFlow graph builder."""

    def test_builds_compiled_graph(self, mock_registry, mock_skill):
        validator_config = ValidatorConfig()
        graph = build_oneflow_graph(
            registry=mock_registry,
            skill=mock_skill,
            validator_config=validator_config,
            llm_client=MagicMock(),
        )
        # Compiled LangGraph should have an invoke method
        assert hasattr(graph, "invoke")

    def test_graph_with_breaker(self, mock_registry, mock_skill):
        validator_config = ValidatorConfig()
        breaker = CircuitBreaker(threshold=5)
        graph = build_oneflow_graph(
            registry=mock_registry,
            skill=mock_skill,
            validator_config=validator_config,
            llm_client=MagicMock(),
            breaker=breaker,
        )
        assert hasattr(graph, "invoke")

    def test_graph_with_control_does_not_crash(self, mock_registry, mock_skill):
        """SCRUM-482: OneFlow graph should build with control without crashing."""
        from src.api.run_executor import RunControl
        validator_config = ValidatorConfig()
        control = RunControl()
        graph = build_oneflow_graph(
            registry=mock_registry,
            skill=mock_skill,
            validator_config=validator_config,
            llm_client=MagicMock(),
            control=control,
        )
        assert hasattr(graph, "invoke")

    def test_graph_with_control_cancels(self, mock_registry, mock_skill, initial_state):
        """SCRUM-482: OneFlow routing with control cancel returns terminate."""
        from src.api.run_executor import RunControl
        validator_config = ValidatorConfig()
        control = RunControl()
        control.cancel_requested = True
        graph = build_oneflow_graph(
            registry=mock_registry,
            skill=mock_skill,
            validator_config=validator_config,
            llm_client=MagicMock(),
            control=control,
        )
        # Test the routing function directly — it should return "terminate" on cancel
        # We can't easily test full graph invoke because plan_and_act makes an LLM call
        # Access the internal routing function via the graph's conditional edges
        state = dict(initial_state)
        state["status"] = RunStatus.PLANNING
        # should_continue_with_control sets status to CANCELLED and returns "terminate"
        from src.agent.graph import should_continue_with_control
        next_node = should_continue_with_control(state, control)
        assert next_node == "terminate"
        assert state["status"] == RunStatus.CANCELLED


# ---------------------------------------------------------------------------
# AgentConfig integration tests
# ---------------------------------------------------------------------------


class TestAgentConfigOneFlow:
    """Test that AgentConfig supports execution_mode."""

    def test_default_execution_mode(self):
        from src.definitions.base import AgentConfig
        config = AgentConfig()
        assert config.execution_mode == "react"

    def test_oneflow_execution_mode(self):
        from src.definitions.base import AgentConfig
        config = AgentConfig(execution_mode="oneflow")
        assert config.execution_mode == "oneflow"

    def test_definition_with_oneflow(self):
        from src.definitions.base import AgentDefinition, AgentConfig
        defn = AgentDefinition(
            id="def-oneflow-test",
            name="OneFlow Test",
            skill_id="invoice",
            template_id="invoice",
            agent_config=AgentConfig(execution_mode="oneflow"),
        )
        assert defn.agent_config.execution_mode == "oneflow"
