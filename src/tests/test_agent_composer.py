"""Tests for AI Agent Composer [BLK-069, SCRUM-76].

Tests cover:
- compose_agent with mocked sub-composers (template + skill + config LLM)
- Validation of definition fields (ID normalization, config, tools, task type)
- Heuristic fallback when LLM is unavailable
- Save-to-store flow
- API endpoint (POST /definitions/compose)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.ai.agent_composer import (
    AgentComposerResult,
    _derive_confidence_threshold,
    _derive_tool_names,
    _heuristic_definition_config,
    _normalize_definition_id,
    _validate_agent_config,
    compose_agent,
)


# ---------------------------------------------------------------------------
# Unit tests — validation helpers
# ---------------------------------------------------------------------------

class TestNormalizeDefinitionId:
    def test_adds_def_prefix(self):
        assert _normalize_definition_id("invoice") == "def-invoice"

    def test_preserves_def_prefix(self):
        assert _normalize_definition_id("def-invoice") == "def-invoice"

    def test_snake_case(self):
        assert _normalize_definition_id("Bank Statement") == "def-bank_statement"

    def test_special_chars(self):
        assert _normalize_definition_id("P&ID Diagram!") == "def-pid_diagram"

    def test_empty(self):
        assert _normalize_definition_id("") == "def-"


class TestValidateAgentConfig:
    def test_defaults(self):
        config = _validate_agent_config({})
        assert config["max_cycles_per_field"] == 5
        assert config["max_cycles_per_document"] == 20
        assert config["confidence_threshold"] == 0.85
        assert config["use_pdf_fast_path"] is False

    def test_valid_values(self):
        config = _validate_agent_config({
            "max_cycles_per_field": 8,
            "max_cycles_per_document": 35,
            "confidence_threshold": 0.90,
        })
        assert config["max_cycles_per_field"] == 8
        assert config["max_cycles_per_document"] == 35
        assert config["confidence_threshold"] == 0.90

    def test_clamps_invalid_values(self):
        config = _validate_agent_config({
            "max_cycles_per_field": 100,  # out of range
            "max_cycles_per_document": -5,  # out of range
            "confidence_threshold": 2.0,  # out of range
        })
        assert config["max_cycles_per_field"] == 5  # default
        assert config["max_cycles_per_document"] == 20  # default
        assert config["confidence_threshold"] == 0.85  # default

    def test_use_pdf_fast_path(self):
        config = _validate_agent_config({"use_pdf_fast_path": True})
        assert config["use_pdf_fast_path"] is True


class TestDeriveToolNames:
    def test_includes_baseline_tools(self):
        skill = {"tool_preferences": {}}
        template = {"fields": []}
        tools = _derive_tool_names(skill, template)
        assert "detect_layout" in tools
        assert "crop" in tools
        assert "ocr" in tools
        assert "vlm" in tools

    def test_includes_tools_from_skill(self):
        skill = {"tool_preferences": {"text": "ocr", "table": "read_table"}}
        template = {"fields": []}
        tools = _derive_tool_names(skill, template)
        assert "read_table" in tools

    def test_includes_read_table_for_list_fields(self):
        skill = {"tool_preferences": {}}
        template = {"fields": [{"name": "items", "type": "list"}]}
        tools = _derive_tool_names(skill, template)
        assert "read_table" in tools

    def test_no_duplicates(self):
        skill = {"tool_preferences": {"text": "ocr", "table": "ocr"}}
        template = {"fields": []}
        tools = _derive_tool_names(skill, template)
        assert tools.count("ocr") == 1

    def test_sorted(self):
        skill = {"tool_preferences": {"handwriting": "vlm", "text": "ocr"}}
        template = {"fields": []}
        tools = _derive_tool_names(skill, template)
        assert tools == sorted(tools)


class TestDeriveConfidenceThreshold:
    def test_uses_skill_overrides(self):
        skill = {"confidence_overrides": {"field_a": 0.85, "field_b": 0.80}}
        template = {"fields": []}
        assert _derive_confidence_threshold(skill, template) == 0.80  # min

    def test_uses_template_thresholds_when_no_overrides(self):
        skill = {"confidence_overrides": {}}
        template = {"fields": [{"confidence_threshold": 0.85}, {"confidence_threshold": 0.75}]}
        assert _derive_confidence_threshold(skill, template) == 0.75

    def test_default_when_nothing_available(self):
        skill = {"confidence_overrides": {}}
        template = {"fields": []}
        assert _derive_confidence_threshold(skill, template) == 0.85


# ---------------------------------------------------------------------------
# Unit tests — heuristic fallback
# ---------------------------------------------------------------------------

class TestHeuristicDefinitionConfig:
    def test_basic(self):
        config = _heuristic_definition_config("Extract invoice fields")
        assert config["definition_id"].startswith("def-")
        assert config["task_type"] == "extraction"
        assert config["max_cycles_per_field"] == 5

    def test_multi_page_heuristic(self):
        config = _heuristic_definition_config("Extract data from multi-page lease documents")
        assert config["max_cycles_per_document"] == 30

    def test_graph_extraction_heuristic(self):
        config = _heuristic_definition_config("Extract symbols from P&ID diagrams")
        assert config["task_type"] == "graph_extraction"

    def test_complex_heuristic(self):
        config = _heuristic_definition_config("Extract complex audit findings")
        assert config["max_cycles_per_document"] == 30

    def test_empty_description(self):
        config = _heuristic_definition_config("")
        assert config["definition_id"].startswith("def-")


# ---------------------------------------------------------------------------
# Unit tests — compose_agent (with mocked sub-composers)
# ---------------------------------------------------------------------------

class TestComposeAgent:
    def test_empty_description_returns_error(self):
        result = compose_agent("")
        assert len(result.errors) > 0
        assert "required" in result.errors[0].lower()
        assert result.definition == {}

    def test_full_pipeline_with_mocked_llm(self):
        """Test the full pipeline with all LLM calls mocked."""
        mock_template = {
            "name": "Custom Invoice Template",
            "description": "Template for custom invoices",
            "fields": [
                {"name": "invoice_number", "type": "string", "description": "Invoice ID", "required": True, "confidence_threshold": 0.85, "sub_fields": []},
                {"name": "total", "type": "float", "description": "Total amount", "required": True, "confidence_threshold": 0.85, "sub_fields": []},
                {"name": "line_items", "type": "list", "description": "Line items", "required": True, "confidence_threshold": 0.80, "sub_fields": []},
            ],
        }
        mock_skill = {
            "name": "custom_invoice",
            "description": "Custom invoice extraction skill",
            "system_prompt": "You are a custom invoice extraction agent.",
            "tool_preferences": {"text": "ocr", "table": "ocr", "handwriting": "vlm"},
            "probe_order": [{"region_type": "header", "rationale": "Top region"}],
            "invariants": [{"name": "sum_check", "fields": ["subtotal", "tax", "total"], "description": "subtotal + tax == total"}],
            "failure_actions": {"missing": "Re-probe the region."},
            "known_failures": "Common issues.",
            "confidence_overrides": {"invoice_number": 0.85, "total": 0.90},
        }
        mock_config = {
            "name": "Custom Invoice Extraction",
            "definition_id": "def-custom-invoice",
            "task_type": "extraction",
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 20,
            "confidence_threshold": 0.85,
            "system_prompt_override": None,
        }

        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {**mock_template, "_token_usage": {"input_tokens": 100, "output_tokens": 200, "total_tokens": 300}}
            mock_gen_skill.return_value = {**mock_skill, "_token_usage": {"input_tokens": 150, "output_tokens": 250, "total_tokens": 400}}
            mock_llm.return_value = MagicMock(
                content=json.dumps(mock_config),
                input_tokens=50,
                output_tokens=100,
                total_tokens=150,
            )

            result = compose_agent("Extract custom invoice fields")

            assert result.definition["id"] == "def-custom-invoice"
            assert result.definition["name"] == "Custom Invoice Extraction"
            assert result.definition["skill_id"] == "custom_invoice"
            assert result.definition["template_id"] == "custom_invoice_template"
            assert result.definition["task_type"] == "extraction"
            assert "detect_layout" in result.definition["tool_names"]
            assert "ocr" in result.definition["tool_names"]
            assert "read_table" in result.definition["tool_names"]  # because template has list field
            assert result.definition["agent_config"]["max_cycles_per_field"] == 5
            assert result.skill["name"] == "custom_invoice"
            assert result.template["name"] == "Custom Invoice Template"
            assert result.token_usage["total_tokens"] == 850  # 300 + 400 + 150
            assert len(result.errors) == 0

    def test_falls_back_to_heuristic_config_when_no_llm(self):
        """When the config LLM call fails, should use heuristic config."""
        mock_template = {
            "name": "Test",
            "description": "Test template",
            "fields": [{"name": "field1", "type": "string", "description": "", "required": True, "confidence_threshold": 0.8, "sub_fields": []}],
        }
        mock_skill = {
            "name": "test_skill",
            "description": "Test skill",
            "system_prompt": "You are a test agent.",
            "tool_preferences": {},
            "probe_order": [],
            "invariants": [],
            "failure_actions": {},
            "known_failures": "",
            "confidence_overrides": {},
        }

        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {**mock_template, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_gen_skill.return_value = {**mock_skill, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)

            result = compose_agent("Extract data from invoices")

            assert result.definition["id"].startswith("def-")
            assert result.definition["skill_id"] == "test_skill"
            assert result.definition["agent_config"]["max_cycles_per_field"] == 5

    def test_template_composer_error_recorded(self):
        """When template composer returns an error, it should be recorded."""
        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {"name": "", "description": "", "fields": [], "error": "LLM call failed"}
            mock_gen_skill.return_value = {
                "name": "test", "description": "", "system_prompt": "",
                "tool_preferences": {}, "probe_order": [], "invariants": [],
                "failure_actions": {}, "known_failures": "", "confidence_overrides": {},
                "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)

            result = compose_agent("Extract data")
            assert any("Template Composer error" in e for e in result.errors)

    def test_save_to_store(self):
        """Test that save_to_store=True persists to the store."""
        mock_template = {
            "name": "Test Template",
            "description": "Test",
            "fields": [{"name": "field1", "type": "string", "description": "", "required": True, "confidence_threshold": 0.8, "sub_fields": []}],
        }
        mock_skill = {
            "name": "test_skill",
            "description": "Test",
            "system_prompt": "Test prompt",
            "tool_preferences": {},
            "probe_order": [],
            "invariants": [],
            "failure_actions": {},
            "known_failures": "",
            "confidence_overrides": {},
        }

        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {**mock_template, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_gen_skill.return_value = {**mock_skill, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)

            # Mock the store
            mock_store = MagicMock()
            mock_store.create_skill.return_value = {"id": "test_skill"}
            mock_store.create_template.return_value = {"id": "test_template"}
            mock_store.create_definition.return_value = {"id": "def-test"}

            with patch("src.definitions.store.get_store", return_value=mock_store):
                result = compose_agent("Extract test data", save_to_store=True)

                assert mock_store.create_skill.called
                assert mock_store.create_template.called
                assert mock_store.create_definition.called

    def test_save_to_store_handles_existing_entries(self):
        """Test that save_to_store handles FileExistsError gracefully."""
        mock_template = {
            "name": "Test",
            "description": "Test",
            "fields": [{"name": "f1", "type": "string", "description": "", "required": True, "confidence_threshold": 0.8, "sub_fields": []}],
        }
        mock_skill = {
            "name": "test_skill",
            "description": "Test",
            "system_prompt": "Test",
            "tool_preferences": {},
            "probe_order": [],
            "invariants": [],
            "failure_actions": {},
            "known_failures": "",
            "confidence_overrides": {},
        }

        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {**mock_template, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_gen_skill.return_value = {**mock_skill, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)

            mock_store = MagicMock()
            mock_store.create_skill.side_effect = FileExistsError("exists")
            mock_store.create_template.side_effect = FileExistsError("exists")
            mock_store.create_definition.side_effect = FileExistsError("exists")

            with patch("src.definitions.store.get_store", return_value=mock_store):
                result = compose_agent("Extract test data", save_to_store=True)

                # Should record errors but not crash
                assert any("already exists" in e for e in result.errors)

    def test_system_prompt_override(self):
        """Test that system_prompt_override from LLM config is applied."""
        mock_template = {"name": "T", "description": "", "fields": []}
        mock_skill = {
            "name": "s", "description": "", "system_prompt": "default",
            "tool_preferences": {}, "probe_order": [], "invariants": [],
            "failure_actions": {}, "known_failures": "", "confidence_overrides": {},
        }
        mock_config = {
            "name": "Test",
            "definition_id": "def-test",
            "task_type": "extraction",
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 20,
            "confidence_threshold": 0.85,
            "system_prompt_override": "Custom system prompt for this definition.",
        }

        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {**mock_template, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_gen_skill.return_value = {**mock_skill, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_llm.return_value = MagicMock(
                content=json.dumps(mock_config),
                input_tokens=0, output_tokens=0, total_tokens=0,
            )

            result = compose_agent("Extract data")
            assert result.definition["system_prompt"] == "Custom system prompt for this definition."

    def test_token_usage_accumulated(self):
        """Test that token usage from all three LLM calls is accumulated."""
        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {
                "name": "T", "description": "", "fields": [],
                "_token_usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            }
            mock_gen_skill.return_value = {
                "name": "s", "description": "", "system_prompt": "",
                "tool_preferences": {}, "probe_order": [], "invariants": [],
                "failure_actions": {}, "known_failures": "", "confidence_overrides": {},
                "_token_usage": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300},
            }
            mock_llm.return_value = MagicMock(
                content="", input_tokens=50, output_tokens=25, total_tokens=75,
            )

            result = compose_agent("Extract data")
            assert result.token_usage["input_tokens"] == 350
            assert result.token_usage["output_tokens"] == 175
            assert result.token_usage["total_tokens"] == 525


# ---------------------------------------------------------------------------
# Unit tests — AgentComposerResult
# ---------------------------------------------------------------------------

class TestAgentComposerResult:
    def test_to_dict(self):
        result = AgentComposerResult(
            definition={"id": "def-test"},
            skill={"name": "test"},
            template={"name": "test"},
            token_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            errors=["warning"],
        )
        d = result.to_dict()
        assert d["definition"]["id"] == "def-test"
        assert d["skill"]["name"] == "test"
        assert d["template"]["name"] == "test"
        assert d["token_usage"]["total_tokens"] == 150
        assert d["errors"] == ["warning"]

    def test_defaults(self):
        result = AgentComposerResult()
        assert result.definition == {}
        assert result.skill == {}
        assert result.template == {}
        assert result.token_usage["total_tokens"] == 0
        assert result.errors == []


# ---------------------------------------------------------------------------
# Integration tests — API endpoint
# ---------------------------------------------------------------------------

class TestAgentComposerAPI:
    @pytest.fixture
    def client(self, tmp_path) -> TestClient:
        """Create a FastAPI TestClient with auth disabled."""
        import src.definitions.store as store_module
        import src.config as config_module
        from src.definitions.store import DefinitionStore

        old_store = store_module._store
        old_auth = config_module.settings.auth_enabled
        store_module._store = DefinitionStore(base_dir=tmp_path / ".adep")
        config_module.settings.auth_enabled = False

        from src.api.main import create_app
        app = create_app()
        test_client = TestClient(app)

        yield test_client

        config_module.settings.auth_enabled = old_auth
        store_module._store = old_store

    def test_compose_endpoint(self, client: TestClient):
        mock_template = {
            "name": "Test Template",
            "description": "Test",
            "fields": [{"name": "field1", "type": "string", "description": "", "required": True, "confidence_threshold": 0.8, "sub_fields": []}],
        }
        mock_skill = {
            "name": "test_skill",
            "description": "Test skill",
            "system_prompt": "You are a test agent.",
            "tool_preferences": {"text": "ocr"},
            "probe_order": [{"region_type": "header", "rationale": "Top"}],
            "invariants": [],
            "failure_actions": {},
            "known_failures": "",
            "confidence_overrides": {},
        }

        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {**mock_template, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_gen_skill.return_value = {**mock_skill, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)

            response = client.post("/api/v1/definitions/compose", json={
                "description": "Extract invoice number and total from commercial invoices",
            })
            assert response.status_code == 200
            data = response.json()
            assert "definition" in data
            assert "skill" in data
            assert "template" in data
            assert data["definition"]["id"].startswith("def-")
            assert "tool_names" in data["definition"]
            assert "agent_config" in data["definition"]

    def test_compose_endpoint_empty_description(self, client: TestClient):
        response = client.post("/api/v1/definitions/compose", json={
            "description": "",
        })
        assert response.status_code == 400

    def test_compose_endpoint_with_save(self, client: TestClient):
        """Test that save_to_store=True persists via the API."""
        mock_template = {
            "name": "API Test Template",
            "description": "Test",
            "fields": [{"name": "f1", "type": "string", "description": "", "required": True, "confidence_threshold": 0.8, "sub_fields": []}],
        }
        mock_skill = {
            "name": "api_test_skill",
            "description": "API test skill",
            "system_prompt": "You are a test agent.",
            "tool_preferences": {},
            "probe_order": [],
            "invariants": [],
            "failure_actions": {},
            "known_failures": "",
            "confidence_overrides": {},
        }

        with patch("src.ai.agent_composer.generate_template") as mock_gen_tmpl, \
             patch("src.ai.agent_composer.generate_skill") as mock_gen_skill, \
             patch("src.ai.agent_composer.invoke_llm") as mock_llm:
            mock_gen_tmpl.return_value = {**mock_template, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_gen_skill.return_value = {**mock_skill, "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)

            response = client.post("/api/v1/definitions/compose", json={
                "description": "Extract test data",
                "save_to_store": True,
            })
            assert response.status_code == 200
            data = response.json()
            assert data["definition"]["id"].startswith("def-")

            # Verify it was saved — fetch it back
            def_id = data["definition"]["id"]
            get_response = client.get(f"/api/v1/definitions/{def_id}")
            assert get_response.status_code == 200
