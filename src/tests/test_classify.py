"""Tests for BLK-127 — classify_document tool + auto-routing.

Tests cover:
- classify_document tool with mocked VLM
- Classification predictions with confidence and reasoning
- suggested_definition_id resolution
- Multi-page document classification and is_multi_type detection
- auto_route success above threshold
- auto_route failure below threshold (fail fast, no silent guessing)
- POST /documents/{id}/suggest-agent endpoint
- definition_id='auto' on run start
- DOCUMENT_TYPE_UNKNOWN GapType
- Prompt lives in src/prompts/ (not inline)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.tools.base import ToolResult
from src.tools.classify import (
    classify_document,
    auto_route,
    _get_candidate_types,
    _parse_vlm_response,
    _resolve_definition_id,
    _enrich_predictions,
    DEFAULT_AUTO_ROUTE_THRESHOLD,
)
from src.agent.validator import GapType


# ---------------------------------------------------------------------------
# Helper: create a mock VLM response
# ---------------------------------------------------------------------------

def _mock_vlm_response(predictions: list[dict]) -> str:
    """Create a mock VLM JSON response string."""
    return json.dumps(predictions)


# ---------------------------------------------------------------------------
# GapType tests
# ---------------------------------------------------------------------------

class TestDocumentTypeUnknownGap:
    """Verify DOCUMENT_TYPE_UNKNOWN GapType exists [BLK-127]."""

    def test_gap_type_exists(self):
        assert hasattr(GapType, "DOCUMENT_TYPE_UNKNOWN")

    def test_gap_type_value(self):
        assert GapType.DOCUMENT_TYPE_UNKNOWN.value == "document_type_unknown"


# ---------------------------------------------------------------------------
# Candidate type resolution tests
# ---------------------------------------------------------------------------

class TestCandidateTypes:
    """Verify candidate type resolution from prebuilt definitions [BLK-127]."""

    def test_get_all_candidates(self):
        candidates = _get_candidate_types()
        assert len(candidates) > 0
        # Each candidate should have type, description, and definition_id
        for c in candidates:
            assert "type" in c
            assert "description" in c
            assert "definition_id" in c

    def test_get_filtered_candidates(self):
        all_candidates = _get_candidate_types()
        first_def_id = all_candidates[0]["definition_id"]
        filtered = _get_candidate_types([first_def_id])
        assert len(filtered) == 1
        assert filtered[0]["definition_id"] == first_def_id

    def test_get_candidates_empty_filter(self):
        filtered = _get_candidate_types(["nonexistent-def"])
        assert len(filtered) == 0


# ---------------------------------------------------------------------------
# VLM response parsing tests
# ---------------------------------------------------------------------------

class TestVLMResponseParsing:
    """Verify VLM JSON response parsing [BLK-127]."""

    def test_parse_simple_json(self):
        response = '[{"document_type": "invoice", "confidence": 0.9, "reasoning": "test"}]'
        result = _parse_vlm_response(response)
        assert len(result) == 1
        assert result[0]["document_type"] == "invoice"

    def test_parse_markdown_fenced_json(self):
        response = '```json\n[{"document_type": "invoice", "confidence": 0.9, "reasoning": "test"}]\n```'
        result = _parse_vlm_response(response)
        assert len(result) == 1
        assert result[0]["document_type"] == "invoice"

    def test_parse_invalid_json(self):
        result = _parse_vlm_response("not json at all")
        assert result == []

    def test_parse_dict_response(self):
        response = '{"document_type": "invoice", "confidence": 0.9, "reasoning": "test"}'
        result = _parse_vlm_response(response)
        assert len(result) == 1
        assert result[0]["document_type"] == "invoice"


# ---------------------------------------------------------------------------
# Definition ID resolution tests
# ---------------------------------------------------------------------------

class TestDefinitionResolution:
    """Verify suggested_definition_id resolution [BLK-127]."""

    def test_resolve_known_type(self):
        candidates = _get_candidate_types()
        first = candidates[0]
        def_id = _resolve_definition_id(first["type"], candidates)
        assert def_id == first["definition_id"]

    def test_resolve_unknown_type(self):
        candidates = _get_candidate_types()
        def_id = _resolve_definition_id("nonexistent_type", candidates)
        assert def_id is None

    def test_enrich_predictions(self):
        candidates = _get_candidate_types()
        first_type = candidates[0]["type"]
        first_def = candidates[0]["definition_id"]
        predictions = [{"document_type": first_type, "confidence": 0.9, "reasoning": "test"}]
        enriched = _enrich_predictions(predictions, candidates)
        assert enriched[0]["suggested_definition_id"] == first_def


# ---------------------------------------------------------------------------
# classify_document tool tests
# ---------------------------------------------------------------------------

class TestClassifyDocument:
    """Verify classify_document tool [BLK-127]."""

    def test_single_page_classification(self, tmp_path: Path):
        mock_response = _mock_vlm_response([
            {"document_type": "invoice", "confidence": 0.92, "reasoning": "Has vendor info and line items."},
            {"document_type": "purchase_order", "confidence": 0.45, "reasoning": "Has table but no PO fields."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = classify_document(image_path="test.png")

        assert result.ok
        assert result.tool == "classify_document"
        assert len(result.data["predictions"]) == 2
        assert result.data["predictions"][0]["confidence"] == 0.92
        assert result.data["page_count"] == 1
        assert result.data["is_multi_type"] is False

    def test_classification_with_definition_id(self, tmp_path: Path):
        candidates = _get_candidate_types()
        first_type = candidates[0]["type"]
        first_def = candidates[0]["definition_id"]
        mock_response = _mock_vlm_response([
            {"document_type": first_type, "confidence": 0.95, "reasoning": "Clear match."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = classify_document(image_path="test.png")

        assert result.ok
        assert result.data["predictions"][0]["suggested_definition_id"] == first_def

    def test_multi_page_classification(self, tmp_path: Path):
        # Mock different responses for different pages
        responses = [
            _mock_vlm_response([{"document_type": "invoice", "confidence": 0.9, "reasoning": "Page 1 is invoice."}]),
            _mock_vlm_response([{"document_type": "bank_statement", "confidence": 0.85, "reasoning": "Page 2 is bank statement."}]),
        ]
        with patch("src.providers.vlm_azure._call_vlm", side_effect=responses):
            result = classify_document(
                image_path="page1.png",
                page_paths=["page1.png", "page2.png"],
            )

        assert result.ok
        assert result.data["page_count"] == 2
        assert result.data["is_multi_type"] is True

    def test_multi_page_same_type(self, tmp_path: Path):
        responses = [
            _mock_vlm_response([{"document_type": "invoice", "confidence": 0.9, "reasoning": "Page 1 is invoice."}]),
            _mock_vlm_response([{"document_type": "invoice", "confidence": 0.88, "reasoning": "Page 2 is also invoice."}]),
        ]
        with patch("src.providers.vlm_azure._call_vlm", side_effect=responses):
            result = classify_document(
                image_path="page1.png",
                page_paths=["page1.png", "page2.png"],
            )

        assert result.ok
        assert result.data["is_multi_type"] is False

    def test_unknown_document_type(self, tmp_path: Path):
        mock_response = _mock_vlm_response([
            {"document_type": "unknown", "confidence": 0.2, "reasoning": "Does not match any known type."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = classify_document(image_path="test.png")

        assert result.ok
        assert result.data["predictions"][0]["document_type"] == "unknown"
        assert result.data["predictions"][0]["suggested_definition_id"] is None

    def test_vlm_returns_none(self, tmp_path: Path):
        with patch("src.providers.vlm_azure._call_vlm", return_value=None):
            result = classify_document(image_path="test.png")

        assert not result.ok
        assert "no response" in result.error.lower()

    def test_vlm_raises_exception(self, tmp_path: Path):
        with patch("src.providers.vlm_azure._call_vlm", side_effect=RuntimeError("API error")):
            result = classify_document(image_path="test.png")

        assert not result.ok
        assert "VLM classification failed" in result.error

    def test_predictions_sorted_by_confidence(self, tmp_path: Path):
        mock_response = _mock_vlm_response([
            {"document_type": "invoice", "confidence": 0.5, "reasoning": "low"},
            {"document_type": "medical_claim", "confidence": 0.9, "reasoning": "high"},
            {"document_type": "utility_bill", "confidence": 0.7, "reasoning": "medium"},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = classify_document(image_path="test.png")

        assert result.ok
        confidences = [p["confidence"] for p in result.data["predictions"]]
        assert confidences == sorted(confidences, reverse=True)

    def test_filtered_candidates(self, tmp_path: Path):
        candidates = _get_candidate_types()
        first_def = candidates[0]["definition_id"]
        first_type = candidates[0]["type"]
        mock_response = _mock_vlm_response([
            {"document_type": first_type, "confidence": 0.9, "reasoning": "match"},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = classify_document(image_path="test.png", candidates=[first_def])

        assert result.ok
        assert result.data["predictions"][0]["document_type"] == first_type
        assert result.data["predictions"][0]["suggested_definition_id"] == first_def


# ---------------------------------------------------------------------------
# auto_route tests
# ---------------------------------------------------------------------------

class TestAutoRoute:
    """Verify auto_route function [BLK-127]."""

    def test_auto_route_success(self, tmp_path: Path):
        candidates = _get_candidate_types()
        first_type = candidates[0]["type"]
        first_def = candidates[0]["definition_id"]
        mock_response = _mock_vlm_response([
            {"document_type": first_type, "confidence": 0.92, "reasoning": "Clear match."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = auto_route(image_path="test.png")

        assert result["routed"] is True
        assert result["definition_id"] == first_def
        assert "confidence" in str(result["reason"]).lower() or "0.92" in result["reason"]

    def test_auto_route_below_threshold_fails_fast(self, tmp_path: Path):
        mock_response = _mock_vlm_response([
            {"document_type": "invoice", "confidence": 0.3, "reasoning": "Low confidence match."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            with pytest.raises(ValueError, match="threshold"):
                auto_route(image_path="test.png", threshold=0.75)

    def test_auto_route_custom_threshold(self, tmp_path: Path):
        candidates = _get_candidate_types()
        first_type = candidates[0]["type"]
        first_def = candidates[0]["definition_id"]
        mock_response = _mock_vlm_response([
            {"document_type": first_type, "confidence": 0.6, "reasoning": "Moderate match."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = auto_route(image_path="test.png", threshold=0.5)

        assert result["routed"] is True
        assert result["definition_id"] == first_def

    def test_auto_route_no_predictions(self, tmp_path: Path):
        with patch("src.providers.vlm_azure._call_vlm", return_value="[]"):
            with pytest.raises(ValueError, match="no predictions"):
                auto_route(image_path="test.png")

    def test_auto_route_uses_config_threshold(self, tmp_path: Path):
        candidates = _get_candidate_types()
        first_type = candidates[0]["type"]
        first_def = candidates[0]["definition_id"]
        mock_response = _mock_vlm_response([
            {"document_type": first_type, "confidence": 0.8, "reasoning": "Good match."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            result = auto_route(image_path="test.png")

        # Default threshold is 0.75, confidence is 0.8 — should route
        assert result["routed"] is True


# ---------------------------------------------------------------------------
# Prompt location test
# ---------------------------------------------------------------------------

class TestPromptLocation:
    """Verify prompt lives in src/prompts/, not inline [BLK-127]."""

    def test_prompt_module_exists(self):
        from src.prompts.classify import CLASSIFY_PROMPT_TEMPLATE
        assert "candidate" in CLASSIFY_PROMPT_TEMPLATE.lower()

    def test_multi_page_prompt_exists(self):
        from src.prompts.classify import MULTI_PAGE_PROMPT_TEMPLATE
        assert "multi" in MULTI_PAGE_PROMPT_TEMPLATE.lower()

    def test_build_candidate_list(self):
        from src.prompts.classify import build_candidate_list
        candidates = [
            {"type": "invoice", "description": "General invoice"},
            {"type": "receipt", "description": "Thermal receipt"},
        ]
        result = build_candidate_list(candidates)
        assert "invoice" in result
        assert "General invoice" in result
        assert "receipt" in result


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestSuggestAgentEndpoint:
    """Verify POST /documents/{id}/suggest-agent endpoint [BLK-127]."""

    @pytest.fixture
    def client(self, tmp_path: Path):
        import src.definitions.store as store_module
        import src.documents.store as doc_store_module
        import src.config as config_module

        old_def_store = store_module._store
        old_doc_store = doc_store_module._store
        old_auth = config_module.settings.auth_enabled

        store_module._store = store_module.DefinitionStore(base_dir=tmp_path / ".adep")
        doc_store_module._store = doc_store_module.DocumentStore(base_dir=tmp_path / ".adep")
        config_module.settings.auth_enabled = False

        from src.api.main import create_app
        app = create_app()
        yield TestClient(app)

        config_module.settings.auth_enabled = old_auth
        store_module._store = old_def_store
        doc_store_module._store = old_doc_store

    def test_suggest_agent_endpoint(self, client, tmp_path: Path):
        # Create a fake document
        doc_store = __import__("src.documents.store", fromlist=["get_document_store"]).get_document_store()
        pages_dir = doc_store.base_dir / "documents" / "test-doc" / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        page_path = pages_dir / "page_001.png"
        page_path.write_bytes(b"fake png")

        # Register document metadata
        import json
        meta_path = doc_store.base_dir / "documents" / "test-doc" / "meta.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps({
            "document_id": "test-doc",
            "original_filename": "test.png",
            "format": "png",
            "total_pages": 1,
            "page_dimensions": [{"width": 800, "height": 600}],
            "page_paths": [str(page_path)],
            "thumbnail_path": "",
            "created_at": "2026-01-01T00:00:00Z",
        }))

        mock_response = _mock_vlm_response([
            {"document_type": "invoice", "confidence": 0.9, "reasoning": "Has invoice fields."},
        ])
        with patch("src.providers.vlm_azure._call_vlm", return_value=mock_response):
            resp = client.post("/api/v1/documents/test-doc/suggest-agent")

        assert resp.status_code == 200
        data = resp.json()
        assert "predictions" in data
        assert len(data["predictions"]) > 0
        assert data["predictions"][0]["confidence"] == 0.9

    def test_suggest_agent_not_found(self, client):
        resp = client.post("/api/v1/documents/nonexistent/suggest-agent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tool registration test
# ---------------------------------------------------------------------------

class TestToolRegistration:
    """Verify classify_document is registered with a ToolSpec [BLK-127]."""

    def test_tool_registered(self):
        from src.run import build_tool_registry
        registry = build_tool_registry()
        names = registry.names()
        assert "classify_document" in names

    def test_tool_spec(self):
        from src.run import build_tool_registry
        registry = build_tool_registry()
        spec, func = registry.get("classify_document")
        assert spec.name == "classify_document"
        assert "image_path" in spec.arg_schema
        assert "candidates" in spec.arg_schema
