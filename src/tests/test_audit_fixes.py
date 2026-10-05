"""Tests for audit fixes (BLK-151, BLK-140, BLK-150, BLK-144, BLK-145).

Tests cover:
- BLK-151: Path traversal rejection in DefinitionStore and DocumentStore
- BLK-140: Timezone-independent _seconds_since calculation
- BLK-150: WebhookStore.get_raw() returns unmasked secret
- BLK-144: read_tag uses settings.ocr_provider (not hardcoded)
- BLK-145: Serialization edge IDs use enumerate (not O(n²) index)
"""

from __future__ import annotations

import json
import os
import time
import calendar
from pathlib import Path
from unittest.mock import patch

import pytest

from src.definitions.store import DefinitionStore
from src.documents.store import DocumentStore
from src.api.auth import _seconds_since
from src.agent.webhooks import WebhookStore, WebhookConfig


# ---------------------------------------------------------------------------
# BLK-151: Path traversal tests
# ---------------------------------------------------------------------------


class TestPathTraversalDefinitionStore:
    """Verify DefinitionStore rejects path traversal in entity IDs."""

    def test_rejects_dotdot(self, tmp_path: Path):
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.create("skills", "../../etc/passwd", {"name": "evil"})

    def test_rejects_slash(self, tmp_path: Path):
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.create("skills", "foo/bar", {"name": "evil"})

    def test_rejects_backslash(self, tmp_path: Path):
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.create("skills", "foo\\bar", {"name": "evil"})

    def test_rejects_dot_prefix(self, tmp_path: Path):
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.create("skills", ".hidden", {"name": "evil"})

    def test_accepts_valid_id(self, tmp_path: Path):
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        result = store.create("skills", "my-skill_1", {"name": "ok"})
        assert result["name"] == "ok"

    def test_rejects_traversal_on_read(self, tmp_path: Path):
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.read("skills", "../../etc/passwd")

    def test_rejects_traversal_on_delete(self, tmp_path: Path):
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid entity ID"):
            store.delete("skills", "../../etc/passwd")


class TestPathTraversalDocumentStore:
    """Verify DocumentStore rejects path traversal in doc IDs."""

    def test_rejects_dotdot(self, tmp_path: Path):
        store = DocumentStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid document ID"):
            store.get_doc_dir("../../etc/passwd")

    def test_rejects_slash(self, tmp_path: Path):
        store = DocumentStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid document ID"):
            store.get_doc_dir("foo/bar")

    def test_rejects_dot_prefix(self, tmp_path: Path):
        store = DocumentStore(base_dir=tmp_path / ".adep")
        with pytest.raises(ValueError, match="Invalid document ID"):
            store.get_doc_dir(".hidden")

    def test_accepts_valid_id(self, tmp_path: Path):
        store = DocumentStore(base_dir=tmp_path / ".adep")
        doc_dir = store.get_doc_dir("abc123_def")
        assert doc_dir.name == "abc123_def"


# ---------------------------------------------------------------------------
# BLK-140: Timezone bug tests
# ---------------------------------------------------------------------------


class TestTimezoneFix:
    """Verify _seconds_since uses UTC, not localtime."""

    def test_returns_finite_for_recent_timestamp(self):
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result = _seconds_since(now)
        assert 0 <= result < 10

    def test_returns_large_for_old_timestamp(self):
        result = _seconds_since("2020-01-01T00:00:00Z")
        assert result > 1000000

    def test_returns_inf_for_invalid(self):
        result = _seconds_since("not-a-timestamp")
        assert result == float("inf")

    def test_timezone_independent(self):
        """Verify the calculation is the same regardless of TZ.

        The bug was that time.mktime() interprets the struct_time as
        localtime. If we run with TZ=Asia/Kolkata (UTC+5:30), the old
        code would subtract 5.5 hours from the result, making
        _seconds_since return ~19800s more than it should.

        With calendar.timegm(), the struct_time is always interpreted
        as UTC, so the result is timezone-independent.
        """
        ts = "2026-01-01T00:00:00Z"
        result = _seconds_since(ts)
        # The exact value depends on current time, but it should be
        # the difference between now and 2026-01-01T00:00:00 UTC.
        # We verify it's reasonable (not off by hours).
        expected_approx = time.time() - time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
        # The difference between the correct (UTC) and buggy (localtime)
        # would be the timezone offset. If the fix is correct, the result
        # should NOT differ from the UTC calculation by more than a few
        # seconds (allowing for execution time).
        utc_calc = time.time() - calendar.timegm(time.strptime(ts, "%Y-%m-%dT%H:%M:%SZ"))
        assert abs(result - utc_calc) < 5


# ---------------------------------------------------------------------------
# BLK-150: WebhookStore.get_raw() tests
# ---------------------------------------------------------------------------


class TestWebhookGetRaw:
    """Verify WebhookStore.get_raw() returns unmasked secret."""

    @pytest.fixture(autouse=True)
    def _mock_url_validation(self):
        """Mock SSRF validation for webhook store tests (uses http:// URLs)."""
        with patch("src.agent.webhooks._validate_webhook_url"):
            yield

    def test_get_masks_secret(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        config = WebhookConfig(id="wh1", url="http://example.com", secret="supersecret")
        store.create("wh1", config)
        data = store.get("wh1")
        assert data["secret"] == "***"

    def test_get_raw_returns_unmasked_secret(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        config = WebhookConfig(id="wh1", url="http://example.com", secret="supersecret")
        store.create("wh1", config)
        raw = store.get_raw("wh1")
        assert raw["secret"] == "supersecret"

    def test_get_raw_raises_for_missing(self, tmp_path: Path):
        store = WebhookStore(base_dir=tmp_path / ".adep")
        with pytest.raises(FileNotFoundError):
            store.get_raw("nonexistent")


# ---------------------------------------------------------------------------
# BLK-144: read_tag OCR provider selection tests
# ---------------------------------------------------------------------------


class TestReadTagOcrProvider:
    """Verify read_tag uses settings.ocr_provider instead of hardcoding."""

    def test_uses_tesseract_when_configured(self):
        with (
            patch("src.providers.image_cv.crop") as mock_crop,
            patch("src.providers.ocr_tesseract.ocr") as mock_ocr,
            patch("src.config.settings") as mock_settings,
        ):
            mock_settings.ocr_provider = "tesseract"
            mock_crop.return_value = type(
                "R",
                (),
                {
                    "ok": True,
                    "data": "cropped.png",
                    "error": "",
                    "tool": "crop",
                },
            )()
            mock_ocr.return_value = type(
                "R",
                (),
                {
                    "ok": True,
                    "data": "FT-101",
                    "error": "",
                    "tool": "ocr",
                    "grounding": type("G", (), {"confidence": 0.9, "bbox": (0, 0, 0, 0)})(),
                },
            )()
            from src.tools.graph.tag_reading import read_tag

            result = read_tag(image_path="test.png", bbox=(10, 10, 50, 30))
            assert result.ok
            assert result.data["tag"] == "FT-101"

    def test_uses_paddle_when_configured(self):
        with (
            patch("src.providers.image_cv.crop") as mock_crop,
            patch("src.providers.ocr_paddle.ocr") as mock_ocr,
            patch("src.config.settings") as mock_settings,
        ):
            mock_settings.ocr_provider = "paddle"
            mock_crop.return_value = type(
                "R",
                (),
                {
                    "ok": True,
                    "data": "cropped.png",
                    "error": "",
                    "tool": "crop",
                },
            )()
            mock_ocr.return_value = type(
                "R",
                (),
                {
                    "ok": True,
                    "data": "FT-101",
                    "error": "",
                    "tool": "ocr",
                    "grounding": type("G", (), {"confidence": 0.9, "bbox": (0, 0, 0, 0)})(),
                },
            )()
            from src.tools.graph.tag_reading import read_tag

            result = read_tag(image_path="test.png", bbox=(10, 10, 50, 30))
            assert result.ok
            assert result.data["tag"] == "FT-101"


# ---------------------------------------------------------------------------
# BLK-145: Serialization edge ID tests
# ---------------------------------------------------------------------------


class TestSerializationEdgeIds:
    """Verify edge IDs use enumerate, not O(n²) index."""

    def test_graphml_edge_ids_without_explicit_ids(self):
        from src.tools.graph.serialization import serialize_graph

        graph = {
            "nodes": [
                {"id": "n1", "type": "valve"},
                {"id": "n2", "type": "pump"},
                {"id": "n3", "type": "tank"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "pipe"},
                {"source": "n2", "target": "n3", "type": "pipe"},
                {"source": "n1", "target": "n3", "type": "signal"},
            ],
        }
        result = serialize_graph(graph=graph, format="graphml")
        assert result.ok
        content = result.data["content"]
        assert 'id="e0"' in content
        assert 'id="e1"' in content
        assert 'id="e2"' in content

    def test_dexpi_edge_ids_without_explicit_ids(self):
        from src.tools.graph.serialization import serialize_graph

        graph = {
            "nodes": [
                {"id": "n1", "type": "valve"},
                {"id": "n2", "type": "pump"},
            ],
            "edges": [
                {"source": "n1", "target": "n2", "type": "pipe"},
                {"source": "n2", "target": "n1", "type": "pipe"},
            ],
        }
        result = serialize_graph(graph=graph, format="dexpi_xml")
        assert result.ok
        content = result.data["content"]
        assert 'ID="p0"' in content
        assert 'ID="p1"' in content

    def test_graphml_preserves_explicit_edge_ids(self):
        from src.tools.graph.serialization import serialize_graph

        graph = {
            "nodes": [{"id": "n1", "type": "valve"}, {"id": "n2", "type": "pump"}],
            "edges": [{"id": "custom_edge", "source": "n1", "target": "n2"}],
        }
        result = serialize_graph(graph=graph, format="graphml")
        content = result.data["content"]
        assert 'id="custom_edge"' in content
