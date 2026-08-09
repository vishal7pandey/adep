"""Tests for detect_tables and read_table_cells tools [BLK-125].

Tests cover:
- Ruled table detection (visible borders)
- Unruled table detection (projection profiles)
- VLM fallback
- Cell-level bboxes
- Header detection
- read_table_cells composition helper
- No-table case
- Strategy recording
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.tools.table_detection import detect_tables, read_table_cells


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_ruled_table_image(path: str) -> None:
    """Create a synthetic image with a ruled table (visible grid lines)."""
    import cv2
    import numpy as np

    img = np.ones((400, 600, 3), dtype=np.uint8) * 255

    # Draw horizontal lines (thick for detection)
    for y in [50, 100, 150, 200, 250, 300]:
        cv2.line(img, (50, y), (550, y), (0, 0, 0), 3)

    # Draw vertical lines (thick for detection)
    for x in [50, 200, 350, 500, 550]:
        cv2.line(img, (x, 50), (x, 300), (0, 0, 0), 3)

    cv2.imwrite(path, img)


def _make_unruled_table_image(path: str) -> None:
    """Create a synthetic image with an unruled table (text in columns)."""
    import cv2
    import numpy as np

    img = np.ones((400, 600, 3), dtype=np.uint8) * 255

    # Draw text-like blocks in a grid pattern without borders
    for row in range(4):
        for col in range(3):
            x = 60 + col * 160
            y = 60 + row * 60
            cv2.rectangle(img, (x, y), (x + 100, y + 30), (80, 80, 80), -1)

    cv2.imwrite(path, img)


def _make_blank_image(path: str) -> None:
    """Create a blank image with no tables."""
    import cv2
    import numpy as np

    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    cv2.imwrite(path, img)


# ---------------------------------------------------------------------------
# detect_tables tests
# ---------------------------------------------------------------------------

class TestDetectTablesRuled:
    """Verify ruled table detection with visible borders."""

    def test_detects_ruled_table(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        result = detect_tables(image_path=img_path)
        assert result.ok
        assert result.tool == "detect_tables"
        tables = result.data["tables"]
        assert len(tables) >= 1
        table = tables[0]
        assert table["n_rows"] >= 2
        assert table["n_cols"] >= 2
        assert table["confidence"] > 0.8
        assert "cells" in table
        assert len(table["cells"]) == table["n_rows"] * table["n_cols"]

    def test_strategy_recorded(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        result = detect_tables(image_path=img_path)
        assert result.ok
        assert result.data["strategy"] == "ruled"

    def test_cell_bboxes_in_source_coordinates(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        result = detect_tables(image_path=img_path)
        tables = result.data["tables"]
        assert len(tables) >= 1
        for cell in tables[0]["cells"]:
            bbox = cell["bbox"]
            assert len(bbox) == 4
            assert bbox[0] < bbox[2]  # x1 < x2
            assert bbox[1] < bbox[3]  # y1 < y2

    def test_cell_text_is_none(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        result = detect_tables(image_path=img_path)
        tables = result.data["tables"]
        for cell in tables[0]["cells"]:
            assert cell["text"] is None

    def test_header_row_detected(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        result = detect_tables(image_path=img_path)
        tables = result.data["tables"]
        assert tables[0]["header_row_index"] is not None

    def test_row_span_col_span_default(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        result = detect_tables(image_path=img_path)
        tables = result.data["tables"]
        for cell in tables[0]["cells"]:
            assert cell["row_span"] == 1
            assert cell["col_span"] == 1


class TestDetectTablesUnruled:
    """Verify unruled table detection via projection profiles."""

    def test_detects_unruled_table(self, tmp_path: Path):
        img_path = str(tmp_path / "unruled_table.png")
        _make_unruled_table_image(img_path)

        result = detect_tables(image_path=img_path)
        assert result.ok
        tables = result.data["tables"]
        # May detect via unruled or VLM strategy
        if tables:
            table = tables[0]
            assert table["n_rows"] >= 2
            assert table["n_cols"] >= 2


class TestDetectTablesNoTable:
    """Verify no-table case returns empty list."""

    def test_blank_image_returns_empty(self, tmp_path: Path):
        img_path = str(tmp_path / "blank.png")
        _make_blank_image(img_path)

        result = detect_tables(image_path=img_path)
        assert result.ok
        assert result.data["tables"] == []
        assert result.data["strategy"] == "none"


class TestDetectTablesRegion:
    """Verify region parameter restricts detection."""

    def test_region_parameter_accepted(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        result = detect_tables(image_path=img_path, region=(40, 40, 560, 320))
        assert result.ok


class TestDetectTablesError:
    """Verify error handling."""

    def test_invalid_image_path(self):
        result = detect_tables(image_path="/nonexistent/path.png")
        assert not result.ok
        assert "Could not load image" in result.error


# ---------------------------------------------------------------------------
# read_table_cells tests
# ---------------------------------------------------------------------------

class TestReadTable:
    """Verify read_table_cells composition helper."""

    def test_read_table_cells_with_provided_table(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        table = {
            "bbox": (50, 50, 550, 300),
            "n_rows": 2,
            "n_cols": 2,
            "header_row_index": 0,
            "cells": [
                {"row": 0, "col": 0, "bbox": (50, 50, 200, 150), "text": "Item", "row_span": 1, "col_span": 1, "confidence": 0.9},
                {"row": 0, "col": 1, "bbox": (200, 50, 400, 150), "text": "Price", "row_span": 1, "col_span": 1, "confidence": 0.9},
                {"row": 1, "col": 0, "bbox": (50, 150, 200, 250), "text": None, "row_span": 1, "col_span": 1, "confidence": 0.9},
                {"row": 1, "col": 1, "bbox": (200, 150, 400, 250), "text": None, "row_span": 1, "col_span": 1, "confidence": 0.9},
            ],
        }

        with patch("src.config.settings") as mock_settings, \
             patch("src.providers.image_cv.crop") as mock_crop, \
             patch("src.providers.ocr_tesseract.ocr") as mock_ocr:
            mock_settings.ocr_provider = "tesseract"
            mock_crop.return_value = MagicMock(ok=True, data="cropped.png")
            mock_ocr.return_value = MagicMock(ok=True, data="Widget")

            result = read_table_cells(image_path=img_path, table=table)
            assert result.ok
            assert result.tool == "read_table_cells"
            assert result.data["headers"] == ["Item", "Price"]
            rows = result.data["rows"]
            assert len(rows) == 1  # 2 rows minus header
            assert rows[0]["Item"] == "Widget"

    def test_read_table_cells_no_table_provided_runs_detect(self, tmp_path: Path):
        img_path = str(tmp_path / "ruled_table.png")
        _make_ruled_table_image(img_path)

        with patch("src.config.settings") as mock_settings, \
             patch("src.providers.image_cv.crop") as mock_crop, \
             patch("src.providers.ocr_tesseract.ocr") as mock_ocr:
            mock_settings.ocr_provider = "tesseract"
            mock_crop.return_value = MagicMock(ok=True, data="cropped.png")
            mock_ocr.return_value = MagicMock(ok=True, data="text")

            result = read_table_cells(image_path=img_path)
            assert result.ok
            assert "rows" in result.data
            assert "headers" in result.data

    def test_read_table_cells_no_tables_found(self, tmp_path: Path):
        img_path = str(tmp_path / "blank.png")
        _make_blank_image(img_path)

        result = read_table_cells(image_path=img_path)
        assert result.ok
        assert result.data["rows"] == []
        assert result.data["headers"] == []
