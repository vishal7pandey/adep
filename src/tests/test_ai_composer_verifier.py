"""Tests for BLK-067: AI Template Composer and BLK-070: Surrogate Verifier.

Covers:
- Template Composer: field normalization, type validation, threshold defaults
- Template Composer: empty description handling, LLM failure handling
- Template Composer: JSON parsing from LLM response
- Surrogate Verifier: trace formatting, gap report formatting, extraction formatting
- Surrogate Verifier: LLM failure handling, JSON parsing
- Endpoints: POST /templates/generate, POST /skills/{id}/verify
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.ai.template_composer import (
    generate_template,
    _normalize_field_name,
    _validate_field,
)
from src.ai.surrogate_verifier import (
    verify_skill,
    _format_trace,
    _format_gap_report,
    _format_extraction,
)
from src.agent.token_tracking import LLMResponse


# ---------------------------------------------------------------------------
# Template Composer unit tests
# ---------------------------------------------------------------------------


class TestNormalizeFieldName:
    """Field name normalization to snake_case [BLK-067]."""

    def test_already_snake_case(self):
        assert _normalize_field_name("invoice_number") == "invoice_number"

    def test_spaces_to_underscores(self):
        assert _normalize_field_name("Invoice Number") == "invoice_number"

    def test_mixed_case(self):
        assert _normalize_field_name("InvoiceNumber") == "invoicenumber"

    def test_special_chars_removed(self):
        assert _normalize_field_name("Total Amount ($)") == "total_amount"

    def test_empty_string(self):
        assert _normalize_field_name("") == ""


class TestValidateField:
    """Field validation and normalization [BLK-067]."""

    def test_valid_field(self):
        field = {"name": "invoice_number", "type": "string", "required": True, "threshold": 0.85}
        result = _validate_field(field)
        assert result["name"] == "invoice_number"
        assert result["type"] == "string"
        assert result["required"] is True
        assert result["confidence_threshold"] == 0.85

    def test_unsupported_type_defaults_to_string(self):
        field = {"name": "test", "type": "weird_type"}
        result = _validate_field(field)
        assert result["type"] == "string"

    def test_threshold_defaults_by_type(self):
        field = {"name": "amount", "type": "float"}
        result = _validate_field(field)
        assert result["confidence_threshold"] == 0.85

        field = {"name": "notes", "type": "string"}
        result = _validate_field(field)
        assert result["confidence_threshold"] == 0.8

        field = {"name": "is_paid", "type": "boolean"}
        result = _validate_field(field)
        assert result["confidence_threshold"] == 0.75

    def test_invalid_threshold_clamped(self):
        field = {"name": "test", "type": "string", "threshold": 1.5}
        result = _validate_field(field)
        assert result["confidence_threshold"] == 0.8

    def test_list_with_sub_fields(self):
        field = {
            "name": "line_items",
            "type": "list",
            "sub_fields": [
                {"name": "quantity", "type": "int"},
                {"name": "rate", "type": "float"},
            ],
        }
        result = _validate_field(field)
        assert result["type"] == "list"
        assert len(result["sub_fields"]) == 2
        assert result["sub_fields"][0]["name"] == "quantity"

    def test_non_list_ignores_sub_fields(self):
        field = {"name": "total", "type": "float", "sub_fields": [{"name": "x", "type": "int"}]}
        result = _validate_field(field)
        assert result["sub_fields"] == []


class TestGenerateTemplate:
    """Template generation from NL [BLK-067]."""

    def test_empty_description_returns_error(self):
        result = generate_template("")
        assert "error" in result
        assert result["fields"] == []

    def test_whitespace_description_returns_error(self):
        result = generate_template("   ")
        assert "error" in result

    @patch("src.ai.template_composer.invoke_llm")
    def test_successful_generation(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(
            content=json.dumps(
                {
                    "name": "Invoice Template",
                    "description": "Extract invoice fields",
                    "fields": [
                        {
                            "name": "vendor_name",
                            "type": "string",
                            "required": True,
                            "threshold": 0.8,
                        },
                        {
                            "name": "invoice_number",
                            "type": "string",
                            "required": True,
                            "threshold": 0.85,
                        },
                        {
                            "name": "total_amount",
                            "type": "float",
                            "required": True,
                            "threshold": 0.85,
                        },
                        {
                            "name": "invoice_date",
                            "type": "date",
                            "required": True,
                            "threshold": 0.85,
                        },
                        {
                            "name": "is_paid",
                            "type": "boolean",
                            "required": False,
                            "threshold": 0.75,
                        },
                    ],
                }
            ),
            input_tokens=100,
            output_tokens=200,
        )
        result = generate_template(
            "Extract vendor name, invoice number, total, date, and paid status"
        )
        assert result["name"] == "Invoice Template"
        assert len(result["fields"]) == 5
        assert result["fields"][0]["name"] == "vendor_name"
        assert result["fields"][2]["type"] == "float"
        assert "_token_usage" in result

    @patch("src.ai.template_composer.invoke_llm")
    def test_llm_failure_returns_error(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(content="", input_tokens=0, output_tokens=0)
        result = generate_template("Extract invoice fields")
        assert "error" in result
        assert result["fields"] == []

    @patch("src.ai.template_composer.invoke_llm")
    def test_invalid_json_returns_error(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(
            content="not json at all", input_tokens=10, output_tokens=5
        )
        result = generate_template("Extract invoice fields")
        assert "error" in result

    @patch("src.ai.template_composer.invoke_llm")
    def test_json_wrapped_in_markdown(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(
            content='```json\n{"name": "Test", "description": "Test", "fields": [{"name": "x", "type": "string"}]}\n```',
            input_tokens=50,
            output_tokens=50,
        )
        result = generate_template("Extract x")
        assert result["name"] == "Test"
        assert len(result["fields"]) == 1

    @patch("src.ai.template_composer.invoke_llm")
    def test_field_names_normalized(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(
            content=json.dumps(
                {
                    "name": "Test",
                    "fields": [
                        {"name": "Invoice Number", "type": "string"},
                        {"name": "Total Amount", "type": "float"},
                    ],
                }
            ),
            input_tokens=50,
            output_tokens=50,
        )
        result = generate_template("Extract invoice number and total")
        assert result["fields"][0]["name"] == "invoice_number"
        assert result["fields"][1]["name"] == "total_amount"


# ---------------------------------------------------------------------------
# Surrogate Verifier unit tests
# ---------------------------------------------------------------------------


class TestFormatTrace:
    """Trace formatting for LLM prompt [BLK-070]."""

    def test_empty_trace(self):
        result = _format_trace([])
        assert "No trace entries" in result

    def test_format_trace_entries(self):
        entries = [
            MagicMock(
                step=1,
                tool_name="ocr",
                thought="Read text",
                tool_args={"image_path": "/doc.png"},
                result_summary="Success",
            ),
            MagicMock(
                step=2,
                tool_name="vlm",
                thought="Ask VLM",
                tool_args={"image_path": "/doc.png", "question": "What is the total?"},
                result_summary="$42.50",
            ),
        ]
        result = _format_trace(entries)
        assert "Step 1" in result
        assert "ocr" in result
        assert "Step 2" in result
        assert "vlm" in result


class TestFormatGapReport:
    """Gap report formatting [BLK-070]."""

    def test_none_gap_report(self):
        result = _format_gap_report(None)
        assert "No gap report" in result

    def test_format_gap_report(self):
        gr = MagicMock()
        gr.total_fields = 5
        gr.satisfied = [MagicMock(field="invoice_number"), MagicMock(field="vendor_name")]
        gr.gaps = [MagicMock(field="total_amount"), MagicMock(field="invoice_date")]
        result = _format_gap_report(gr)
        assert "Total fields: 5" in result
        assert "invoice_number" in result
        assert "total_amount" in result


class TestFormatExtraction:
    """Extraction formatting [BLK-070]."""

    def test_empty_extraction(self):
        result = _format_extraction({})
        assert "No fields extracted" in result

    def test_format_extraction(self):
        fv = MagicMock()
        fv.value = "$42.50"
        fv.confidence = 0.92
        result = _format_extraction({"total_amount": fv})
        assert "total_amount" in result
        assert "$42.50" in result
        assert "0.92" in result

    def test_format_plain_values(self):
        result = _format_extraction({"vendor": "ACME Corp"})
        assert "vendor" in result
        assert "ACME Corp" in result


class TestVerifySkill:
    """Surrogate Verifier [BLK-070]."""

    @patch("src.ai.surrogate_verifier.invoke_llm")
    def test_successful_verification(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(
            content=json.dumps(
                {
                    "diagnoses": [
                        {
                            "type": "tool_selection",
                            "severity": "high",
                            "message": "Used OCR on a region better suited for VLM",
                        },
                        {
                            "type": "invariant",
                            "severity": "medium",
                            "message": "Missing date comparison invariant for due_date",
                        },
                    ],
                    "proposed_tests": [
                        {
                            "assertion": "total_amount == sum(line_items.total) + tax_amount",
                            "reason": "math invariant",
                        },
                    ],
                    "skill_patch": {
                        "invariants_to_add": [
                            {
                                "name": "total_check",
                                "fields": ["total", "line_items", "tax"],
                                "description": "Verify total",
                            }
                        ],
                    },
                }
            ),
            input_tokens=200,
            output_tokens=300,
        )
        result = verify_skill(
            skill={"name": "invoice", "system_prompt": "Extract invoice fields"},
            trace=[],
            gap_report=None,
            extraction={},
        )
        assert len(result["diagnoses"]) == 2
        assert result["diagnoses"][0]["type"] == "tool_selection"
        assert len(result["proposed_tests"]) == 1
        assert "invariants_to_add" in result["skill_patch"]
        assert "_token_usage" in result

    @patch("src.ai.surrogate_verifier.invoke_llm")
    def test_llm_failure_falls_back_to_heuristic(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(content="", input_tokens=0, output_tokens=0)
        result = verify_skill(skill={}, trace=[], gap_report=None, extraction={})
        assert "diagnoses" in result
        assert "proposed_tests" in result
        assert "skill_patch" in result
        assert "error" not in result

    @patch("src.ai.surrogate_verifier.invoke_llm")
    def test_invalid_json_falls_back_to_heuristic(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(content="not json", input_tokens=10, output_tokens=5)
        result = verify_skill(skill={}, trace=[], gap_report=None, extraction={})
        assert "diagnoses" in result
        assert "error" not in result

    @patch("src.ai.surrogate_verifier.invoke_llm")
    def test_missing_keys_defaulted(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(
            content=json.dumps(
                {"diagnoses": [{"type": "other", "severity": "low", "message": "test"}]}
            ),
            input_tokens=50,
            output_tokens=50,
        )
        result = verify_skill(skill={}, trace=[], gap_report=None, extraction={})
        assert result["proposed_tests"] == []
        assert result["skill_patch"] == {}


# ---------------------------------------------------------------------------
# Integration tests with FastAPI
# ---------------------------------------------------------------------------


class TestTemplateGenerateEndpoint:
    """POST /templates/generate endpoint [BLK-067]."""

    def _create_app(self) -> FastAPI:
        app = FastAPI()
        from src.api.routes.templates import router

        app.include_router(router, prefix="/api/v1")
        return app

    @patch("src.ai.template_composer.invoke_llm")
    def test_generate_endpoint_success(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(
            content=json.dumps(
                {
                    "name": "Invoice Schema",
                    "description": "Invoice extraction",
                    "fields": [
                        {
                            "name": "vendor_name",
                            "type": "string",
                            "required": True,
                            "threshold": 0.8,
                        },
                        {
                            "name": "total_amount",
                            "type": "float",
                            "required": True,
                            "threshold": 0.85,
                        },
                        {
                            "name": "invoice_date",
                            "type": "date",
                            "required": True,
                            "threshold": 0.85,
                        },
                        {
                            "name": "invoice_number",
                            "type": "string",
                            "required": True,
                            "threshold": 0.85,
                        },
                        {
                            "name": "is_paid",
                            "type": "boolean",
                            "required": False,
                            "threshold": 0.75,
                        },
                    ],
                }
            ),
            input_tokens=100,
            output_tokens=200,
        )
        app = self._create_app()
        client = TestClient(app)
        resp = client.post(
            "/api/v1/templates/generate", json={"description": "Extract invoice fields"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Invoice Schema"
        assert len(data["fields"]) == 5

    @patch("src.ai.template_composer.invoke_llm")
    def test_generate_endpoint_llm_failure(self, mock_invoke):
        mock_invoke.return_value = LLMResponse(content="", input_tokens=0, output_tokens=0)
        app = self._create_app()
        client = TestClient(app)
        resp = client.post("/api/v1/templates/generate", json={"description": "Extract fields"})
        assert resp.status_code == 503


class TestSkillVerifyEndpoint:
    """POST /skills/{id}/verify endpoint [BLK-070]."""

    def _create_app(self, tmp_path) -> FastAPI:
        app = FastAPI()
        from src.api.routes.skills import router

        app.include_router(router, prefix="/api/v1")

        # Create a test skill in the store
        from src.definitions.store import DefinitionStore, get_store
        import src.definitions.store as store_module

        store_module._store = DefinitionStore(base_dir=str(tmp_path))
        store_module._store.create_skill(
            "test-skill",
            {
                "id": "test-skill",
                "name": "Test Skill",
                "system_prompt": "Extract fields",
                "tools": ["ocr", "vlm"],
            },
        )
        return app

    @patch("src.ai.surrogate_verifier.invoke_llm")
    def test_verify_endpoint_success(self, mock_invoke, tmp_path):
        mock_invoke.return_value = LLMResponse(
            content=json.dumps(
                {
                    "diagnoses": [
                        {
                            "type": "invariant",
                            "severity": "high",
                            "message": "Missing total invariant",
                        }
                    ],
                    "proposed_tests": [{"assertion": "total > 0", "reason": "sanity"}],
                    "skill_patch": {
                        "invariants_to_add": [
                            {
                                "name": "total_pos",
                                "fields": ["total"],
                                "description": "Total must be positive",
                            }
                        ]
                    },
                }
            ),
            input_tokens=200,
            output_tokens=300,
        )
        app = self._create_app(tmp_path)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/skills/test-skill/verify",
            json={
                "trace": [],
                "gap_report": {"total_fields": 3, "satisfied": [], "gaps": []},
                "extraction": {},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["diagnoses"]) == 1
        assert data["diagnoses"][0]["type"] == "invariant"

    def test_verify_endpoint_skill_not_found(self, tmp_path):
        app = self._create_app(tmp_path)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/skills/nonexistent/verify",
            json={
                "trace": [],
                "gap_report": {},
                "extraction": {},
            },
        )
        assert resp.status_code == 404

    @patch("src.ai.surrogate_verifier.invoke_llm")
    def test_verify_endpoint_llm_failure_heuristic_fallback(self, mock_invoke, tmp_path):
        mock_invoke.return_value = LLMResponse(content="", input_tokens=0, output_tokens=0)
        app = self._create_app(tmp_path)
        client = TestClient(app)
        resp = client.post(
            "/api/v1/skills/test-skill/verify",
            json={
                "trace": [],
                "gap_report": {},
                "extraction": {},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "diagnoses" in data
