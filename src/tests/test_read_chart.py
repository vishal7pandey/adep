"""Tests for read_chart tool [BLK-040, TS].

Tests cover:
- Structured data series output
- Chart type hint integration
- Grounding bbox from image dimensions
- VLM failure handling (rate limit, invalid JSON, missing series)
- ToolSpec registration in build_tool_registry
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.providers.vlm_azure import read_chart, _CHART_SYSTEM_PROMPT
from src.tools.base import ToolResult


class TestReadChartStructured:
    """Verify read_chart returns structured data, not free text."""

    @patch("src.providers.vlm_azure._call_vlm")
    @patch("src.providers.vlm_azure.Grounding")
    def test_returns_structured_dict(self, mock_grounding, mock_vlm):
        """read_chart returns a dict with series, x_axis, y_axis, chart_type."""
        mock_vlm.return_value = json.dumps({
            "series": [{"label": "Consumption", "values": [100, 200, 150]}],
            "x_axis": ["Jan", "Feb", "Mar"],
            "y_axis": {"label": "kWh", "min": 0, "max": 250},
            "chart_type": "bar",
        })
        mock_grounding.return_value = MagicMock()

        result = read_chart("test.png")
        assert result.ok is True
        assert isinstance(result.data, dict)
        assert "series" in result.data
        assert len(result.data["series"]) == 1
        assert result.data["series"][0]["values"] == [100, 200, 150]
        assert result.data["x_axis"] == ["Jan", "Feb", "Mar"]
        assert result.data["chart_type"] == "bar"

    @patch("src.providers.vlm_azure._call_vlm")
    def test_grounding_set_from_image(self, mock_vlm, tmp_path: Path):
        """Grounding bbox should be set from image dimensions."""
        from PIL import Image
        # Create a small test image
        img_path = tmp_path / "chart.png"
        Image.new("RGB", (400, 300), "white").save(img_path)

        mock_vlm.return_value = json.dumps({
            "series": [{"label": "A", "values": [1, 2]}],
            "x_axis": ["x", "y"],
            "y_axis": {"label": "val", "min": 0, "max": 2},
            "chart_type": "line",
        })

        result = read_chart(str(img_path))
        assert result.ok is True
        assert result.grounding is not None
        assert result.grounding.bbox == (0, 0, 400, 300)
        assert result.grounding.source_tool == "read_chart"

    @patch("src.providers.vlm_azure._call_vlm")
    def test_chart_type_hint_in_prompt(self, mock_vlm):
        """Chart type hint should be included in the VLM prompt."""
        mock_vlm.return_value = json.dumps({
            "series": [{"label": "A", "values": [1]}],
            "x_axis": ["x"],
            "y_axis": {"label": "y", "min": 0, "max": 1},
            "chart_type": "pie",
        })

        read_chart("test.png", chart_type="pie")
        call_args = mock_vlm.call_args
        prompt = call_args[0][1]
        assert "pie" in prompt

    @patch("src.providers.vlm_azure._call_vlm")
    def test_question_appended_to_prompt(self, mock_vlm):
        """Optional question should be appended to the prompt."""
        mock_vlm.return_value = json.dumps({
            "series": [{"label": "A", "values": [1]}],
            "x_axis": ["x"],
            "y_axis": {"label": "y", "min": 0, "max": 1},
            "chart_type": "bar",
        })

        read_chart("test.png", question="What is the peak value?")
        call_args = mock_vlm.call_args
        prompt = call_args[0][1]
        assert "What is the peak value?" in prompt


class TestReadChartFailures:
    """Verify read_chart handles VLM failures gracefully."""

    @patch("src.providers.vlm_azure._call_vlm")
    def test_vlm_returns_none(self, mock_vlm):
        """VLM call failure (rate limit/timeout) returns error ToolResult."""
        mock_vlm.return_value = None
        result = read_chart("test.png")
        assert result.ok is False
        assert "rate limit" in result.error.lower() or "timeout" in result.error.lower()
        assert result.tool == "read_chart"

    @patch("src.providers.vlm_azure._call_vlm")
    def test_vlm_returns_non_json(self, mock_vlm):
        """Non-JSON VLM response returns error."""
        mock_vlm.return_value = "This is a bar chart showing consumption data."
        result = read_chart("test.png")
        assert result.ok is False
        assert "json" in result.error.lower()

    @patch("src.providers.vlm_azure._call_vlm")
    def test_vlm_returns_json_without_series(self, mock_vlm):
        """JSON missing 'series' key returns error."""
        mock_vlm.return_value = json.dumps({"x_axis": ["a", "b"]})
        result = read_chart("test.png")
        assert result.ok is False
        assert "series" in result.error.lower()

    @patch("src.providers.vlm_azure._call_vlm")
    def test_vlm_returns_malformed_json(self, mock_vlm):
        """Malformed JSON returns error."""
        mock_vlm.return_value = '{"series": [{"label": "A", "values": [1,}'
        result = read_chart("test.png")
        assert result.ok is False
        assert "parse" in result.error.lower() or "json" in result.error.lower()

    @patch("src.providers.vlm_azure._call_vlm")
    def test_runtime_error_handled(self, mock_vlm):
        """RuntimeError (missing openai package) is caught."""
        mock_vlm.side_effect = RuntimeError("openai package not installed")
        result = read_chart("test.png")
        assert result.ok is False
        assert "openai" in result.error.lower()


class TestReadChartRegistry:
    """Verify read_chart is registered in the tool registry."""

    def test_read_chart_registered(self):
        """read_chart should be in the registry when vlm_provider=azure."""
        from src.run import build_tool_registry
        registry = build_tool_registry()
        names = registry.names()
        assert "read_chart" in names

    def test_read_chart_spec_has_chart_type(self):
        """ToolSpec should include chart_type in arg_schema."""
        from src.run import build_tool_registry
        registry = build_tool_registry()
        specs = {s.name: s for s in registry.specs()}
        assert "read_chart" in specs
        assert "chart_type" in specs["read_chart"].arg_schema

    def test_read_chart_spec_description_mentions_vlm(self):
        """ToolSpec description should mention VLM and bypassing OCR."""
        from src.run import build_tool_registry
        registry = build_tool_registry()
        specs = {s.name: s for s in registry.specs()}
        desc = specs["read_chart"].description.lower()
        assert "vlm" in desc
        assert "ocr" in desc


class TestReadChartMultipleSeries:
    """Verify multi-series chart extraction."""

    @patch("src.providers.vlm_azure._call_vlm")
    @patch("src.providers.vlm_azure.Grounding")
    def test_multiple_series(self, mock_grounding, mock_vlm):
        """read_chart handles multiple data series."""
        mock_vlm.return_value = json.dumps({
            "series": [
                {"label": "2024", "values": [100, 200, 150]},
                {"label": "2025", "values": [120, 210, 180]},
            ],
            "x_axis": ["Jan", "Feb", "Mar"],
            "y_axis": {"label": "kWh", "min": 0, "max": 250},
            "chart_type": "stacked_area",
        })
        mock_grounding.return_value = MagicMock()

        result = read_chart("test.png")
        assert result.ok is True
        assert len(result.data["series"]) == 2
        assert result.data["series"][0]["label"] == "2024"
        assert result.data["series"][1]["label"] == "2025"
        assert result.data["chart_type"] == "stacked_area"
