"""Tests for graph extraction tools [BLK-110].

Tests cover:
- ISA-5.1 tag parsing (deterministic)
- build_graph (deterministic)
- validate_topology (deterministic, all 4 rules)
- serialize_graph (json, graphml, dexpi_xml, smart_pid_json)
- detect_symbols, classify_symbol (mocked VLM)
- detect_connections, trace_line (mocked VLM)
- read_tag (mocked OCR + crop)
- Integration: full pipeline detect → read_tag → build → validate → serialize
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from src.tools.base import ToolResult, Grounding
from src.tools.graph.tag_reading import parse_isa_tag, read_tag
from src.tools.graph.graph_building import build_graph, validate_topology
from src.tools.graph.serialization import serialize_graph
from src.tools.graph.symbol_detection import detect_symbols, classify_symbol
from src.tools.graph.connection import detect_connections, trace_line


# ---------------------------------------------------------------------------
# ISA-5.1 tag parsing tests
# ---------------------------------------------------------------------------

class TestIsaTagParsing:
    """Verify ISA-5.1 tag parsing (deterministic)."""

    def test_ft_101(self):
        result = parse_isa_tag("FT-101")
        assert result["function"] == "F"
        assert result["modifier"] == "T"
        assert result["number"] == "101"
        assert result["function_meaning"] == "Flow"
        assert result["modifier_meaning"] == "Transmitter"
        assert result["parse_error"] is False

    def test_pic_202(self):
        result = parse_isa_tag("PIC-202")
        assert result["function"] == "P"
        assert result["modifier"] == "IC"
        assert result["number"] == "202"
        assert result["function_meaning"] == "Pressure"
        assert "Indicator" in result["modifier_meaning"]
        assert "Controller" in result["modifier_meaning"]

    def test_lv_303(self):
        result = parse_isa_tag("LV-303")
        assert result["function"] == "L"
        assert result["modifier"] == "V"
        assert result["number"] == "303"
        assert result["function_meaning"] == "Level"
        assert result["modifier_meaning"] == "Valve"

    def test_no_dash(self):
        result = parse_isa_tag("FT101")
        assert result["parse_error"] is False
        assert result["function"] == "F"
        assert result["number"] == "101"

    def test_invalid_tag(self):
        result = parse_isa_tag("hello")
        assert result["parse_error"] is True
        assert result["function"] is None

    def test_lowercase_normalized(self):
        result = parse_isa_tag("ft-101")
        assert result["tag"] == "FT-101"
        assert result["function"] == "F"

    def test_single_letter(self):
        result = parse_isa_tag("T-501")
        assert result["function"] == "T"
        assert result["modifier"] is None
        assert result["function_meaning"] == "Temperature"


# ---------------------------------------------------------------------------
# build_graph tests
# ---------------------------------------------------------------------------

class TestBuildGraph:
    """Verify graph building from symbols and connections."""

    def test_builds_nodes_and_edges(self):
        symbols = [
            {"id": "sym_0", "bbox": (10, 10, 50, 50), "class": "valve", "confidence": 0.9},
            {"id": "sym_1", "bbox": (100, 10, 140, 50), "class": "pump", "confidence": 0.85},
        ]
        connections = [
            {"id": "conn_0", "from_id": "sym_0", "to_id": "sym_1", "type": "pipe", "confidence": 0.8},
        ]
        result = build_graph(symbols=symbols, connections=connections)
        assert result.ok
        graph = result.data
        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1
        assert graph["nodes"][0]["id"] == "sym_0"
        assert graph["nodes"][0]["type"] == "valve"
        assert graph["edges"][0]["source"] == "sym_0"
        assert graph["edges"][0]["target"] == "sym_1"

    def test_empty_inputs(self):
        result = build_graph()
        assert result.ok
        assert result.data == {"nodes": [], "edges": []}

    def test_preserves_tag_data(self):
        symbols = [
            {"id": "sym_0", "bbox": (10, 10, 50, 50), "class": "instrument",
             "tag": "FT-101", "tag_components": {"function": "F", "modifier": "T"}},
        ]
        result = build_graph(symbols=symbols)
        assert result.ok
        assert result.data["nodes"][0]["tag"] == "FT-101"


# ---------------------------------------------------------------------------
# validate_topology tests
# ---------------------------------------------------------------------------

class TestValidateTopology:
    """Verify topology validation rules."""

    def test_valid_graph_no_violations(self):
        graph = {
            "nodes": [
                {"id": "v1", "type": "valve"},
                {"id": "p1", "type": "pump"},
            ],
            "edges": [
                {"source": "v1", "target": "p1", "type": "pipe"},
            ],
        }
        result = validate_topology(graph=graph)
        assert result.ok
        assert result.data["ok"] is True
        assert result.data["violations"] == []

    def test_orphan_node_detected(self):
        graph = {
            "nodes": [
                {"id": "v1", "type": "valve"},
                {"id": "orphan", "type": "pump"},
            ],
            "edges": [],
        }
        result = validate_topology(graph=graph)
        assert result.ok
        assert result.data["ok"] is False
        violations = result.data["violations"]
        assert any(v["rule"] == "no_orphans" for v in violations)

    def test_unconnected_valve_detected(self):
        graph = {
            "nodes": [
                {"id": "v1", "type": "gate_valve"},
                {"id": "p1", "type": "pump"},
            ],
            "edges": [
                {"source": "v1", "target": "p1", "type": "signal"},
            ],
        }
        result = validate_topology(graph=graph)
        assert result.ok
        assert result.data["ok"] is False
        violations = result.data["violations"]
        assert any(v["rule"] == "valve_connected" for v in violations)

    def test_invalid_isa_tag_detected(self):
        graph = {
            "nodes": [
                {"id": "i1", "type": "instrument", "tag": "hello",
                 "tag_components": {"parse_error": True}},
                {"id": "v1", "type": "valve"},
            ],
            "edges": [
                {"source": "i1", "target": "v1", "type": "pipe"},
            ],
        }
        result = validate_topology(graph=graph)
        assert result.ok
        violations = result.data["violations"]
        assert any(v["rule"] == "isa_tag_format" for v in violations)

    def test_control_loop_incomplete(self):
        graph = {
            "nodes": [
                {"id": "tx1", "type": "instrument", "tag": "FT-101",
                 "tag_components": {"function": "F", "modifier": "T", "parse_error": False}},
            ],
            "edges": [],
        }
        result = validate_topology(graph=graph)
        assert result.ok
        violations = result.data["violations"]
        assert any(v["rule"] == "control_loop" for v in violations)

    def test_specific_rules_only(self):
        graph = {
            "nodes": [
                {"id": "orphan", "type": "pump"},
                {"id": "v1", "type": "valve"},
            ],
            "edges": [],
        }
        # Only check no_orphans, skip valve_connected
        result = validate_topology(graph=graph, rules=["no_orphans"])
        assert result.ok
        violations = result.data["violations"]
        assert all(v["rule"] == "no_orphans" for v in violations)


# ---------------------------------------------------------------------------
# serialize_graph tests
# ---------------------------------------------------------------------------

class TestSerializeGraph:
    """Verify graph serialization to multiple formats."""

    @pytest.fixture
    def sample_graph(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"id": "v1", "type": "valve", "bbox": (10, 10, 50, 50), "tag": "V-101"},
                {"id": "p1", "type": "pump", "bbox": (100, 10, 140, 50), "tag": "P-201"},
            ],
            "edges": [
                {"id": "e1", "source": "v1", "target": "p1", "type": "pipe"},
            ],
        }

    def test_json_format(self, sample_graph):
        result = serialize_graph(graph=sample_graph, format="json")
        assert result.ok
        assert result.data["format"] == "json"
        parsed = json.loads(result.data["content"])
        assert len(parsed["nodes"]) == 2
        assert len(parsed["edges"]) == 1

    def test_graphml_format(self, sample_graph):
        result = serialize_graph(graph=sample_graph, format="graphml")
        assert result.ok
        assert result.data["format"] == "graphml"
        content = result.data["content"]
        assert "<?xml" in content
        assert "<graphml" in content
        assert "<node" in content
        assert "<edge" in content
        assert 'id="v1"' in content

    def test_dexpi_xml_format(self, sample_graph):
        result = serialize_graph(graph=sample_graph, format="dexpi_xml")
        assert result.ok
        assert result.data["format"] == "dexpi_xml"
        content = result.data["content"]
        assert "<?xml" in content
        assert "<DEXPI" in content
        assert "<Plant>" in content
        assert "<Equipment>" in content
        assert "<Piping>" in content
        assert "V-101" in content

    def test_smart_pid_json_format(self, sample_graph):
        result = serialize_graph(graph=sample_graph, format="smart_pid_json")
        assert result.ok
        assert result.data["format"] == "smart_pid_json"
        parsed = json.loads(result.data["content"])
        assert parsed["format"] == "smart_pid_json"
        assert len(parsed["components"]) == 2
        assert len(parsed["connections"]) == 1
        assert parsed["components"][0]["geometry"]["x"] == 10

    def test_unknown_format_returns_error(self, sample_graph):
        result = serialize_graph(graph=sample_graph, format="unknown")
        assert not result.ok
        assert "Unknown" in result.error

    def test_xml_escaping(self):
        graph = {
            "nodes": [{"id": "n<>&\"'", "type": "valve"}],
            "edges": [],
        }
        result = serialize_graph(graph=graph, format="graphml")
        content = result.data["content"]
        assert "&lt;" in content
        assert "&gt;" in content
        assert "&amp;" in content
        assert "&quot;" in content
        assert "&apos;" in content


# ---------------------------------------------------------------------------
# detect_symbols tests (mocked VLM)
# ---------------------------------------------------------------------------

class TestDetectSymbols:
    """Verify symbol detection with mocked VLM."""

    def test_detects_symbols(self):
        mock_response = json.dumps([
            {"bbox": [10, 10, 50, 50], "class": "valve", "confidence": 0.9},
            {"bbox": [100, 10, 140, 50], "class": "pump", "confidence": 0.85},
        ])
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=True, data=mock_response, tool="vlm")
            result = detect_symbols(image_path="test.png")
            assert result.ok
            symbols = result.data
            assert len(symbols) == 2
            assert symbols[0]["id"] == "sym_0"
            assert symbols[0]["class"] == "valve"
            assert symbols[1]["id"] == "sym_1"
            assert symbols[1]["class"] == "pump"

    def test_vlm_failure_returns_error(self):
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=False, error="API timeout", tool="vlm")
            result = detect_symbols(image_path="test.png")
            assert not result.ok
            assert "VLM call failed" in result.error

    def test_invalid_json_returns_error(self):
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=True, data="not json", tool="vlm")
            result = detect_symbols(image_path="test.png")
            assert not result.ok
            assert "Failed to parse" in result.error


# ---------------------------------------------------------------------------
# classify_symbol tests (mocked VLM + crop)
# ---------------------------------------------------------------------------

class TestClassifySymbol:
    """Verify symbol classification with mocked VLM."""

    def test_classifies_symbol(self):
        with patch("src.providers.image_cv.crop") as mock_crop, \
             patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_crop.return_value = ToolResult(ok=True, data="cropped.png", tool="crop")
            mock_vlm.return_value = ToolResult(
                ok=True, data=json.dumps({"class": "gate_valve", "confidence": 0.92}),
                tool="vlm",
            )
            result = classify_symbol(image_path="test.png", bbox=(10, 10, 50, 50))
            assert result.ok
            assert result.data["class"] == "gate_valve"
            assert result.data["confidence"] == 0.92


# ---------------------------------------------------------------------------
# detect_connections tests (mocked VLM)
# ---------------------------------------------------------------------------

class TestDetectConnections:
    """Verify connection detection with mocked VLM."""

    def test_detects_connections(self):
        symbols = [
            {"id": "sym_0", "bbox": (10, 10, 50, 50), "class": "valve"},
            {"id": "sym_1", "bbox": (100, 10, 140, 50), "class": "pump"},
        ]
        mock_response = json.dumps([
            {"from_id": "sym_0", "to_id": "sym_1", "path_bbox": [[30, 30, 80, 40]], "type": "pipe", "confidence": 0.85},
        ])
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=True, data=mock_response, tool="vlm")
            result = detect_connections(image_path="test.png", symbols=symbols)
            assert result.ok
            conns = result.data
            assert len(conns) == 1
            assert conns[0]["from_id"] == "sym_0"
            assert conns[0]["to_id"] == "sym_1"
            assert conns[0]["id"] == "conn_0"

    def test_no_symbols_returns_error(self):
        result = detect_connections(image_path="test.png", symbols=[])
        assert not result.ok
        assert "No symbols" in result.error


# ---------------------------------------------------------------------------
# trace_line tests (mocked VLM)
# ---------------------------------------------------------------------------

class TestTraceLine:
    """Verify line tracing with mocked VLM."""

    def test_traces_line(self):
        mock_response = json.dumps({
            "bboxes": [[10, 30, 50, 40], [50, 30, 90, 40]],
            "end_point": [90, 35],
            "connected_to_id": "sym_1",
            "confidence": 0.8,
        })
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=True, data=mock_response, tool="vlm")
            result = trace_line(image_path="test.png", start_point=(10, 35))
            assert result.ok
            assert len(result.data["bboxes"]) == 2
            assert result.data["connected_to_id"] == "sym_1"

    def test_bbox_start_point_converted_to_center(self):
        mock_response = json.dumps({
            "bboxes": [], "end_point": [0, 0], "confidence": 0.5,
        })
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=True, data=mock_response, tool="vlm")
            trace_line(image_path="test.png", start_point=(10, 10, 50, 50))
            # Check the prompt contains the center point
            call_args = mock_vlm.call_args
            assert "30, 30" in call_args.kwargs["question"]


# ---------------------------------------------------------------------------
# read_tag tests (mocked OCR + crop)
# ---------------------------------------------------------------------------

class TestReadTag:
    """Verify tag reading with mocked OCR."""

    def test_reads_and_parses_tag(self):
        with patch("src.providers.image_cv.crop") as mock_crop, \
             patch("src.providers.ocr_tesseract.ocr") as mock_ocr, \
             patch("src.config.settings") as mock_settings:
            mock_settings.ocr_provider = "tesseract"
            mock_crop.return_value = ToolResult(ok=True, data="cropped.png", tool="crop")
            mock_ocr.return_value = ToolResult(
                ok=True, data="FT-101",
                grounding=Grounding(bbox=(10, 10, 50, 30), source_tool="ocr", confidence=0.95),
                tool="ocr",
            )
            result = read_tag(image_path="test.png", bbox=(10, 10, 50, 30))
            assert result.ok
            assert result.data["tag"] == "FT-101"
            assert result.data["parsed_components"]["function"] == "F"
            assert result.data["parsed_components"]["modifier"] == "T"
            assert result.data["confidence"] == 0.95

    def test_empty_ocr_returns_error(self):
        with patch("src.providers.image_cv.crop") as mock_crop, \
             patch("src.providers.ocr_tesseract.ocr") as mock_ocr, \
             patch("src.config.settings") as mock_settings:
            mock_settings.ocr_provider = "tesseract"
            mock_crop.return_value = ToolResult(ok=True, data="cropped.png", tool="crop")
            mock_ocr.return_value = ToolResult(ok=True, data="", tool="ocr")
            result = read_tag(image_path="test.png", bbox=(10, 10, 50, 30))
            assert not result.ok
            assert "No text" in result.error

    def test_crop_failure_returns_error(self):
        with patch("src.providers.image_cv.crop") as mock_crop, \
             patch("src.config.settings") as mock_settings:
            mock_settings.ocr_provider = "tesseract"
            mock_crop.return_value = ToolResult(ok=False, error="file not found", tool="crop")
            result = read_tag(image_path="test.png", bbox=(10, 10, 50, 30))
            assert not result.ok
            assert "crop" in result.error.lower()


# ---------------------------------------------------------------------------
# Integration test: full pipeline
# ---------------------------------------------------------------------------

class TestGraphExtractionPipeline:
    """Integration test: detect → read_tag → build → validate → serialize."""

    def test_full_pipeline_mocked(self):
        # Step 1: detect_symbols
        mock_symbols = json.dumps([
            {"bbox": [10, 10, 50, 50], "class": "valve", "confidence": 0.9},
            {"bbox": [100, 10, 140, 50], "class": "pump", "confidence": 0.85},
            {"bbox": [50, 100, 90, 130], "class": "instrument", "confidence": 0.8},
        ])
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=True, data=mock_symbols, tool="vlm")
            sym_result = detect_symbols(image_path="pid.png")
            assert sym_result.ok
            symbols = sym_result.data
            assert len(symbols) == 3

        # Step 2: detect_connections
        mock_conns = json.dumps([
            {"from_id": "sym_0", "to_id": "sym_1", "type": "pipe", "confidence": 0.85},
            {"from_id": "sym_2", "to_id": "sym_0", "type": "pipe", "confidence": 0.8},
        ])
        with patch("src.providers.vlm_azure.vlm") as mock_vlm:
            mock_vlm.return_value = ToolResult(ok=True, data=mock_conns, tool="vlm")
            conn_result = detect_connections(image_path="pid.png", symbols=symbols)
            assert conn_result.ok
            connections = conn_result.data
            assert len(connections) == 2

        # Step 3: build_graph
        graph_result = build_graph(symbols=symbols, connections=connections)
        assert graph_result.ok
        graph = graph_result.data
        assert len(graph["nodes"]) == 3
        assert len(graph["edges"]) == 2

        # Step 4: validate_topology
        val_result = validate_topology(graph=graph)
        assert val_result.ok
        # No orphan nodes since all are connected
        assert val_result.data["ok"] is True

        # Step 5: serialize_graph (all formats)
        for fmt in ["json", "graphml", "dexpi_xml", "smart_pid_json"]:
            ser_result = serialize_graph(graph=graph, format=fmt)
            assert ser_result.ok
            assert ser_result.data["format"] == fmt
            assert ser_result.data["content"]
