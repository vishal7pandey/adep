"""Tests for AI Skill Composer [BLK-068, SCRUM-75].

Tests cover:
- generate_skill with heuristic fallback (no LLM credentials)
- Validation of all skill fields
- apply_skill_patch from Surrogate Verifier output
- co_evolve_skill loop convergence
- API endpoints (compose, co-evolve)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.ai.skill_composer import (
    CoEvolutionResult,
    _heuristic_skill,
    _normalize_name,
    _validate_confidence_overrides,
    _validate_failure_actions,
    _validate_invariants,
    _validate_probe_order,
    _validate_tool_preferences,
    apply_skill_patch,
    co_evolve_skill,
    generate_skill,
)


# ---------------------------------------------------------------------------
# Unit tests — validation helpers
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_simple(self):
        assert _normalize_name("Invoice") == "invoice"

    def test_with_spaces(self):
        assert _normalize_name("Bank Statement") == "bank_statement"

    def test_with_special_chars(self):
        assert _normalize_name("P&ID Diagram!") == "pid_diagram"

    def test_empty(self):
        assert _normalize_name("") == ""


class TestValidateToolPreferences:
    def test_valid_tools(self):
        raw = {"text": "ocr", "table": "ocr", "handwriting": "vlm"}
        result = _validate_tool_preferences(raw)
        assert result == raw

    def test_unknown_tool_kept(self):
        raw = {"text": "ocr", "custom_region": "unknown_tool"}
        result = _validate_tool_preferences(raw)
        assert "custom_region" in result
        assert result["custom_region"] == "unknown_tool"

    def test_normalizes_case(self):
        raw = {"Text": "OCR"}
        result = _validate_tool_preferences(raw)
        assert "text" in result
        assert result["text"] == "ocr"

    def test_empty(self):
        assert _validate_tool_preferences({}) == {}


class TestValidateProbeOrder:
    def test_valid_entries(self):
        raw = [
            {"region_type": "header", "rationale": "Top of document"},
            {"region_type": "table", "rationale": "Main body"},
        ]
        result = _validate_probe_order(raw)
        assert len(result) == 2
        assert result[0]["region_type"] == "header"

    def test_skips_non_dict(self):
        raw = ["invalid", {"region_type": "header", "rationale": "ok"}]
        result = _validate_probe_order(raw)
        assert len(result) == 1

    def test_skips_empty_region(self):
        raw = [{"region_type": "", "rationale": "no region"}]
        result = _validate_probe_order(raw)
        assert len(result) == 0

    def test_empty(self):
        assert _validate_probe_order([]) == []


class TestValidateInvariants:
    def test_valid_invariants(self):
        raw = [
            {
                "name": "sum_check",
                "fields": ["subtotal", "tax", "total"],
                "description": "subtotal + tax == total",
            },
        ]
        result = _validate_invariants(raw)
        assert len(result) == 1
        assert result[0]["name"] == "sum_check"
        assert result[0]["fields"] == ["subtotal", "tax", "total"]

    def test_skips_non_dict(self):
        raw = ["invalid", {"name": "ok", "fields": [], "description": ""}]
        result = _validate_invariants(raw)
        assert len(result) == 1

    def test_skips_no_name(self):
        raw = [{"fields": ["a"], "description": "no name"}]
        result = _validate_invariants(raw)
        assert len(result) == 0

    def test_coerces_fields_to_list(self):
        raw = [{"name": "check", "fields": "single_field", "description": ""}]
        result = _validate_invariants(raw)
        assert result[0]["fields"] == ["single_field"]


class TestValidateFailureActions:
    def test_fills_defaults_for_all_gap_types(self):
        result = _validate_failure_actions({})
        for gt in (
            "missing",
            "type_error",
            "format_error",
            "ungrounded",
            "low_confidence",
            "invariant_failed",
            "semantic_fail",
        ):
            assert gt in result
            assert len(result[gt]) > 0

    def test_preserves_provided_actions(self):
        raw = {"missing": "Custom action for missing fields."}
        result = _validate_failure_actions(raw)
        assert result["missing"] == "Custom action for missing fields."
        # Other gap types should have defaults
        assert "type_error" in result

    def test_skips_invalid_gap_types(self):
        raw = {"invalid_gap_type": "action", "missing": "valid action"}
        result = _validate_failure_actions(raw)
        assert "invalid_gap_type" not in result
        assert "missing" in result


class TestValidateConfidenceOverrides:
    def test_valid_thresholds(self):
        raw = {"invoice_number": 0.85, "total": 0.90}
        result = _validate_confidence_overrides(raw)
        assert result == raw

    def test_clamps_invalid_values(self):
        raw = {"field1": 1.5, "field2": -0.5}
        result = _validate_confidence_overrides(raw)
        assert "field1" not in result
        assert "field2" not in result

    def test_skips_non_numeric(self):
        raw = {"field1": "high", "field2": 0.8}
        result = _validate_confidence_overrides(raw)
        assert "field1" not in result
        assert "field2" in result


# ---------------------------------------------------------------------------
# Unit tests — heuristic fallback
# ---------------------------------------------------------------------------


class TestHeuristicSkill:
    def test_invoice_keyword(self):
        skill = _heuristic_skill("Extract invoice fields from commercial invoices")
        assert skill["name"] != ""
        assert "invoice" in skill["system_prompt"].lower()
        assert len(skill["probe_order"]) >= 3
        assert len(skill["invariants"]) >= 1
        assert skill["invariants"][0]["name"] == "sum_check"

    def test_bank_statement_keyword(self):
        skill = _heuristic_skill("Extract bank statement transactions and balances")
        assert "bank" in skill["system_prompt"].lower()
        assert len(skill["invariants"]) >= 1
        assert "balance_check" in [i["name"] for i in skill["invariants"]]

    def test_generic_fallback(self):
        skill = _heuristic_skill("Extract data from customs declaration forms")
        assert skill["name"] != ""
        assert len(skill["system_prompt"]) > 0
        assert len(skill["probe_order"]) >= 3

    def test_empty_description(self):
        skill = _heuristic_skill("")
        assert skill["name"] == "custom"

    def test_sample_fields_in_confidence(self):
        skill = _heuristic_skill("Extract data", sample_fields=["field_a", "field_b"])
        assert "field_a" in skill["confidence_overrides"]
        assert "field_b" in skill["confidence_overrides"]


# ---------------------------------------------------------------------------
# Unit tests — generate_skill (with mocked LLM)
# ---------------------------------------------------------------------------


class TestGenerateSkill:
    def test_empty_description_returns_error(self):
        result = generate_skill("")
        assert "error" in result
        assert "required" in result["error"].lower()

    def test_whitespace_description_returns_error(self):
        result = generate_skill("   ")
        assert "error" in result

    def test_falls_back_to_heuristic_when_no_llm(self):
        """When invoke_llm returns empty content, should fall back to heuristic."""
        with patch("src.ai.skill_composer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content="", input_tokens=0, output_tokens=0, total_tokens=0
            )
            result = generate_skill("Extract invoice fields")
            assert result["name"] != ""
            assert "system_prompt" in result
            assert len(result["probe_order"]) > 0
            assert result.get("_heuristic") is True

    def test_parses_llm_response(self):
        """When LLM returns valid JSON, should parse and validate it."""
        mock_skill = {
            "name": "Custom Invoice",
            "description": "Custom invoice extraction skill",
            "system_prompt": "You are a custom invoice extraction agent.",
            "tool_preferences": {"text": "ocr", "table": "ocr"},
            "probe_order": [{"region_type": "header", "rationale": "Top region"}],
            "invariants": [{"name": "check1", "fields": ["a", "b"], "description": "a == b"}],
            "failure_actions": {"missing": "Re-probe the region."},
            "known_failures": "Common issues here.",
            "confidence_overrides": {"total": 0.90},
        }
        with patch("src.ai.skill_composer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps(mock_skill),
                input_tokens=100,
                output_tokens=200,
                total_tokens=300,
            )
            result = generate_skill("Extract custom invoice data")

            assert result["name"] == "custom_invoice"
            assert result["description"] == "Custom invoice extraction skill"
            assert "system_prompt" in result
            assert len(result["tool_preferences"]) == 2
            assert len(result["probe_order"]) == 1
            assert len(result["invariants"]) == 1
            # All gap types should be present (defaults filled)
            for gt in (
                "missing",
                "type_error",
                "format_error",
                "ungrounded",
                "low_confidence",
                "invariant_failed",
                "semantic_fail",
            ):
                assert gt in result["failure_actions"]
            assert result["confidence_overrides"]["total"] == 0.90
            assert result["_token_usage"]["total_tokens"] == 300

    def test_falls_back_on_invalid_json(self):
        with patch("src.ai.skill_composer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content="This is not JSON at all.",
                input_tokens=10,
                output_tokens=10,
                total_tokens=20,
            )
            result = generate_skill("Extract invoice fields")
            assert result.get("_heuristic") is True
            assert result["name"] != ""

    def test_with_sample_fields(self):
        with patch("src.ai.skill_composer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content="", input_tokens=0, output_tokens=0, total_tokens=0
            )
            result = generate_skill("Extract data", sample_fields=["amount", "date"])
            # Heuristic should include sample fields in confidence overrides
            assert "amount" in result["confidence_overrides"]
            assert "date" in result["confidence_overrides"]


# ---------------------------------------------------------------------------
# Unit tests — apply_skill_patch
# ---------------------------------------------------------------------------


class TestApplySkillPatch:
    def _base_skill(self) -> dict[str, Any]:
        return {
            "name": "test_skill",
            "system_prompt": "Original prompt.",
            "tool_preferences": {"text": "ocr"},
            "probe_order": [{"region_type": "header", "rationale": "Top"}],
            "invariants": [{"name": "existing", "fields": ["a"], "description": "existing check"}],
            "failure_actions": {"missing": "Default action."},
            "known_failures": "",
            "confidence_overrides": {},
        }

    def test_adds_new_invariant(self):
        skill = self._base_skill()
        patch = {
            "invariants_to_add": [
                {"name": "new_check", "fields": ["x", "y"], "description": "x == y"},
            ],
        }
        result = apply_skill_patch(skill, patch)
        names = [i["name"] for i in result["invariants"]]
        assert "existing" in names
        assert "new_check" in names

    def test_does_not_duplicate_existing_invariant(self):
        skill = self._base_skill()
        patch = {
            "invariants_to_add": [
                {"name": "existing", "fields": ["a"], "description": "already exists"},
            ],
        }
        result = apply_skill_patch(skill, patch)
        assert len(result["invariants"]) == 1

    def test_adds_failure_action(self):
        skill = self._base_skill()
        patch = {
            "failure_actions_to_add": {"low_confidence": "Re-crop and re-read."},
        }
        result = apply_skill_patch(skill, patch)
        assert result["failure_actions"]["low_confidence"] == "Re-crop and re-read."
        assert result["failure_actions"]["missing"] == "Default action."

    def test_adds_probe_order_first(self):
        skill = self._base_skill()
        patch = {
            "probe_order_adjustments": [
                {"region_type": "footer", "rationale": "Check footer first", "position": "first"},
            ],
        }
        result = apply_skill_patch(skill, patch)
        assert result["probe_order"][0]["region_type"] == "footer"

    def test_adds_probe_order_last(self):
        skill = self._base_skill()
        patch = {
            "probe_order_adjustments": [
                {"region_type": "footer", "rationale": "Check footer last", "position": "last"},
            ],
        }
        result = apply_skill_patch(skill, patch)
        assert result["probe_order"][-1]["region_type"] == "footer"

    def test_adds_probe_order_after(self):
        skill = self._base_skill()
        patch = {
            "probe_order_adjustments": [
                {"region_type": "table", "rationale": "After header", "position": "after:header"},
            ],
        }
        result = apply_skill_patch(skill, patch)
        assert result["probe_order"][1]["region_type"] == "table"

    def test_appends_system_prompt_suggestions(self):
        skill = self._base_skill()
        patch = {
            "system_prompt_suggestions": "Add more detail about handling handwriting.",
        }
        result = apply_skill_patch(skill, patch)
        assert "Original prompt." in result["system_prompt"]
        assert "Add more detail about handling handwriting." in result["system_prompt"]

    def test_empty_patch_returns_copy(self):
        skill = self._base_skill()
        result = apply_skill_patch(skill, {})
        assert result == skill
        assert result is not skill  # should be a copy

    def test_does_not_mutate_original(self):
        skill = self._base_skill()
        original_invariants = list(skill["invariants"])
        patch = {
            "invariants_to_add": [
                {"name": "new_check", "fields": ["x"], "description": "new"},
            ],
        }
        apply_skill_patch(skill, patch)
        assert skill["invariants"] == original_invariants  # original unchanged


# ---------------------------------------------------------------------------
# Unit tests — co_evolve_skill
# ---------------------------------------------------------------------------


class TestCoEvolveSkill:
    def test_converges_immediately_when_no_diagnoses(self):
        """If verifier returns no diagnoses, co-evolution should stop after 1 iteration."""
        with (
            patch("src.ai.skill_composer.invoke_llm") as mock_llm,
            patch("src.ai.surrogate_verifier.verify_skill") as mock_verify,
        ):
            mock_llm.return_value = MagicMock(
                content="", input_tokens=0, output_tokens=0, total_tokens=0
            )
            mock_verify.return_value = {
                "diagnoses": [],
                "proposed_tests": [],
                "skill_patch": {},
                "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }
            result = co_evolve_skill(
                description="Extract invoice data",
                trace=[],
                gap_report={"gaps": [], "satisfied": [], "total_fields": 5, "is_complete": True},
                extraction={},
                max_iterations=3,
            )
            assert result.iterations == 0
            assert len(result.verifier_reports) == 1
            assert len(result.history) == 1  # just the initial skill

    def test_runs_patch_loop(self):
        """When verifier returns diagnoses + patches, should iterate."""
        verifier_calls = [
            {
                "diagnoses": [
                    {"type": "invariant", "severity": "high", "message": "Missing sum check"}
                ],
                "proposed_tests": [],
                "skill_patch": {
                    "invariants_to_add": [
                        {
                            "name": "sum_check",
                            "fields": ["subtotal", "tax", "total"],
                            "description": "subtotal + tax == total",
                        },
                    ],
                    "failure_actions_to_add": {},
                    "probe_order_adjustments": [],
                    "system_prompt_suggestions": "Add sum check guidance.",
                },
                "_token_usage": {"input_tokens": 50, "output_tokens": 50, "total_tokens": 100},
            },
            {
                "diagnoses": [],
                "proposed_tests": [],
                "skill_patch": {},
                "_token_usage": {"input_tokens": 30, "output_tokens": 30, "total_tokens": 60},
            },
        ]
        with (
            patch("src.ai.skill_composer.invoke_llm") as mock_llm,
            patch("src.ai.surrogate_verifier.verify_skill") as mock_verify,
        ):
            mock_llm.return_value = MagicMock(
                content="", input_tokens=0, output_tokens=0, total_tokens=0
            )
            mock_verify.side_effect = verifier_calls
            result = co_evolve_skill(
                description="Extract invoice data",
                trace=[],
                gap_report={"gaps": [], "satisfied": [], "total_fields": 5},
                extraction={},
                max_iterations=3,
            )
            assert result.iterations == 1
            assert len(result.verifier_reports) == 2
            assert len(result.history) == 2  # initial + 1 patch
            # The patched skill should have the new invariant
            inv_names = [i["name"] for i in result.skill.get("invariants", [])]
            assert "sum_check" in inv_names

    def test_respects_max_iterations(self):
        """Should stop at max_iterations even if verifier keeps returning patches."""
        always_patch = {
            "diagnoses": [{"type": "other", "severity": "low", "message": "Issue"}],
            "proposed_tests": [],
            "skill_patch": {
                "invariants_to_add": [
                    {"name": "persistent_check", "fields": [], "description": ""}
                ],
                "failure_actions_to_add": {},
                "probe_order_adjustments": [],
                "system_prompt_suggestions": "Keep improving.",
            },
            "_token_usage": {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20},
        }
        with (
            patch("src.ai.skill_composer.invoke_llm") as mock_llm,
            patch("src.ai.surrogate_verifier.verify_skill") as mock_verify,
        ):
            mock_llm.return_value = MagicMock(
                content="", input_tokens=0, output_tokens=0, total_tokens=0
            )
            mock_verify.return_value = always_patch
            result = co_evolve_skill(
                description="Extract data",
                trace=[],
                gap_report={},
                extraction={},
                max_iterations=2,
            )
            assert result.iterations == 2
            assert len(result.verifier_reports) == 2

    def test_token_usage_accumulated(self):
        with (
            patch("src.ai.skill_composer.invoke_llm") as mock_llm,
            patch("src.ai.surrogate_verifier.verify_skill") as mock_verify,
        ):
            mock_llm.return_value = MagicMock(
                content="",
                input_tokens=100,
                output_tokens=50,
                total_tokens=150,
            )
            mock_verify.return_value = {
                "diagnoses": [],
                "proposed_tests": [],
                "skill_patch": {},
                "_token_usage": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300},
            }
            result = co_evolve_skill(
                description="Extract data",
                trace=[],
                gap_report={},
                extraction={},
                max_iterations=1,
            )
            assert result.token_usage["input_tokens"] >= 100
            assert result.token_usage["total_tokens"] >= 150


# ---------------------------------------------------------------------------
# Integration tests — API endpoints
# ---------------------------------------------------------------------------


class TestSkillComposerAPI:
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
        with patch("src.ai.skill_composer.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content="", input_tokens=0, output_tokens=0, total_tokens=0
            )
            response = client.post(
                "/api/v1/skills/compose",
                json={
                    "description": "Extract invoice number, date, and total from commercial invoices",
                    "sample_fields": ["invoice_number", "invoice_date", "total"],
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "system_prompt" in data
            assert "probe_order" in data
            assert "failure_actions" in data

    def test_compose_endpoint_empty_description(self, client: TestClient):
        response = client.post(
            "/api/v1/skills/compose",
            json={
                "description": "",
            },
        )
        assert response.status_code == 400

    def test_co_evolve_endpoint(self, client: TestClient):
        with (
            patch("src.ai.skill_composer.invoke_llm") as mock_llm,
            patch("src.ai.surrogate_verifier.verify_skill") as mock_verify,
        ):
            mock_llm.return_value = MagicMock(
                content="", input_tokens=0, output_tokens=0, total_tokens=0
            )
            mock_verify.return_value = {
                "diagnoses": [],
                "proposed_tests": [],
                "skill_patch": {},
                "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            }
            response = client.post(
                "/api/v1/skills/co-evolve",
                json={
                    "description": "Extract invoice fields",
                    "trace": [],
                    "gap_report": {},
                    "extraction": {},
                    "max_iterations": 2,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "skill" in data
            assert "iterations" in data
            assert "verifier_reports" in data
