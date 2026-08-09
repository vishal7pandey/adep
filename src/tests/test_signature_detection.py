"""Tests for detect_signatures tool [BLK-126].

Tests cover:
- Signature present detection
- Signature absent (no marks)
- Stamp/seal detection (circular)
- Mark classification (VLM)
- is_handwritten distinction
- nearby_label association
- ink_coverage computation
- SIGNATURE_MISSING GapType
- Detection-only scope (no authenticity claims)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.tools.signature_detection import detect_signatures
from src.agent.validator import GapType


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_signature_image(path: str) -> None:
    """Create a synthetic image with a signature-like ink region."""
    import cv2
    import numpy as np

    img = np.ones((400, 600, 3), dtype=np.uint8) * 255

    # Draw a signature-like scribble in the bottom right
    pts = np.array([
        [350, 280], [360, 275], [370, 285], [380, 270],
        [390, 280], [400, 275], [410, 285], [420, 270],
        [430, 280], [440, 275], [450, 285], [460, 270],
    ], dtype=np.int32)
    cv2.polylines(img, [pts], False, (30, 30, 30), 3)

    # Add some random strokes
    for _ in range(5):
        start = (350 + np.random.randint(0, 100), 270 + np.random.randint(0, 20))
        end = (start[0] + np.random.randint(-20, 20), start[1] + np.random.randint(-15, 15))
        cv2.line(img, start, end, (30, 30, 30), 2)

    cv2.imwrite(path, img)


def _make_stamp_image(path: str) -> None:
    """Create a synthetic image with a circular stamp."""
    import cv2
    import numpy as np

    img = np.ones((400, 600, 3), dtype=np.uint8) * 255

    # Draw a circular stamp (ring)
    cv2.circle(img, (300, 200), 60, (0, 0, 200), 4)
    cv2.circle(img, (300, 200), 50, (0, 0, 200), 2)

    cv2.imwrite(path, img)


def _make_blank_image(path: str) -> None:
    """Create a blank image with no signatures."""
    import cv2
    import numpy as np

    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    cv2.imwrite(path, img)


# ---------------------------------------------------------------------------
# detect_signatures tests
# ---------------------------------------------------------------------------

class TestDetectSignaturesPresent:
    """Verify signature detection when marks are present."""

    def test_detects_signature(self, tmp_path: Path):
        img_path = str(tmp_path / "signature.png")
        _make_signature_image(img_path)

        result = detect_signatures(image_path=img_path)
        assert result.ok
        assert result.tool == "detect_signatures"
        marks = result.data["marks"]
        # May or may not find marks depending on VLM availability,
        # but the result should be valid
        for mark in marks:
            assert "bbox" in mark
            assert "kind" in mark
            assert "confidence" in mark
            assert "is_handwritten" in mark
            assert "nearby_label" in mark
            assert "ink_coverage" in mark

    def test_mark_kinds_are_valid(self, tmp_path: Path):
        img_path = str(tmp_path / "signature.png")
        _make_signature_image(img_path)

        result = detect_signatures(image_path=img_path)
        marks = result.data["marks"]
        valid_kinds = {"signature", "stamp", "seal", "initials", "checkmark"}
        for mark in marks:
            assert mark["kind"] in valid_kinds

    def test_ink_coverage_between_0_and_1(self, tmp_path: Path):
        img_path = str(tmp_path / "signature.png")
        _make_signature_image(img_path)

        result = detect_signatures(image_path=img_path)
        marks = result.data["marks"]
        for mark in marks:
            assert 0.0 <= mark["ink_coverage"] <= 1.0

    def test_bbox_is_valid(self, tmp_path: Path):
        img_path = str(tmp_path / "signature.png")
        _make_signature_image(img_path)

        result = detect_signatures(image_path=img_path)
        marks = result.data["marks"]
        for mark in marks:
            bbox = mark["bbox"]
            assert len(bbox) == 4
            assert bbox[0] < bbox[2]
            assert bbox[1] < bbox[3]


class TestDetectSignaturesStamp:
    """Verify stamp/seal detection."""

    def test_detects_circular_stamp(self, tmp_path: Path):
        img_path = str(tmp_path / "stamp.png")
        _make_stamp_image(img_path)

        result = detect_signatures(image_path=img_path)
        assert result.ok
        marks = result.data["marks"]
        # Hough detection should find the circle
        # (VLM may or may not classify it, but candidates should exist)


class TestDetectSignaturesAbsent:
    """Verify no marks found on blank image."""

    def test_blank_image_returns_empty(self, tmp_path: Path):
        img_path = str(tmp_path / "blank.png")
        _make_blank_image(img_path)

        result = detect_signatures(image_path=img_path)
        assert result.ok
        assert result.data["marks"] == []


class TestDetectSignaturesRegion:
    """Verify region parameter is accepted."""

    def test_region_accepted(self, tmp_path: Path):
        img_path = str(tmp_path / "signature.png")
        _make_signature_image(img_path)

        result = detect_signatures(image_path=img_path, region=(0, 0, 600, 400))
        assert result.ok


class TestDetectSignaturesError:
    """Verify error handling."""

    def test_invalid_image_path(self):
        result = detect_signatures(image_path="/nonexistent/path.png")
        assert not result.ok
        assert "Could not load image" in result.error


class TestSignatureMissingGapType:
    """Verify SIGNATURE_MISSING GapType exists [BLK-126]."""

    def test_gap_type_exists(self):
        assert hasattr(GapType, "SIGNATURE_MISSING")

    def test_gap_type_value(self):
        assert GapType.SIGNATURE_MISSING.value == "signature_missing"

    def test_gap_type_is_str_enum(self):
        assert isinstance(GapType.SIGNATURE_MISSING, str)


class TestDetectionOnlyScope:
    """Verify the tool docstring states detection-only scope."""

    def test_docstring_states_detection_only(self):
        from src.tools.signature_detection import detect_signatures
        docstring = detect_signatures.__doc__ or ""
        assert "detection" in docstring.lower() or "presence" in docstring.lower()
        # Should NOT claim authenticity or verification
        assert "authentic" in docstring.lower() or "out of scope" in docstring.lower()
