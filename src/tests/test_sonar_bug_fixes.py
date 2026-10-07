"""Regression tests for the SonarCloud findings ADE-58 (S930) and ADE-59 (S6466).

ADE-58: ``decompose_skill`` (src/ai/query_rewriter.py) called ``invoke_llm(..., temperature=0.3)``,
a keyword ``invoke_llm`` does not accept (and current OpenAI reasoning models reject
``temperature`` anyway). The TypeError was swallowed by the broad ``except``, so the LLM path
silently never worked. Behind it sat a second mismatch: ``invoke_llm`` returns an ``LLMResponse``
but the code parsed the response as a string. These tests drive the real ``invoke_llm`` with a
stubbed chat client, so both mismatches show up.

ADE-59: ``_heuristic_verify`` (src/ai/surrogate_verifier.py) took ``gaps[:8]`` of whatever the gap
report held; a report whose ``gaps`` or ``satisfied`` is ``None`` (or missing) must be treated as
empty, never crash.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from src.agent.token_tracking import LLMResponse
from src.ai.query_rewriter import FailurePattern, decompose_skill
from src.ai.surrogate_verifier import _heuristic_verify
from src.providers import llm

# ---------------------------------------------------------------------------
# ADE-58
# ---------------------------------------------------------------------------

_SKILL = {
    "name": "invoice_skill",
    "description": "Extract invoice fields",
    "system_prompt": "You are extracting invoice fields.",
    "probe_order": [{"region_type": "header", "rationale": "Header"}],
    "invariants": [],
    "failure_actions": {"missing": "Re-probe"},
    "confidence_overrides": {"invoice_number": 0.9, "total": 0.95},
}

_PATTERN = FailurePattern(
    definition_id="def-invoice",
    failure_rate=0.5,
    total_runs=10,
    failed_runs=5,
    gap_type_counts={"missing": 5},
    failing_fields={"invoice_number": 5},
    avg_cycles_per_run=20.0,
)

_REPLY = {
    "rationale": "Split header from totals",
    "estimated_improvement": 0.2,
    "sub_skills": [
        {
            "name": "extract_header",
            "description": "Header fields",
            "system_prompt": "Focus on the header",
            "field_subset": ["invoice_number"],
            "probe_order": [],
            "validation_criteria": [],
        }
    ],
}


def _completion(text: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))], usage=None
    )


class TestDecomposeSkillCallsTheModelCorrectly:
    def test_llm_path_returns_the_sub_skills_the_model_proposed(self):
        """Through the real `invoke_llm`: the call must not raise and the reply must be parsed."""
        with patch.object(llm, "_call_llm", return_value=_completion(json.dumps(_REPLY))) as call:
            result = decompose_skill(_SKILL, _PATTERN, template_fields=["invoice_number"])
        call.assert_called_once()
        assert "LLM decomposition failed" not in result.rationale
        assert [s.name for s in result.sub_skills] == ["extract_header"]
        assert result.rationale == "Split header from totals"

    def test_invoke_llm_is_called_with_arguments_it_accepts(self):
        """`autospec` enforces invoke_llm's real signature: an unknown keyword raises TypeError."""
        reply = LLMResponse(content=json.dumps(_REPLY), input_tokens=1, output_tokens=1)
        with patch("src.ai.query_rewriter.invoke_llm", autospec=True, return_value=reply) as call:
            result = decompose_skill(_SKILL, _PATTERN, template_fields=["invoice_number"])
        call.assert_called_once()
        assert "temperature" not in call.call_args.kwargs
        assert len(result.sub_skills) == 1

    def test_reply_wrapped_in_prose_is_still_parsed(self):
        reply = LLMResponse(content="Here you go:\n" + json.dumps(_REPLY) + "\nDone.")
        with patch("src.ai.query_rewriter.invoke_llm", autospec=True, return_value=reply):
            result = decompose_skill(_SKILL, _PATTERN, template_fields=["invoice_number"])
        assert len(result.sub_skills) == 1

    def test_empty_reply_degrades_to_a_result_without_sub_skills(self):
        """`invoke_llm` returns empty content when the model call failed."""
        with patch("src.ai.query_rewriter.invoke_llm", autospec=True, return_value=LLMResponse("")):
            result = decompose_skill(_SKILL, _PATTERN, template_fields=["invoice_number"])
        assert result.sub_skills == []
        assert result.rationale in ("No JSON in LLM response", "Failed to parse LLM response")


# ---------------------------------------------------------------------------
# ADE-59
# ---------------------------------------------------------------------------

_VERIFY_SKILL = {"failure_actions": {"missing": "x"}}


def _verify(gap_report, trace=()):
    return _heuristic_verify(_VERIFY_SKILL, list(trace), gap_report, {})


class TestHeuristicVerifyEmptyCollections:
    def test_no_gap_report(self):
        report = _verify(None)
        assert report["diagnoses"][0]["type"] == "tool_selection"  # shallow trace only
        assert len(report["diagnoses"]) == 1

    def test_empty_gap_report_dict(self):
        assert _verify({}, trace=[1, 2])["diagnoses"] == []

    def test_empty_gap_and_satisfied_lists(self):
        report = _verify({"gaps": [], "satisfied": []}, trace=[1, 2])
        assert report["diagnoses"] == []
        assert report["proposed_tests"] == []

    def test_gaps_none_in_a_dict_is_treated_as_empty(self):
        report = _verify({"gaps": None, "satisfied": None}, trace=[1, 2])
        assert report["diagnoses"] == []

    def test_gaps_none_on_an_object_is_treated_as_empty(self):
        report = _verify(SimpleNamespace(gaps=None, satisfied=None), trace=[1, 2])
        assert report["diagnoses"] == []

    def test_at_most_eight_gaps_are_diagnosed(self):
        gaps = [{"field": f"f{i}", "gap_type": "missing", "detail": "d"} for i in range(12)]
        report = _verify({"gaps": gaps, "satisfied": []}, trace=[1, 2])
        assert [d["field"] for d in report["diagnoses"]] == [f"f{i}" for i in range(8)]
        assert len(report["proposed_tests"]) == 8

    def test_a_missing_gap_gets_the_high_severity_failure_action_diagnosis(self):
        gaps = [{"field": "total", "gap_type": "missing", "detail": "not found"}]
        report = _verify({"gaps": gaps, "satisfied": []}, trace=[1, 2])
        assert report["diagnoses"] == [
            {
                "type": "failure_action",
                "severity": "high",
                "message": "Gap remains for total: missing. not found",
                "field": "total",
            }
        ]
