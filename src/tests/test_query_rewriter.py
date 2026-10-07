"""Tests for Agentic Query Rewriting [BLK-073, SCRUM-80]."""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.agent.token_tracking import LLMResponse
from src.ai.query_rewriter import (
    analyze_failures,
    decompose_skill,
    heuristic_decompose,
    rewrite_failing_skill,
    FailurePattern,
    SubSkill,
    RewriteResult,
    DEFAULT_FAILURE_THRESHOLD,
    DEFAULT_MIN_SAMPLE_SIZE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_run(status: str, gaps: list[dict] | None = None, cycles: int = 10):
    """Create a mock run dict."""
    return {
        "run_id": f"run-{status}",
        "status": status,
        "total_cycles": cycles,
        "trace": [{"gaps": gaps or []}],
    }


def _make_skill():
    """Create a mock skill dict."""
    return {
        "name": "invoice_skill",
        "description": "Extract invoice fields",
        "system_prompt": "You are extracting invoice fields.",
        "probe_order": [
            {"region_type": "header", "rationale": "Header has metadata"},
            {"region_type": "table", "rationale": "Line items in table"},
            {"region_type": "footer", "rationale": "Totals in footer"},
        ],
        "invariants": [
            {
                "name": "subtotal_check",
                "fields": ["subtotal", "tax", "total"],
                "description": "subtotal + tax == total",
            },
        ],
        "failure_actions": {"missing": "Re-probe the region"},
        "confidence_overrides": {"invoice_number": 0.9, "total": 0.95, "vendor": 0.8},
    }


@pytest.fixture
def failing_runs():
    """Create a list of runs where >40% fail."""
    runs = []
    for i in range(10):
        if i < 5:
            runs.append(
                _make_run(
                    "failed",
                    gaps=[
                        {"gap_type": "missing", "field": "invoice_number"},
                        {"gap_type": "missing", "field": "invoice_number"},
                        {"gap_type": "low_confidence", "field": "total"},
                    ],
                    cycles=25,
                )
            )
        else:
            runs.append(_make_run("completed", cycles=12))
    return runs


@pytest.fixture
def passing_runs():
    """Create a list of runs where most succeed."""
    runs = []
    for i in range(10):
        if i < 2:
            runs.append(_make_run("failed", cycles=20))
        else:
            runs.append(_make_run("completed", cycles=10))
    return runs


# ---------------------------------------------------------------------------
# Failure analysis tests
# ---------------------------------------------------------------------------


class TestAnalyzeFailures:
    """Test failure pattern analysis."""

    def test_detects_high_failure_rate(self, failing_runs):
        pattern = analyze_failures("def-invoice", failing_runs)
        assert pattern is not None
        assert pattern.definition_id == "def-invoice"
        assert pattern.failure_rate == 0.5
        assert pattern.total_runs == 10
        assert pattern.failed_runs == 5
        assert "missing" in pattern.gap_type_counts
        assert "invoice_number" in pattern.failing_fields
        assert pattern.avg_cycles_per_run == 25.0

    def test_no_rewriting_for_low_failure_rate(self, passing_runs):
        pattern = analyze_failures("def-invoice", passing_runs)
        assert pattern is None  # 20% failure rate < 40% threshold

    def test_insufficient_samples(self):
        runs = [_make_run("failed") for _ in range(3)]
        pattern = analyze_failures("def-invoice", runs, min_sample=5)
        assert pattern is None

    def test_custom_threshold(self, passing_runs):
        # With a lower threshold, even 20% failure rate triggers
        pattern = analyze_failures("def-invoice", passing_runs, failure_threshold=0.1)
        assert pattern is not None
        assert pattern.failure_rate == 0.2

    def test_max_iterations_counts_as_failure(self):
        runs = [_make_run("max_iterations_reached") for _ in range(6)]
        runs += [_make_run("completed") for _ in range(4)]
        pattern = analyze_failures("def-invoice", runs)
        assert pattern is not None
        assert pattern.failed_runs == 6


# ---------------------------------------------------------------------------
# Heuristic decomposition tests
# ---------------------------------------------------------------------------


class TestHeuristicDecompose:
    """Test heuristic skill decomposition."""

    def test_decomposes_failing_fields(self):
        pattern = FailurePattern(
            definition_id="def-invoice",
            failure_rate=0.5,
            total_runs=10,
            failed_runs=5,
            gap_type_counts={"missing": 10},
            failing_fields={"invoice_number": 5, "total": 3},
            avg_cycles_per_run=25.0,
        )
        skill = _make_skill()
        result = heuristic_decompose(
            skill, pattern, template_fields=["invoice_number", "total", "vendor", "date"]
        )

        assert len(result.sub_skills) >= 1
        # Failing fields should be isolated
        failing_sub = result.sub_skills[0]
        assert "invoice_number" in failing_sub.field_subset
        assert result.rationale is not None
        assert result.estimated_improvement > 0

    def test_no_failing_fields(self):
        pattern = FailurePattern(
            definition_id="def-invoice",
            failure_rate=0.5,
            total_runs=10,
            failed_runs=5,
            gap_type_counts={"missing": 5},
            failing_fields={},
            avg_cycles_per_run=20.0,
        )
        skill = _make_skill()
        result = heuristic_decompose(
            skill, pattern, template_fields=["a", "b", "c", "d", "e", "f", "g", "h"]
        )

        # All fields split into groups of 4
        assert len(result.sub_skills) == 2
        assert all(len(ss.field_subset) <= 4 for ss in result.sub_skills)

    def test_rewritten_skill_has_sub_skills(self):
        pattern = FailurePattern(
            definition_id="def-invoice",
            failure_rate=0.5,
            total_runs=10,
            failed_runs=5,
            gap_type_counts={"missing": 5},
            failing_fields={"invoice_number": 5},
            avg_cycles_per_run=20.0,
        )
        skill = _make_skill()
        result = heuristic_decompose(skill, pattern, template_fields=["invoice_number", "total"])

        assert "sub_skills" in result.rewritten_skill
        assert result.rewritten_skill["name"] == "invoice_skill_rewritten"
        assert "Auto-rewritten" not in result.rewritten_skill["description"]
        assert "Heuristic rewrite" in result.rewritten_skill["description"]


# ---------------------------------------------------------------------------
# LLM decomposition tests (mocked)
# ---------------------------------------------------------------------------


class TestLLMDecompose:
    """Test LLM-powered decomposition."""

    def test_llm_decomposition_success(self):
        pattern = FailurePattern(
            definition_id="def-invoice",
            failure_rate=0.5,
            total_runs=10,
            failed_runs=5,
            gap_type_counts={"missing": 10},
            failing_fields={"invoice_number": 5, "total": 3},
            avg_cycles_per_run=25.0,
        )
        skill = _make_skill()

        mock_response = """{
            "rationale": "Split by visual proximity: header vs table vs footer",
            "estimated_improvement": 0.2,
            "sub_skills": [
                {
                    "name": "extract_header",
                    "description": "Extract header fields",
                    "system_prompt": "Focus on header region",
                    "field_subset": ["invoice_number", "vendor"],
                    "probe_order": [{"region_type": "header", "rationale": "Header"}],
                    "validation_criteria": ["invoice_number non-empty"]
                },
                {
                    "name": "extract_totals",
                    "description": "Extract total fields",
                    "system_prompt": "Focus on footer totals",
                    "field_subset": ["total"],
                    "probe_order": [{"region_type": "footer", "rationale": "Totals"}],
                    "validation_criteria": ["total is numeric"]
                }
            ]
        }"""

        with patch(
            "src.ai.query_rewriter.invoke_llm", return_value=LLMResponse(content=mock_response)
        ):
            result = decompose_skill(
                skill, pattern, template_fields=["invoice_number", "vendor", "total"]
            )

        assert len(result.sub_skills) == 2
        assert result.sub_skills[0].name == "extract_header"
        assert result.sub_skills[1].name == "extract_totals"
        assert result.rationale == "Split by visual proximity: header vs table vs footer"
        assert result.estimated_improvement == 0.2

    def test_llm_decomposition_fallback_on_error(self):
        pattern = FailurePattern(
            definition_id="def-invoice",
            failure_rate=0.5,
            total_runs=10,
            failed_runs=5,
            gap_type_counts={"missing": 5},
            failing_fields={"invoice_number": 5},
            avg_cycles_per_run=20.0,
        )
        skill = _make_skill()

        with patch("src.ai.query_rewriter.invoke_llm", side_effect=Exception("API error")):
            result = decompose_skill(skill, pattern, template_fields=["invoice_number", "total"])

        assert len(result.sub_skills) == 0
        assert "LLM decomposition failed" in result.rationale

    def test_llm_decomposition_invalid_json(self):
        pattern = FailurePattern(
            definition_id="def-invoice",
            failure_rate=0.5,
            total_runs=10,
            failed_runs=5,
            gap_type_counts={"missing": 5},
            failing_fields={"invoice_number": 5},
            avg_cycles_per_run=20.0,
        )
        skill = _make_skill()

        with patch(
            "src.ai.query_rewriter.invoke_llm", return_value=LLMResponse(content="not json at all")
        ):
            result = decompose_skill(skill, pattern, template_fields=["invoice_number"])

        assert len(result.sub_skills) == 0
        assert "No JSON" in result.rationale or "Failed to parse" in result.rationale


# ---------------------------------------------------------------------------
# Main entry point tests
# ---------------------------------------------------------------------------


class TestRewriteFailingSkill:
    """Test the main rewrite_failing_skill entry point."""

    def test_rewrite_triggers_on_high_failure(self, failing_runs):
        skill = _make_skill()
        with patch("src.ai.query_rewriter.invoke_llm") as mock_llm:
            mock_llm.return_value = LLMResponse(
                content='{"rationale": "test", "estimated_improvement": 0.1, "sub_skills": [{"name": "s1", "description": "d", "system_prompt": "p", "field_subset": ["a"], "probe_order": [], "validation_criteria": []}]}'
            )
            result = rewrite_failing_skill("def-invoice", failing_runs, skill, use_llm=True)

        assert result is not None
        assert result.original_definition_id == "def-invoice"
        assert len(result.sub_skills) == 1

    def test_rewrite_returns_none_for_low_failure(self, passing_runs):
        skill = _make_skill()
        result = rewrite_failing_skill("def-invoice", passing_runs, skill, use_llm=False)
        assert result is None

    def test_rewrite_heuristic_fallback(self, failing_runs):
        skill = _make_skill()
        with patch("src.ai.query_rewriter.invoke_llm", side_effect=Exception("API error")):
            result = rewrite_failing_skill("def-invoice", failing_runs, skill, use_llm=True)

        # Should fall back to heuristic
        assert result is not None
        assert len(result.sub_skills) > 0
        assert "Heuristic" in result.rewritten_skill.get("description", "")

    def test_rewrite_heuristic_only(self, failing_runs):
        skill = _make_skill()
        result = rewrite_failing_skill("def-invoice", failing_runs, skill, use_llm=False)
        assert result is not None
        assert len(result.sub_skills) > 0
