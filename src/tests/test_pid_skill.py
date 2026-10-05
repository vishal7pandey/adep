"""Tests for P&ID to DEXPI skill and contract [BLK-111].

Tests cover:
- PnIDContract structure (node types, edge types, topology rules, output formats)
- PnIDSkill configuration (prompt, probe order, invariants, failure actions)
- Topology invariant logic (valve connections, ISA-5.1 tags, control loops, orphan pipes)
- Registry resolution (skill + template in run_engine)
- Prebuilt definition registration
- E2E smoke test: build_graph → validate_topology → serialize_graph
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.skills.pid_diagram import (
    PnIDSkill,
    _every_valve_connected,
    _isa_51_tag_format,
    _control_loop_completeness,
    _no_orphan_pipes,
)
from src.templates.pid_diagram import PnIDContract
from src.agent.validator import GapType


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


class MockFieldValue:
    """Mock FieldValue for invariant testing."""

    def __init__(self, value):
        self.value = value


def mock_graph(graph: dict) -> dict:
    """Wrap a graph dict in a MockFieldValue for invariant testing."""
    return {"graph": MockFieldValue(graph)}


# ---------------------------------------------------------------------------
# Contract structure tests
# ---------------------------------------------------------------------------


class TestPnIDContract:
    """Verify PnIDContract structure."""

    def test_is_graph_extraction_contract(self):
        from src.templates.base import GraphExtractionContract

        assert isinstance(PnIDContract(), GraphExtractionContract)

    def test_task_type(self):
        c = PnIDContract()
        assert c.task_type == "graph_extraction"

    def test_node_types(self):
        c = PnIDContract()
        node_type_names = {nt["name"] for nt in c.node_types}
        assert node_type_names == {"equipment", "valve", "instrument", "pipe", "fitting"}

    def test_valve_subtypes(self):
        c = PnIDContract()
        valve = next(nt for nt in c.node_types if nt["name"] == "valve")
        assert set(valve["subtypes"]) == {"manual", "control", "check", "relief"}

    def test_equipment_subtypes(self):
        c = PnIDContract()
        eq = next(nt for nt in c.node_types if nt["name"] == "equipment")
        assert "vessel" in eq["subtypes"]
        assert "pump" in eq["subtypes"]

    def test_edge_types(self):
        c = PnIDContract()
        edge_type_names = {et["name"] for et in c.edge_types}
        assert edge_type_names == {"connected_to", "branches_from", "measures", "controls"}

    def test_topology_rules(self):
        c = PnIDContract()
        rule_names = {r["name"] for r in c.topology_rules}
        assert "every_valve_connected_to_pipe" in rule_names
        assert "isa_51_tag_format" in rule_names
        assert "control_loop_completeness" in rule_names
        assert "no_orphan_pipes" in rule_names

    def test_output_formats(self):
        c = PnIDContract()
        assert "dexpi_xml" in c.output_formats
        assert "smart_pid_json" in c.output_formats
        assert "graphml" in c.output_formats


# ---------------------------------------------------------------------------
# Skill configuration tests
# ---------------------------------------------------------------------------


class TestPnIDSkillConfig:
    """Verify PnIDSkill configuration."""

    def test_name(self):
        assert PnIDSkill.name == "pid_to_dexpi"

    def test_system_prompt(self):
        assert len(PnIDSkill.system_prompt) > 100
        assert "detect_symbols" in PnIDSkill.system_prompt
        assert "build_graph" in PnIDSkill.system_prompt
        assert "serialize_graph" in PnIDSkill.system_prompt
        assert "DEXPI" in PnIDSkill.system_prompt

    def test_tool_preferences(self):
        assert "symbol_detection" in PnIDSkill.tool_preferences
        assert PnIDSkill.tool_preferences["symbol_detection"] == "detect_symbols"

    def test_probe_order(self):
        assert len(PnIDSkill.probe_order) >= 7
        region_types = [r for r, _ in PnIDSkill.probe_order]
        assert "title_block" in region_types
        assert "main_diagram" in region_types
        assert "connections" in region_types
        assert "serialize" in region_types

    def test_invariants(self):
        assert len(PnIDSkill.invariants) == 4
        inv_names = [inv.name for inv in PnIDSkill.invariants]
        assert "every_valve_connected_to_pipe" in inv_names
        assert "isa_51_tag_format" in inv_names
        assert "control_loop_completeness" in inv_names
        assert "no_orphan_pipes" in inv_names

    def test_failure_actions(self):
        assert GapType.SYMBOL_UNCLASSIFIED in PnIDSkill.failure_actions
        assert GapType.TAG_UNREADABLE in PnIDSkill.failure_actions
        assert GapType.CONNECTION_AMBIGUOUS in PnIDSkill.failure_actions
        assert GapType.TOPOLOGY_VIOLATION in PnIDSkill.failure_actions

    def test_known_failures(self):
        assert len(PnIDSkill.known_failures) > 0
        assert "deskew" in PnIDSkill.known_failures.lower()

    def test_confidence_overrides(self):
        assert "graph" in PnIDSkill.confidence_overrides


# ---------------------------------------------------------------------------
# Topology invariant tests
# ---------------------------------------------------------------------------


class TestEveryValveConnected:
    """Verify every_valve_connected_to_pipe invariant."""

    def test_valid_all_valves_connected(self):
        graph = {
            "nodes": [
                {"id": "v1", "type": "valve"},
                {"id": "p1", "type": "pipe"},
                {"id": "p2", "type": "pipe"},
            ],
            "edges": [
                {"source": "v1", "target": "p1"},
                {"source": "v2", "target": "p2"} if False else {"source": "p2", "target": "v1"},
            ],
        }
        ok, msg = _every_valve_connected(mock_graph(graph))
        assert ok is True

    def test_invalid_valve_not_connected(self):
        graph = {
            "nodes": [
                {"id": "v1", "type": "valve"},
                {"id": "v2", "type": "valve"},
                {"id": "p1", "type": "pipe"},
            ],
            "edges": [
                {"source": "v1", "target": "p1"},
            ],
        }
        ok, msg = _every_valve_connected(mock_graph(graph))
        assert ok is False
        assert "v2" in msg

    def test_invalid_valve_connected_but_not_to_pipe(self):
        graph = {
            "nodes": [
                {"id": "v1", "type": "valve"},
                {"id": "e1", "type": "equipment"},
            ],
            "edges": [
                {"source": "v1", "target": "e1"},
            ],
        }
        ok, msg = _every_valve_connected(mock_graph(graph))
        assert ok is False

    def test_passes_when_no_valves(self):
        graph = {"nodes": [{"id": "p1", "type": "pipe"}], "edges": []}
        ok, msg = _every_valve_connected(mock_graph(graph))
        assert ok is True

    def test_passes_when_no_graph(self):
        ok, msg = _every_valve_connected({})
        assert ok is True


class TestIsaTagFormat:
    """Verify ISA-5.1 tag format invariant."""

    def test_valid_tags(self):
        graph = {
            "nodes": [
                {"id": "i1", "type": "instrument", "tag": "FT-101"},
                {"id": "i2", "type": "instrument", "tag": "PIC-205"},
            ],
            "edges": [],
        }
        ok, msg = _isa_51_tag_format(mock_graph(graph))
        assert ok is True

    def test_invalid_tag_format(self):
        graph = {
            "nodes": [
                {"id": "i1", "type": "instrument", "tag": "flow-transmitter-101"},
            ],
            "edges": [],
        }
        ok, msg = _isa_51_tag_format(mock_graph(graph))
        assert ok is False
        assert "flow-transmitter-101" in msg

    def test_no_tag_passes(self):
        graph = {
            "nodes": [
                {"id": "i1", "type": "instrument"},
            ],
            "edges": [],
        }
        ok, msg = _isa_51_tag_format(mock_graph(graph))
        assert ok is True

    def test_non_instrument_tags_ignored(self):
        graph = {
            "nodes": [
                {"id": "v1", "type": "valve", "tag": "V-001"},
            ],
            "edges": [],
        }
        ok, msg = _isa_51_tag_format(mock_graph(graph))
        assert ok is True


class TestControlLoopCompleteness:
    """Verify control loop completeness invariant."""

    def test_valid_complete_loop(self):
        graph = {
            "nodes": [
                {"id": "ft1", "type": "instrument", "tag": "FT-101"},
                {"id": "fic1", "type": "instrument", "tag": "FIC-101"},
                {"id": "v1", "type": "valve"},
            ],
            "edges": [
                {"source": "ft1", "target": "fic1"},
                {"source": "fic1", "target": "v1"},
            ],
        }
        ok, msg = _control_loop_completeness(mock_graph(graph))
        assert ok is True

    def test_invalid_missing_sensor(self):
        graph = {
            "nodes": [
                {"id": "fic1", "type": "instrument", "tag": "FIC-101"},
                {"id": "v1", "type": "valve"},
            ],
            "edges": [
                {"source": "fic1", "target": "v1"},
            ],
        }
        ok, msg = _control_loop_completeness(mock_graph(graph))
        assert ok is False
        assert "sensor" in msg

    def test_invalid_missing_final_element(self):
        graph = {
            "nodes": [
                {"id": "ft1", "type": "instrument", "tag": "FT-101"},
                {"id": "fic1", "type": "instrument", "tag": "FIC-101"},
            ],
            "edges": [
                {"source": "ft1", "target": "fic1"},
            ],
        }
        ok, msg = _control_loop_completeness(mock_graph(graph))
        assert ok is False
        assert "final_element" in msg

    def test_passes_when_no_controllers(self):
        graph = {
            "nodes": [
                {"id": "ft1", "type": "instrument", "tag": "FT-101"},
            ],
            "edges": [],
        }
        ok, msg = _control_loop_completeness(mock_graph(graph))
        assert ok is True


class TestNoOrphanPipes:
    """Verify no_orphan_pipes invariant."""

    def test_valid_connected_pipes(self):
        graph = {
            "nodes": [
                {"id": "p1", "type": "pipe"},
                {"id": "v1", "type": "valve"},
            ],
            "edges": [
                {"source": "p1", "target": "v1"},
            ],
        }
        ok, msg = _no_orphan_pipes(mock_graph(graph))
        assert ok is True

    def test_invalid_orphan_pipe(self):
        graph = {
            "nodes": [
                {"id": "p1", "type": "pipe"},
                {"id": "p2", "type": "pipe"},
                {"id": "v1", "type": "valve"},
            ],
            "edges": [
                {"source": "p1", "target": "v1"},
            ],
        }
        ok, msg = _no_orphan_pipes(mock_graph(graph))
        assert ok is False
        assert "p2" in msg

    def test_passes_when_no_pipes(self):
        graph = {"nodes": [{"id": "v1", "type": "valve"}], "edges": []}
        ok, msg = _no_orphan_pipes(mock_graph(graph))
        assert ok is True


# ---------------------------------------------------------------------------
# Registry resolution tests
# ---------------------------------------------------------------------------


class TestRegistryResolution:
    """Verify P&ID skill and template are registered."""

    def test_skill_resolvable(self):
        from src.api.run_engine import resolve_skill

        skill = resolve_skill("pid_to_dexpi")
        assert skill is not None
        assert skill.name == "pid_to_dexpi"

    def test_template_resolvable(self):
        from src.api.run_engine import resolve_template

        template_cls = resolve_template("pid_to_dexpi")
        assert template_cls is not None


# ---------------------------------------------------------------------------
# Prebuilt definition tests
# ---------------------------------------------------------------------------


class TestPrebuiltDefinition:
    """Verify P&ID prebuilt definition is registered."""

    def test_definition_present(self):
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS

        def_ids = {d["id"] for d in PREBUILT_DEFINITIONS}
        assert "def-pnid-to-dexpi" in def_ids

    def test_definition_has_task_type(self):
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS

        defn = next(d for d in PREBUILT_DEFINITIONS if d["id"] == "def-pnid-to-dexpi")
        assert defn["task_type"] == "graph_extraction"

    def test_definition_has_graph_tools(self):
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS

        defn = next(d for d in PREBUILT_DEFINITIONS if d["id"] == "def-pnid-to-dexpi")
        assert "detect_symbols" in defn["tool_names"]
        assert "build_graph" in defn["tool_names"]
        assert "validate_topology" in defn["tool_names"]
        assert "serialize_graph" in defn["tool_names"]

    def test_skill_in_prebuilt_skills(self):
        from src.definitions.prebuilt import PREBUILT_SKILLS

        skill_ids = {s["id"] for s in PREBUILT_SKILLS}
        assert "pid_to_dexpi" in skill_ids

    def test_template_in_prebuilt_templates(self):
        from src.definitions.prebuilt import PREBUILT_TEMPLATES

        template_ids = {t["id"] for t in PREBUILT_TEMPLATES}
        assert "pid_to_dexpi" in template_ids


# ---------------------------------------------------------------------------
# E2E smoke test: full pipeline with mocked tools
# ---------------------------------------------------------------------------


class TestE2EPipeline:
    """E2E smoke test: build_graph → validate_topology → serialize_graph."""

    def test_full_pipeline_produces_valid_dexpi(self):
        from src.tools.graph.graph_building import build_graph, validate_topology
        from src.tools.graph.serialization import serialize_graph

        symbols = [
            {"id": "v1", "class": "valve", "bbox": (10, 10, 50, 50), "confidence": 0.9},
            {"id": "p1", "class": "pipe", "bbox": (60, 10, 200, 50), "confidence": 0.85},
            {
                "id": "ft1",
                "class": "instrument",
                "bbox": (10, 60, 50, 100),
                "tag": "FT-101",
                "confidence": 0.88,
            },
            {
                "id": "fic1",
                "class": "instrument",
                "bbox": (60, 60, 100, 100),
                "tag": "FIC-101",
                "confidence": 0.87,
            },
        ]

        connections = [
            {"from_id": "v1", "to_id": "p1", "type": "connected_to", "confidence": 0.8},
            {"from_id": "ft1", "to_id": "fic1", "type": "measures", "confidence": 0.85},
            {"from_id": "fic1", "to_id": "v1", "type": "controls", "confidence": 0.82},
        ]

        # Step 1: Build graph
        graph_result = build_graph(symbols=symbols, connections=connections)
        assert graph_result.ok
        graph = graph_result.data

        # Step 2: Validate topology
        topo_result = validate_topology(graph=graph)
        assert topo_result.ok

        # Step 3: Serialize to DEXPI XML
        dexpi_result = serialize_graph(graph=graph, format="dexpi_xml")
        assert dexpi_result.ok
        dexpi_content = dexpi_result.data["content"]
        assert "<DEXPI" in dexpi_content or "<Plant" in dexpi_content
        assert "FT-101" in dexpi_content

    def test_full_pipeline_produces_valid_graphml(self):
        from src.tools.graph.graph_building import build_graph
        from src.tools.graph.serialization import serialize_graph

        symbols = [
            {"id": "v1", "class": "valve", "bbox": (10, 10, 50, 50), "confidence": 0.9},
            {"id": "p1", "class": "pipe", "bbox": (60, 10, 200, 50), "confidence": 0.85},
        ]
        connections = [
            {"from_id": "v1", "to_id": "p1", "type": "connected_to", "confidence": 0.8},
        ]

        graph_result = build_graph(symbols=symbols, connections=connections)
        assert graph_result.ok

        graphml_result = serialize_graph(graph=graph_result.data, format="graphml")
        assert graphml_result.ok
        graphml_content = graphml_result.data["content"]
        assert "<graphml" in graphml_content
        assert "<node" in graphml_content
        assert "<edge" in graphml_content

    def test_full_pipeline_produces_smart_pid_json(self):
        from src.tools.graph.graph_building import build_graph
        from src.tools.graph.serialization import serialize_graph

        symbols = [
            {"id": "v1", "class": "valve", "bbox": (10, 10, 50, 50), "confidence": 0.9},
            {"id": "p1", "class": "pipe", "bbox": (60, 10, 200, 50), "confidence": 0.85},
        ]
        connections = [
            {"from_id": "v1", "to_id": "p1", "type": "connected_to", "confidence": 0.8},
        ]

        graph_result = build_graph(symbols=symbols, connections=connections)
        assert graph_result.ok

        json_result = serialize_graph(graph=graph_result.data, format="smart_pid_json")
        assert json_result.ok
        import json

        data = json.loads(json_result.data["content"])
        assert "components" in data
        assert "connections" in data
