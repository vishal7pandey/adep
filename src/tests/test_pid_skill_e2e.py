"""End-to-end proof for the new engine (ADE-40): the real pid-dexpi-digitizer skill loads, and
build_agent() drives a real imported document through survey -> validate_extraction -> to_dexpi_xml.

This is the one test in the engine suite that intentionally exercises the real repo-root skills/
directory (via engine_skills.load_skill) rather than monkeypatching it - proving the real SKILL.md +
schema.json parse is the point. Everything else is hermetic: DocumentStore is pointed at tmp_path
(never .adep/), the VLM call ADE-38's survey_layout makes is monkeypatched, and the model is a
pydantic-ai FunctionModel scripting the tool-call sequence - no network, no live Azure/LLM.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

from src.documents.store import DocumentStore
from src.engine import agent as engine_agent
from src.engine import skills as engine_skills
from src.engine import tools as engine_tools
from src.engine.agent import ExtractionState

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_PID = _REPO_ROOT / "sample-data" / "pid-diagrams" / "sample-pid-01.jpg"

FIXED_EXTRACTION = {
    "header": {"drawing_number": "D-100", "drawing_title": "Sample P&ID", "revision": "A"},
    "nodes": [{"id": "Eq_1", "tag": "P-101", "type": "Pump"}],
    "edges": [{"id": "E_1", "from_id": "Eq_1", "to_id": "Eq_1"}],
}


def test_skill_loads_with_schema_and_invariants():
    skill = engine_skills.load_skill("pid-dexpi-digitizer")

    assert skill is not None
    assert skill.modality == "graph_digitization"
    assert skill.schema is not None
    assert len(skill.invariants) == 4
    assert {inv["name"] for inv in skill.invariants} == {
        "nodes_non_empty",
        "edges_non_empty",
        "all_nodes_have_tag_and_type",
        "all_edges_have_endpoints",
    }


def test_schema_matches_pid_graph_shape():
    skill = engine_skills.load_skill("pid-dexpi-digitizer")

    props = skill.schema["properties"]
    expected_keys = ("header", "nodes", "valves", "instruments", "off_page_connectors", "edges")
    for key in (*expected_keys, "dexpi_xml"):
        assert key in props

    node_schema = props["nodes"]["items"]
    assert set(node_schema["required"]) == {"id", "tag", "type"}
    edge_schema = props["edges"]["items"]
    assert set(edge_schema["required"]) == {"id", "from_id", "to_id"}


def test_engine_runs_end_to_end_against_a_real_pid_sample(tmp_path, monkeypatch):
    store = DocumentStore(base_dir=tmp_path)

    def _fake_survey_layout(document_id, page_num=1):
        return {"zones": [], "zone_count": 0}

    monkeypatch.setattr(engine_tools, "survey_layout", _fake_survey_layout)

    meta = store.import_document(SAMPLE_PID)

    calls: list[str] = []
    tool_returns: dict[str, dict] = {}

    def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        last = messages[-1]
        if isinstance(last, ModelRequest):
            for part in last.parts:
                if isinstance(part, ToolReturnPart):
                    tool_returns[part.tool_name] = part.content
        if not calls:
            calls.append("survey_layout_tool")
            return ModelResponse(
                parts=[
                    ToolCallPart(tool_name="survey_layout_tool", args={"document_id": meta.doc_id})
                ]
            )
        if calls == ["survey_layout_tool"]:
            calls.append("validate_extraction")
            return ModelResponse(
                parts=[
                    ToolCallPart(tool_name="validate_extraction", args={"data": FIXED_EXTRACTION})
                ]
            )
        if calls == ["survey_layout_tool", "validate_extraction"]:
            calls.append("to_dexpi_xml")
            return ModelResponse(
                parts=[ToolCallPart(tool_name="to_dexpi_xml", args={"data": FIXED_EXTRACTION})]
            )
        return ModelResponse(parts=[TextPart('{"status": "done"}')])

    built = engine_agent.build_agent(model=FunctionModel(script))
    result = built.run_sync(
        "digitize this P&ID",
        deps=ExtractionState(document_id=meta.doc_id, skill_id="pid-dexpi-digitizer"),
    )

    assert calls == ["survey_layout_tool", "validate_extraction", "to_dexpi_xml"]
    assert result.output == '{"status": "done"}'
    assert tool_returns["validate_extraction"]["valid"] is True
    assert tool_returns["to_dexpi_xml"] == {
        "error": "DEXPI serialization is not available yet (ADE-14)",
        "dexpi_xml": None,
    }
