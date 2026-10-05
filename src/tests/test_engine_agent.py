"""Tests for the new-engine agent loop (ADE-39): wires ADE-34-38 as pydantic-ai tools.

Hermetic: every ADE-34/36/37/38 function this module calls is monkeypatched at the boundary
`src.engine.agent` imports through (same style as ADE-38's tests); the one true integration test
(AC5) uses pydantic-ai's own `FunctionModel` to script a tool-call sequence instead of a real model
call. No network, no live Azure/LLM credentials, no `AZURE_API_KEY` needed anywhere in this file.
"""

from __future__ import annotations

import pytest
from pydantic_ai import RunContext
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from src.engine import agent as engine_agent
from src.engine import skills as engine_skills
from src.engine import tools as engine_tools
from src.engine.agent import ExtractionState
from src.engine.skills import Skill


def _ctx(deps: ExtractionState) -> RunContext[ExtractionState]:
    """Build a minimal RunContext for calling a @agent.tool function directly in a test."""
    return RunContext(deps=deps, model=TestModel(), usage=None, prompt=None)


@pytest.fixture
def state() -> ExtractionState:
    return ExtractionState(document_id="doc-1", skill_id="")


# --- AC1: build_agent() registers every ADE-34-38 module as a tool --------------------------------


def test_build_agent_registers_every_tool():
    built = engine_agent.build_agent(model=TestModel())
    names = set(built._function_toolset.tools.keys())
    expected = {
        "list_document_pages",
        "survey_layout_tool",
        "survey_region_tool",
        "crop_and_read_tool",
        "ocr_page_tool",
        "budget_status",
        "update_plan",
        "validate_extraction",
        "to_dexpi_xml",
        "to_spice_netlist",
        "list_skills",
        "load_skill",
    }
    assert expected <= names


# --- AC2: system prompt documents tools but never injects probe_order -----------------------------


def test_system_prompt_documents_tools_but_omits_probe_order():
    prompt = engine_agent.SYSTEM_PROMPT
    for name in (
        "survey_layout_tool",
        "crop_and_read_tool",
        "validate_extraction",
        "budget_status",
    ):
        assert name in prompt
    # A skill's probe_order must never leak into the static system prompt.
    assert "probe_order" not in prompt


def test_to_prompt_block_output_never_appears_verbatim_in_system_prompt():
    skill = Skill(
        id="pid",
        name="P&ID",
        description="d",
        hints="h",
        probe_order=[{"step": "look at the title block first"}],
    )
    rendered = skill.to_prompt_block()
    assert "probe_order" not in rendered  # ADE-34's own guarantee
    assert "probe_order" not in engine_agent.SYSTEM_PROMPT


# --- AC3: importable with no Azure credentials; building the real model is lazy -------------------


def test_import_requires_no_azure_credentials(monkeypatch):
    for var in ("AZURE_API_KEY", "AZURE_CHAT_ENDPOINT", "AZURE_CHAT_DEPLOYMENT"):
        monkeypatch.delenv(var, raising=False)
    import importlib

    importlib.reload(engine_agent)  # must not raise even with no Azure env at all


def test_build_agent_with_no_model_arg_does_not_require_azure_env_until_called(monkeypatch):
    monkeypatch.delenv("AZURE_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_CHAT_ENDPOINT", raising=False)
    # Passing an explicit model must never touch Azure settings at all.
    built = engine_agent.build_agent(model=TestModel())
    assert built is not None


# --- AC4: tool-call failures are structured errors, never exceptions ------------------------------


def test_crop_and_read_tool_wraps_errors_as_structured_not_exceptions(state, monkeypatch):
    def fake_crop_and_read(document_id, bbox_pixel, question, page_num=1):
        return {"error": "Page 99 not found for document 'doc-1'"}

    monkeypatch.setattr(engine_tools, "crop_and_read", fake_crop_and_read)
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["crop_and_read_tool"].function

    result = tool_fn(_ctx(state), "doc-1", (0, 0, 10, 10), "what is this?", 99)

    assert result == {"error": "Page 99 not found for document 'doc-1'"}
    assert "crop_and_read_tool" in state.budget.tool_history


def test_validate_extraction_never_raises_on_malformed_data(state):
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["validate_extraction"].function

    result = tool_fn(_ctx(state), {"dexpi_xml": "<not valid xml"})

    assert result["valid"] is False
    assert any("not well-formed" in e.lower() or "parse" in e.lower() for e in result["errors"])


def test_dexpi_stub_never_raises(state):
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["to_dexpi_xml"].function

    result = tool_fn(_ctx(state), {"nodes": [], "valves": []})

    assert result["dexpi_xml"] is None
    assert "ADE-14" in result["error"]


def test_spice_stub_never_raises(state):
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["to_spice_netlist"].function

    result = tool_fn(_ctx(state), {"components": []})

    assert result["spice_netlist"] is None
    assert "ADE-16" in result["error"]


# --- R3/R4/R5: budget accounting per tool ---------------------------------------------------------


def test_budget_status_tool_is_free(state):
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["budget_status"].function

    before = len(state.budget.tool_history)
    result = tool_fn(_ctx(state))
    after = len(state.budget.tool_history)

    assert after == before  # budget_status itself is never recorded
    assert "remaining_turns" in result


def test_update_plan_tool_records_cost_and_updates_state(state):
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["update_plan"].function

    tasks = [
        {"description": "survey the page", "status": "completed"},
        {"description": "crop the valves", "status": "in_progress"},
        {"description": "serialize", "status": "pending"},
    ]
    result = tool_fn(_ctx(state), tasks)

    assert state.todo == tasks
    assert "update_plan" in state.budget.tool_history
    assert result["summary"] == "1 completed, 1 in progress, 1 pending"


def test_perception_tools_record_one_turn_each(state, monkeypatch):
    monkeypatch.setattr(
        engine_tools, "survey_layout", lambda document_id, page_num=1: {"zones": []}
    )
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["survey_layout_tool"].function

    before = state.budget.spend.turns
    tool_fn(_ctx(state), "doc-1", 1)
    after = state.budget.spend.turns

    assert after == before + 1


# --- R6: validate_extraction's combined checks -----------------------------------------------


def test_validate_extraction_surfaces_could_not_check_never_as_passed(state, monkeypatch):
    skill = Skill(
        id="s1",
        name="S1",
        description="",
        hints="",
        invariants=[{"name": "balance", "check": "balance_equals", "fields": ["a", "b", "c", "d"]}],
    )
    monkeypatch.setattr(engine_skills, "load_skill", lambda skill_id: skill)
    state.skill_id = "s1"
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["validate_extraction"].function

    result = tool_fn(_ctx(state), {"a": 1})  # b, c, d all missing -> could_not_check

    assert "balance" in result["invariants_unchecked"]
    assert "balance" not in result["invariants_passed"]


def test_validate_extraction_completeness_and_thinness_checks(state):
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["validate_extraction"].function

    result = tool_fn(
        _ctx(state), {"nodes": [{"id": "n1"}, {"id": "n2"}], "valves": [], "edges": []}
    )

    assert any("valves" in e for e in result["errors"])  # empty collection -> error
    assert result["valid"] is False


def test_validate_extraction_dexpi_wellformedness_only(state):
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["validate_extraction"].function

    result = tool_fn(_ctx(state), {"dexpi_xml": "<DEXPI><Plant/></DEXPI>"})

    assert result["dexpi"]["valid"] is True
    assert "equipment" not in result["dexpi"]  # no round-trip entity counts (needs ADE-14)


# --- R8: load_skill_tool / list_skills_tool --------------------------------------------------


def test_load_skill_tool_returns_structured_error_for_unknown_id(monkeypatch):
    monkeypatch.setattr(engine_skills, "load_skill", lambda skill_id: None)
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["load_skill"].function

    result = tool_fn("no-such-skill")

    assert result == {"error": "Skill 'no-such-skill' not found"}


def test_list_skills_tool_delegates_to_engine_skills(monkeypatch):
    monkeypatch.setattr(engine_skills, "list_skills", lambda: [{"id": "pid", "name": "P&ID"}])
    built = engine_agent.build_agent(model=TestModel())
    tool_fn = built._function_toolset.tools["list_skills"].function

    assert tool_fn() == [{"id": "pid", "name": "P&ID"}]


# --- AC5: a scripted FunctionModel drives the loop through validate_extraction --------------------


def test_function_model_drives_tool_calls_through_validate_extraction_to_a_final_answer(
    monkeypatch,
):
    monkeypatch.setattr(
        engine_tools,
        "survey_layout",
        lambda document_id, page_num=1: {"zones": [], "zone_count": 0},
    )

    calls: list[str] = []

    def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        last = messages[-1]
        tool_returns = (
            [p for p in last.parts if isinstance(p, ToolReturnPart)]
            if isinstance(last, ModelRequest)
            else []
        )
        if not calls:
            calls.append("survey_layout_tool")
            return ModelResponse(
                parts=[ToolCallPart(tool_name="survey_layout_tool", args={"document_id": "doc-1"})]
            )
        if len(calls) == 1 and tool_returns:
            calls.append("validate_extraction")
            return ModelResponse(
                parts=[ToolCallPart(tool_name="validate_extraction", args={"data": {}})]
            )
        return ModelResponse(parts=[TextPart('{"status": "done"}')])

    built = engine_agent.build_agent(model=FunctionModel(script))
    result = built.run_sync("extract this document", deps=ExtractionState(document_id="doc-1"))

    assert calls == ["survey_layout_tool", "validate_extraction"]
    assert result.output == '{"status": "done"}'
