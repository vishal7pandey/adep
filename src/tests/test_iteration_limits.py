"""Regression tests for the SonarCloud S6680 findings ADE-60, ADE-61 and ADE-62.

The three optimisation loops take ``max_iterations`` from the request body and used it as the
loop bound without a limit of their own (the API model caps it, a direct caller does not):

- ADE-60: ``optimize_skill`` (GEPA), src/ai/prompt_evolver.py
- ADE-61: ``optimize_workflow`` (MCTS), src/ai/workflow_optimizer.py
- ADE-62: ``co_evolve_skill``, src/ai/skill_composer.py

Each loop now clamps ``max_iterations`` to a documented module limit (the same number the API
request model allows). The tests hard-code those limits on purpose: a runaway loop is stopped
by a ``BaseException`` after a few extra rounds so a failing test never hangs.
"""

from __future__ import annotations

import importlib
import json
from unittest.mock import MagicMock, patch

import pytest

from src.ai import prompt_evolver, skill_composer, workflow_optimizer
from src.api.routes import skills as skills_routes

GEPA_LIMIT = 50
MCTS_LIMIT = 100
CO_EVOLVE_LIMIT = 10
HUGE = 10**9


class _Runaway(BaseException):
    """Raised by the counting stubs when a loop runs past its documented limit."""


def _counting(real, calls: list[int], cap: int):
    def wrapper(*args, **kwargs):
        calls.append(1)
        if len(calls) > cap:
            raise _Runaway(f"loop ran more than {cap} rounds")
        return real(*args, **kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# ADE-60: GEPA
# ---------------------------------------------------------------------------


def _gepa_inputs():
    skill = {
        "name": "t",
        "description": "d",
        "system_prompt": "Extract data.",
        "tool_preferences": {"text": "ocr"},
        "probe_order": [{"region_type": "header", "rationale": "Top"}],
        "invariants": [],
        "failure_actions": {"missing": "Re-probe"},
        "known_failures": "",
        "confidence_overrides": {"total": 0.85},
    }
    trace = [
        {"step": i + 1, "tool_name": "ocr", "thought": "t", "tool_args": {}, "result": "ok"}
        for i in range(3)
    ]
    gaps = {
        "total_fields": 4,
        "satisfied": [{"field": f"f{i}"} for i in range(3)],
        "gaps": [{"field": "g", "gap_type": "missing", "detail": "x"}],
    }
    extraction = {f"f{i}": {"value": "v", "confidence": 0.9} for i in range(3)}
    return skill, [trace], [gaps], [extraction]


def _run_gepa(max_iterations: int) -> tuple[list[int], prompt_evolver.GEPAResult]:
    skill, traces, gaps, extractions = _gepa_inputs()
    calls: list[int] = []
    llm_reply = MagicMock(
        content=json.dumps({"lessons": ["l"], "diagnoses": [], "proposed_mutations": {}}),
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
    )
    with (
        patch("src.ai.prompt_evolver.invoke_llm", return_value=llm_reply),
        patch(
            "src.ai.prompt_evolver._reflect",
            _counting(prompt_evolver._reflect, calls, GEPA_LIMIT + 3),
        ),
    ):
        result = prompt_evolver.optimize_skill(
            skill,
            traces,
            gaps,
            extractions,
            max_iterations=max_iterations,
            convergence_threshold=-1.0,  # never "converged": only the bound stops the loop
            rng_seed=1,
        )
    return calls, result


class TestGepaIterationLimit:
    @pytest.mark.parametrize("requested", [GEPA_LIMIT, GEPA_LIMIT + 1, HUGE])
    def test_loop_never_runs_past_the_limit(self, requested):
        calls, result = _run_gepa(requested)
        assert len(calls) == GEPA_LIMIT
        assert result.iterations == GEPA_LIMIT
        assert result.convergence_reason == f"Reached max iterations ({GEPA_LIMIT})"

    def test_a_value_below_the_limit_is_untouched(self):
        calls, result = _run_gepa(4)
        assert len(calls) == 4
        assert result.convergence_reason == "Reached max iterations (4)"


# ---------------------------------------------------------------------------
# ADE-61: MCTS
# ---------------------------------------------------------------------------


def _run_mcts(max_iterations: int) -> tuple[list[int], workflow_optimizer.MCTSResult]:
    calls: list[int] = []
    llm_reply = MagicMock(
        content=json.dumps(
            {"action": "add_node", "description": "Add review", "details": {"node_name": "review"}}
        ),
        input_tokens=1,
        output_tokens=1,
        total_tokens=2,
    )
    with (
        patch("src.ai.workflow_optimizer.invoke_llm", return_value=llm_reply),
        patch(
            "src.ai.workflow_optimizer._select",
            _counting(workflow_optimizer._select, calls, MCTS_LIMIT + 3),
        ),
    ):
        result = workflow_optimizer.optimize_workflow(
            max_iterations=max_iterations,
            convergence_threshold=-1.0,  # never "converged": only the bound stops the loop
            rng_seed=1,
        )
    return calls, result


class TestMctsIterationLimit:
    @pytest.mark.parametrize("requested", [MCTS_LIMIT, MCTS_LIMIT + 1, HUGE])
    def test_loop_never_runs_past_the_limit(self, requested):
        calls, result = _run_mcts(requested)
        assert len(calls) == MCTS_LIMIT
        assert result.iterations == MCTS_LIMIT
        assert result.convergence_reason == f"Reached max iterations ({MCTS_LIMIT})"

    def test_a_value_below_the_limit_is_untouched(self):
        calls, result = _run_mcts(4)
        assert len(calls) == 4
        assert result.convergence_reason == "Reached max iterations (4)"


# ---------------------------------------------------------------------------
# ADE-62: skill co-evolution
# ---------------------------------------------------------------------------

_ALWAYS_PATCH = {
    "diagnoses": [{"type": "other", "severity": "low", "message": "Issue"}],
    "proposed_tests": [],
    "skill_patch": {
        "invariants_to_add": [{"name": "persistent_check", "fields": [], "description": ""}],
        "failure_actions_to_add": {},
        "probe_order_adjustments": [],
        "system_prompt_suggestions": "Keep improving.",
    },
    "_token_usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
}


def _run_co_evolve(max_iterations: int) -> tuple[list[int], skill_composer.CoEvolutionResult]:
    calls: list[int] = []
    verify = _counting(lambda *a, **k: _ALWAYS_PATCH, calls, CO_EVOLVE_LIMIT + 3)
    with (
        patch(
            "src.ai.skill_composer.invoke_llm",
            return_value=MagicMock(content="", input_tokens=0, output_tokens=0, total_tokens=0),
        ),
        patch("src.ai.surrogate_verifier.verify_skill", verify),
    ):
        result = skill_composer.co_evolve_skill(
            description="Extract data",
            trace=[],
            gap_report={},
            extraction={},
            max_iterations=max_iterations,
        )
    return calls, result


class TestCoEvolveIterationLimit:
    @pytest.mark.parametrize("requested", [CO_EVOLVE_LIMIT, CO_EVOLVE_LIMIT + 1, HUGE])
    def test_loop_never_runs_past_the_limit(self, requested):
        calls, result = _run_co_evolve(requested)
        assert len(calls) == CO_EVOLVE_LIMIT
        assert result.iterations == CO_EVOLVE_LIMIT
        assert len(result.verifier_reports) == CO_EVOLVE_LIMIT

    def test_a_value_below_the_limit_is_untouched(self):
        calls, result = _run_co_evolve(2)
        assert len(calls) == 2
        assert result.iterations == 2


# ---------------------------------------------------------------------------
# The module limits and the API request limits are one number
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("model_name", "module_name", "constant"),
    [
        ("OptimizeSkillRequest", "src.ai.prompt_evolver", "MAX_GEPA_ITERATIONS"),
        ("OptimizeWorkflowRequest", "src.ai.workflow_optimizer", "MAX_MCTS_ITERATIONS"),
        ("CoEvolveSkillRequest", "src.ai.skill_composer", "MAX_CO_EVOLUTION_ITERATIONS"),
    ],
)
def test_module_limit_matches_the_api_request_limit(model_name, module_name, constant):
    model = getattr(skills_routes, model_name)
    api_limit = next(
        m.le for m in model.model_fields["max_iterations"].metadata if hasattr(m, "le")
    )
    assert getattr(importlib.import_module(module_name), constant) == api_limit
