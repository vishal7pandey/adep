"""Tests for GEPA Reflective Prompt Evolution [BLK-071, SCRUM-78].

Tests cover:
- Candidate dataclass (fitness, to_dict)
- Evaluation (score computation, side info generation)
- Pareto front (dominance, ranking, selection)
- Reflection (LLM mock, lesson accumulation)
- Mutation (LLM mock, structure preservation)
- Heuristic merge (union of fields, stricter thresholds)
- Full optimize_skill loop (convergence, max iterations, population management)
- API endpoint (POST /skills/optimize)
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.ai.prompt_evolver import (
    Candidate,
    EvaluationResult,
    GEPAResult,
    _compute_pareto_ranks,
    _dominates,
    _evaluate_candidate,
    _heuristic_merge,
    _merge_candidates,
    _mutate,
    _reflect,
    _select_from_pareto,
    optimize_skill,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

def _make_skill(name: str = "test", system_prompt: str = "Extract data.") -> dict[str, Any]:
    return {
        "name": name,
        "description": "Test skill",
        "system_prompt": system_prompt,
        "tool_preferences": {"text": "ocr", "table": "ocr"},
        "probe_order": [{"region_type": "header", "rationale": "Top"}],
        "invariants": [],
        "failure_actions": {"missing": "Re-probe"},
        "known_failures": "",
        "confidence_overrides": {"total": 0.85},
    }


def _make_trace(steps: int = 3) -> list[dict[str, Any]]:
    return [
        {"step": i + 1, "tool_name": "ocr", "thought": f"Step {i+1}", "tool_args": {}, "result": "ok"}
        for i in range(steps)
    ]


def _make_gap_report(satisfied: int = 3, gaps: int = 1) -> dict[str, Any]:
    return {
        "total_fields": satisfied + gaps,
        "satisfied": [{"field": f"field_{i}"} for i in range(satisfied)],
        "gaps": [{"field": f"gap_{i}", "gap_type": "missing", "detail": "Not found"} for i in range(gaps)],
    }


def _make_extraction(fields: int = 3) -> dict[str, Any]:
    return {
        f"field_{i}": {"value": f"val_{i}", "confidence": 0.85 + i * 0.03}
        for i in range(fields)
    }


# ---------------------------------------------------------------------------
# Unit tests — Candidate
# ---------------------------------------------------------------------------

class TestCandidate:
    def test_fitness_default(self):
        c = Candidate(skill={})
        assert c.fitness() == 0.0

    def test_fitness_with_scores(self):
        c = Candidate(
            skill={},
            scores={"field_coverage": 0.8, "avg_confidence": 0.9, "token_efficiency": 0.01, "gap_severity": 0.2},
        )
        # 0.8*0.4 + 0.9*0.3 + 0.01*0.2 - 0.2*0.1 = 0.32 + 0.27 + 0.002 - 0.02 = 0.572
        assert abs(c.fitness() - 0.572) < 0.001

    def test_to_dict(self):
        c = Candidate(
            skill={"name": "test"},
            scores={"field_coverage": 0.5},
            lessons=["lesson1"],
            candidate_id="c1",
            generation=2,
            pareto_rank=0,
        )
        d = c.to_dict()
        assert d["candidate_id"] == "c1"
        assert d["generation"] == 2
        assert d["pareto_rank"] == 0
        assert d["skill"]["name"] == "test"
        assert d["lessons"] == ["lesson1"]
        assert "fitness" in d


# ---------------------------------------------------------------------------
# Unit tests — Evaluation
# ---------------------------------------------------------------------------

class TestEvaluateCandidate:
    def test_basic_evaluation(self):
        skill = _make_skill()
        traces = [_make_trace(3), _make_trace(2)]
        gap_reports = [_make_gap_report(3, 1), _make_gap_report(2, 2)]
        extractions = [_make_extraction(3), _make_extraction(2)]

        result = _evaluate_candidate(skill, traces, gap_reports, extractions)

        assert "field_coverage" in result.scores
        assert "avg_confidence" in result.scores
        assert "token_efficiency" in result.scores
        assert "gap_severity" in result.scores
        assert 0.0 <= result.scores["field_coverage"] <= 1.0
        assert result.side_info != ""
        assert result.trace_summary != ""

    def test_empty_traces(self):
        result = _evaluate_candidate(_make_skill(), [], [], [])
        assert result.scores["field_coverage"] == 0.0
        assert result.scores["avg_confidence"] == 0.0

    def test_full_coverage(self):
        traces = [_make_trace(3)]
        gap_reports = [_make_gap_report(5, 0)]
        extractions = [_make_extraction(5)]

        result = _evaluate_candidate(_make_skill(), traces, gap_reports, extractions)
        assert result.scores["field_coverage"] == 1.0
        assert result.scores["gap_severity"] == 0.0

    def test_token_efficiency(self):
        traces = [_make_trace(3)]
        gap_reports = [_make_gap_report(3, 0)]
        extractions = [_make_extraction(3)]
        token_usages = [{"total_tokens": 1000}]

        result = _evaluate_candidate(_make_skill(), traces, gap_reports, extractions, token_usages)
        assert result.scores["token_efficiency"] == 3 / 1000

    def test_side_info_includes_gap_details(self):
        traces = [_make_trace(2)]
        gap_reports = [_make_gap_report(1, 2)]
        extractions = [_make_extraction(1)]

        result = _evaluate_candidate(_make_skill(), traces, gap_reports, extractions)
        assert "gap" in result.side_info.lower()


# ---------------------------------------------------------------------------
# Unit tests — Pareto front
# ---------------------------------------------------------------------------

class TestDominates:
    def test_a_dominates_b(self):
        a = Candidate(skill={}, scores={"field_coverage": 0.9, "avg_confidence": 0.9, "token_efficiency": 0.01, "gap_severity": 0.1})
        b = Candidate(skill={}, scores={"field_coverage": 0.5, "avg_confidence": 0.7, "token_efficiency": 0.005, "gap_severity": 0.3})
        assert _dominates(a, b)

    def test_b_does_not_dominate_a(self):
        a = Candidate(skill={}, scores={"field_coverage": 0.9, "avg_confidence": 0.9, "token_efficiency": 0.01, "gap_severity": 0.1})
        b = Candidate(skill={}, scores={"field_coverage": 0.5, "avg_confidence": 0.7, "token_efficiency": 0.005, "gap_severity": 0.3})
        assert not _dominates(b, a)

    def test_non_dominated(self):
        a = Candidate(skill={}, scores={"field_coverage": 0.9, "avg_confidence": 0.7, "token_efficiency": 0.01, "gap_severity": 0.1})
        b = Candidate(skill={}, scores={"field_coverage": 0.5, "avg_confidence": 0.9, "token_efficiency": 0.01, "gap_severity": 0.1})
        assert not _dominates(a, b)
        assert not _dominates(b, a)

    def test_equal_scores_no_domination(self):
        a = Candidate(skill={}, scores={"field_coverage": 0.8, "avg_confidence": 0.8, "token_efficiency": 0.01, "gap_severity": 0.1})
        b = Candidate(skill={}, scores={"field_coverage": 0.8, "avg_confidence": 0.8, "token_efficiency": 0.01, "gap_severity": 0.1})
        assert not _dominates(a, b)


class TestComputeParetoRanks:
    def test_single_candidate(self):
        c = Candidate(skill={}, scores={"field_coverage": 0.8, "avg_confidence": 0.8, "token_efficiency": 0.01, "gap_severity": 0.1})
        _compute_pareto_ranks([c])
        assert c.pareto_rank == 0

    def test_two_fronts(self):
        a = Candidate(skill={}, scores={"field_coverage": 0.9, "avg_confidence": 0.9, "token_efficiency": 0.01, "gap_severity": 0.1})
        b = Candidate(skill={}, scores={"field_coverage": 0.9, "avg_confidence": 0.9, "token_efficiency": 0.01, "gap_severity": 0.1})
        c = Candidate(skill={}, scores={"field_coverage": 0.5, "avg_confidence": 0.5, "token_efficiency": 0.005, "gap_severity": 0.3})
        _compute_pareto_ranks([a, b, c])
        assert a.pareto_rank == 0
        assert b.pareto_rank == 0
        assert c.pareto_rank == 1


class TestSelectFromPareto:
    def test_selects_from_best_front(self):
        a = Candidate(skill={"name": "a"}, scores={"field_coverage": 0.9, "avg_confidence": 0.9, "token_efficiency": 0.01, "gap_severity": 0.1})
        b = Candidate(skill={"name": "b"}, scores={"field_coverage": 0.5, "avg_confidence": 0.5, "token_efficiency": 0.005, "gap_severity": 0.3})
        _compute_pareto_ranks([a, b])

        import random
        rng = random.Random(42)
        selected = _select_from_pareto([a, b], rng)
        assert selected.pareto_rank == 0

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _select_from_pareto([])


# ---------------------------------------------------------------------------
# Unit tests — Reflection
# ---------------------------------------------------------------------------

class TestReflect:
    def test_reflect_with_llm(self):
        candidate = Candidate(
            skill=_make_skill(),
            scores={"field_coverage": 0.5},
            lessons=["prior lesson"],
        )
        eval_result = EvaluationResult(
            scores={"field_coverage": 0.5},
            side_info="Field coverage: 50%",
        )

        mock_reflection = {
            "lessons": ["Add more specific probe order", "Improve failure actions"],
            "diagnoses": [{"type": "system_prompt", "severity": "high", "message": "Too vague", "field": ""}],
            "proposed_mutations": {"system_prompt_hint": "Be more specific"},
        }

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps(mock_reflection),
                input_tokens=100, output_tokens=200, total_tokens=300,
            )
            result = _reflect(candidate, eval_result)

            assert len(result["lessons"]) == 2
            assert "Add more specific probe order" in result["lessons"][0]
            assert result["_token_usage"]["total_tokens"] == 300

    def test_reflect_no_llm(self):
        candidate = Candidate(skill=_make_skill(), scores={})
        eval_result = EvaluationResult(scores={}, side_info="No data")

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)
            result = _reflect(candidate, eval_result)

            assert result["lessons"] == []
            assert result["diagnoses"] == []

    def test_reflect_invalid_json(self):
        candidate = Candidate(skill=_make_skill(), scores={})
        eval_result = EvaluationResult(scores={}, side_info="No data")

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(content="not json", input_tokens=10, output_tokens=20, total_tokens=30)
            result = _reflect(candidate, eval_result)

            assert result["lessons"] == []


# ---------------------------------------------------------------------------
# Unit tests — Mutation
# ---------------------------------------------------------------------------

class TestMutate:
    def test_mutate_with_llm(self):
        candidate = Candidate(skill=_make_skill(system_prompt="Original prompt"))
        reflection = {
            "lessons": ["Be more specific"],
            "proposed_mutations": {"system_prompt_hint": "Add document-specific cues"},
        }

        mutated_skill = _make_skill(system_prompt="Improved prompt with specific cues")

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps(mutated_skill),
                input_tokens=100, output_tokens=200, total_tokens=300,
            )
            new_skill, tu = _mutate(candidate, reflection)

            assert new_skill["system_prompt"] == "Improved prompt with specific cues"
            assert tu["total_tokens"] == 300

    def test_mutate_no_llm_returns_original(self):
        candidate = Candidate(skill=_make_skill(system_prompt="Original"))
        reflection = {"lessons": [], "proposed_mutations": {}}

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)
            new_skill, tu = _mutate(candidate, reflection)

            assert new_skill["system_prompt"] == "Original"

    def test_mutate_preserves_missing_keys(self):
        candidate = Candidate(skill=_make_skill())
        reflection = {"lessons": [], "proposed_mutations": {}}

        # LLM returns partial skill (missing some keys)
        partial = {"name": "new_name", "system_prompt": "New prompt"}

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps(partial),
                input_tokens=0, output_tokens=0, total_tokens=0,
            )
            new_skill, _ = _mutate(candidate, reflection)

            assert new_skill["name"] == "new_name"
            assert new_skill["system_prompt"] == "New prompt"
            # Inherited from parent
            assert new_skill["tool_preferences"] == candidate.skill["tool_preferences"]
            assert new_skill["probe_order"] == candidate.skill["probe_order"]


# ---------------------------------------------------------------------------
# Unit tests — Merge
# ---------------------------------------------------------------------------

class TestHeuristicMerge:
    def test_merges_tool_preferences(self):
        a = _make_skill()
        a["tool_preferences"] = {"text": "ocr", "table": "ocr"}
        b = _make_skill()
        b["tool_preferences"] = {"handwriting": "vlm", "stamp": "vlm"}

        merged = _heuristic_merge(a, b)
        assert "text" in merged["tool_preferences"]
        assert "handwriting" in merged["tool_preferences"]

    def test_merges_invariants_dedup(self):
        a = _make_skill()
        a["invariants"] = [{"name": "sum_check", "fields": ["total"], "description": "check"}]
        b = _make_skill()
        b["invariants"] = [
            {"name": "sum_check", "fields": ["total"], "description": "check"},
            {"name": "date_check", "fields": ["date"], "description": "check date"},
        ]

        merged = _heuristic_merge(a, b)
        inv_names = [i["name"] for i in merged["invariants"]]
        assert "sum_check" in inv_names
        assert "date_check" in inv_names
        assert inv_names.count("sum_check") == 1

    def test_confidence_overrides_take_stricter(self):
        a = _make_skill()
        a["confidence_overrides"] = {"total": 0.85, "vendor": 0.80}
        b = _make_skill()
        b["confidence_overrides"] = {"total": 0.90, "date": 0.75}

        merged = _heuristic_merge(a, b)
        assert merged["confidence_overrides"]["total"] == 0.90  # stricter
        assert merged["confidence_overrides"]["vendor"] == 0.80
        assert merged["confidence_overrides"]["date"] == 0.75

    def test_merges_failure_actions(self):
        a = _make_skill()
        a["failure_actions"] = {"missing": "Re-probe A"}
        b = _make_skill()
        b["failure_actions"] = {"type_error": "Re-read B"}

        merged = _heuristic_merge(a, b)
        assert "missing" in merged["failure_actions"]
        assert "type_error" in merged["failure_actions"]


class TestMergeCandidates:
    def test_merge_with_llm(self):
        a = Candidate(skill=_make_skill(name="skill_a"), scores={"field_coverage": 0.9})
        b = Candidate(skill=_make_skill(name="skill_b"), scores={"avg_confidence": 0.9})

        merged_skill = _make_skill(name="merged_skill")
        merged_skill["system_prompt"] = "Merged prompt"

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps(merged_skill),
                input_tokens=50, output_tokens=100, total_tokens=150,
            )
            result, tu = _merge_candidates(a, b)

            assert result["name"] == "merged_skill"
            assert tu["total_tokens"] == 150

    def test_merge_no_llm_uses_heuristic(self):
        a = Candidate(skill=_make_skill(name="a"), scores={})
        b = Candidate(skill=_make_skill(name="b"), scores={})

        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0)
            result, _ = _merge_candidates(a, b)

            # Heuristic merge should have union of tool_preferences
            assert "text" in result["tool_preferences"]


# ---------------------------------------------------------------------------
# Unit tests — optimize_skill (full loop)
# ---------------------------------------------------------------------------

class TestOptimizeSkill:
    def test_empty_seed_returns_empty(self):
        result = optimize_skill({}, [_make_trace()], [_make_gap_report()], [_make_extraction()])
        assert result.best_candidate is None
        assert "No seed skill" in result.convergence_reason

    def test_no_traces_returns_empty(self):
        result = optimize_skill(_make_skill(), [], [], [])
        assert result.best_candidate is None
        assert "No execution traces" in result.convergence_reason

    def test_max_iterations(self):
        """Test that the loop runs up to max_iterations without converging."""
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            # Reflection returns lessons, mutation returns same skill (no improvement)
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["lesson"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_skill(
                seed_skill=_make_skill(),
                traces=[_make_trace(3)],
                gap_reports=[_make_gap_report(3, 1)],
                extractions=[_make_extraction(3)],
                max_iterations=3,
                rng_seed=42,
            )

            assert result.iterations == 3
            # At 3 iterations, convergence may trigger (plateau) or max may be reached
            assert result.convergence_reason in (
                "Converged at iteration 3 (fitness plateau)",
                "Reached max iterations (3)",
            )
            assert result.best_candidate is not None
            assert len(result.history) >= 4  # seed + 3 iterations

    def test_convergence_plateau(self):
        """Test that the loop stops when fitness plateaus."""
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["lesson"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_skill(
                seed_skill=_make_skill(),
                traces=[_make_trace(3)],
                gap_reports=[_make_gap_report(3, 0)],
                extractions=[_make_extraction(3)],
                max_iterations=20,
                convergence_threshold=0.01,
                rng_seed=42,
            )

            # Should converge before 20 iterations since mutation doesn't improve
            assert result.iterations < 20
            assert "Converged" in result.convergence_reason

    def test_token_usage_accumulated(self):
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["l"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=100, output_tokens=200, total_tokens=300,
            )
            result = optimize_skill(
                seed_skill=_make_skill(),
                traces=[_make_trace(3)],
                gap_reports=[_make_gap_report(3, 1)],
                extractions=[_make_extraction(3)],
                max_iterations=2,
                rng_seed=42,
            )

            assert result.token_usage["total_tokens"] > 0
            assert result.token_usage["input_tokens"] > 0
            assert result.token_usage["output_tokens"] > 0

    def test_population_does_not_exceed_max(self):
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["l"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_skill(
                seed_skill=_make_skill(),
                traces=[_make_trace(3)],
                gap_reports=[_make_gap_report(3, 1)],
                extractions=[_make_extraction(3)],
                max_iterations=10,
                population_size=3,
                rng_seed=42,
            )

            assert len(result.population) <= 3

    def test_pareto_front_populated(self):
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["l"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_skill(
                seed_skill=_make_skill(),
                traces=[_make_trace(3)],
                gap_reports=[_make_gap_report(3, 1)],
                extractions=[_make_extraction(3)],
                max_iterations=3,
                rng_seed=42,
            )

            assert len(result.pareto_front) >= 1
            assert all(c.pareto_rank == 0 for c in result.pareto_front)

    def test_history_records_iterations(self):
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["l"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_skill(
                seed_skill=_make_skill(),
                traces=[_make_trace(3)],
                gap_reports=[_make_gap_report(3, 1)],
                extractions=[_make_extraction(3)],
                max_iterations=3,
                rng_seed=42,
            )

            # History: seed (iteration 0) + 3 iterations
            assert len(result.history) == 4
            assert result.history[0]["event"] == "seed_evaluated"
            assert all("iteration" in h for h in result.history)

    def test_to_dict(self):
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["l"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            result = optimize_skill(
                seed_skill=_make_skill(),
                traces=[_make_trace(3)],
                gap_reports=[_make_gap_report(3, 1)],
                extractions=[_make_extraction(3)],
                max_iterations=2,
                rng_seed=42,
            )

            d = result.to_dict()
            assert "best_candidate" in d
            assert "population_size" in d
            assert "pareto_front" in d
            assert "iterations" in d
            assert "history" in d
            assert "token_usage" in d
            assert "convergence_reason" in d


# ---------------------------------------------------------------------------
# Integration tests — API endpoint
# ---------------------------------------------------------------------------

class TestOptimizeSkillAPI:
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

    def test_optimize_endpoint(self, client: TestClient):
        with patch("src.ai.prompt_evolver.invoke_llm") as mock_llm:
            mock_llm.return_value = MagicMock(
                content=json.dumps({"lessons": ["l"], "diagnoses": [], "proposed_mutations": {}}),
                input_tokens=10, output_tokens=20, total_tokens=30,
            )
            response = client.post("/api/v1/skills/optimize", json={
                "seed_skill": _make_skill(),
                "traces": [_make_trace(3)],
                "gap_reports": [_make_gap_report(3, 1)],
                "extractions": [_make_extraction(3)],
                "max_iterations": 2,
                "rng_seed": 42,
            })
            assert response.status_code == 200
            data = response.json()
            assert "best_candidate" in data
            assert "iterations" in data
            assert "history" in data
            assert "convergence_reason" in data

    def test_optimize_endpoint_empty_seed(self, client: TestClient):
        response = client.post("/api/v1/skills/optimize", json={
            "seed_skill": {},
            "traces": [_make_trace(3)],
            "gap_reports": [_make_gap_report(3, 1)],
            "extractions": [_make_extraction(3)],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["best_candidate"] is None
        assert "No seed skill" in data["convergence_reason"]
