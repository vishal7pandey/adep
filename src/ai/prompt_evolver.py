"""GEPA: Reflective Prompt Evolution for skills [BLK-071, SCRUM-78].

Implements a Genetic-Pareto prompt evolution loop that optimizes skill
playbooks by reflecting on execution traces. Unlike the simple linear
co-evolution in skill_composer.py, GEPA maintains a population of candidate
skills, uses Pareto-front selection for diversity, and accumulates textual
lessons across generations.

Algorithm:
1. Initialize population with the seed skill (+ heuristic variants)
2. Evaluate each candidate on sample data → scores + diagnostic feedback
3. Reflect via LLM on execution traces → natural-language lessons
4. Mutate the system prompt / probe order / failure actions using lessons
5. Accept if improved on minibatch, then evaluate on full Pareto set
6. Update Pareto front and repeat

Depends on:
- BLK-068 (Skill Composer) for skill structure
- BLK-070 (Surrogate Verifier) for diagnostic feedback

Uses Azure OpenAI (GPT-5.4) for reflection and mutation.
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Any

from src.providers.llm import invoke_llm

logger = logging.getLogger(__name__)

# Upper bound for `optimize_skill(max_iterations=...)`; same number as the API request model
# (`OptimizeSkillRequest`). Each iteration makes paid model calls, so a larger request is clamped.
MAX_GEPA_ITERATIONS = 50


# ---------------------------------------------------------------------------
# System prompts for reflection and mutation
# ---------------------------------------------------------------------------

_REFLECT_PROMPT = """You are an expert analyst for a document extraction agent's skill playbook.

You will receive:
1. The current skill definition (system prompt, tools, probe order, invariants, failure actions)
2. Execution traces from sample document runs
3. Gap reports showing which fields were satisfied vs missing
4. Extracted outputs with confidence scores
5. Accumulated lessons from previous iterations (if any)

Your task: Diagnose WHY the skill is underperforming and propose SPECIFIC, ACTIONABLE lessons that will guide the next mutation.

Focus on:
- **System prompt weaknesses**: Is the prompt too vague? Missing document-specific cues? Not guiding the agent to the right regions?
- **Probe order issues**: Is the agent wasting cycles on low-value regions first?
- **Tool selection**: Is OCR used where VLM would be better? Are redundant calls being made?
- **Failure action gaps**: When a field is missing, does the skill have a concrete recovery strategy?
- **Invariant gaps**: Are there math/logic checks that should be declared but aren't?
- **Confidence calibration**: Are thresholds too high (causing unnecessary re-reads) or too low (accepting bad values)?

Return your analysis as JSON:
{
  "lessons": [
    "Lesson 1: Specific, actionable insight...",
    "Lesson 2: ..."
  ],
  "diagnoses": [
    {"type": "system_prompt|probe_order|tool_selection|failure_action|invariant|confidence", "severity": "high|medium|low", "message": "...", "field": "..."}
  ],
  "proposed_mutations": {
    "system_prompt_hint": "Specific suggestion for improving the system prompt",
    "probe_order_hint": "Specific suggestion for adjusting probe order",
    "failure_action_hint": "Specific suggestion for new/changed failure actions",
    "invariant_hint": "Specific suggestion for new invariants"
  }
}

Return ONLY the JSON. Be specific and actionable — vague lessons are useless."""

_MUTATE_PROMPT = """You are an expert skill mutator for a document extraction agent.

You will receive:
1. The current skill definition (as JSON)
2. Accumulated lessons from reflection (natural language insights about what went wrong)
3. Proposed mutation hints

Your task: Produce an IMPROVED version of the skill JSON. Apply the lessons and hints to make targeted changes.

Rules:
- Keep the same JSON structure: name, description, system_prompt, tool_preferences, probe_order, invariants, failure_actions, known_failures, confidence_overrides
- Make TARGETED changes based on the lessons — don't rewrite everything
- The system_prompt should be specific and actionable (3-8 sentences)
- Include ALL gap types in failure_actions: missing, type_error, format_error, ungrounded, low_confidence, invariant_failed, semantic_fail
- Include 3-6 probe_order entries with rationales
- Include 1-4 invariants if the document has math/logic relationships
- Skill name MUST remain snake_case
- Return ONLY the JSON, no markdown or explanation"""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Candidate:
    """A candidate skill in the GEPA population.

    Attributes:
        skill: The skill dict.
        scores: Per-metric scores from evaluation (field_coverage, avg_confidence, token_efficiency, gap_severity).
        lessons: Accumulated textual lessons from all ancestors.
        parent_id: ID of the parent candidate (None for seed).
        candidate_id: Unique ID for this candidate.
        generation: Generation number (0 for seed).
        pareto_rank: Rank on Pareto front (0 = non-dominated, lower is better).
        trace_summary: Summary of execution traces from last evaluation.
    """

    skill: dict[str, Any]
    scores: dict[str, float] = field(default_factory=dict)
    lessons: list[str] = field(default_factory=list)
    parent_id: str | None = None
    candidate_id: str = ""
    generation: int = 0
    pareto_rank: int = 0
    trace_summary: str = ""

    def fitness(self) -> float:
        """Aggregate fitness score (higher is better)."""
        coverage = self.scores.get("field_coverage", 0.0)
        confidence = self.scores.get("avg_confidence", 0.0)
        efficiency = self.scores.get("token_efficiency", 0.0)
        gap_penalty = self.scores.get("gap_severity", 0.0)
        return coverage * 0.4 + confidence * 0.3 + efficiency * 0.2 - gap_penalty * 0.1

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "parent_id": self.parent_id,
            "generation": self.generation,
            "pareto_rank": self.pareto_rank,
            "scores": self.scores,
            "fitness": self.fitness(),
            "lessons": self.lessons,
            "skill": self.skill,
            "trace_summary": self.trace_summary,
        }


@dataclass
class EvaluationResult:
    """Result of evaluating a candidate on sample data.

    Attributes:
        scores: Per-metric scores.
        side_info: Actionable side information (ASI) — diagnostic feedback for the reflection model.
        trace_summary: Human-readable summary of execution traces.
    """

    scores: dict[str, float] = field(default_factory=dict)
    side_info: str = ""
    trace_summary: str = ""


@dataclass
class GEPAResult:
    """Result of the GEPA optimization loop.

    Attributes:
        best_candidate: The best candidate found.
        population: Final population of candidates.
        pareto_front: Candidates on the Pareto front.
        iterations: Number of iterations completed.
        history: Per-iteration snapshots.
        token_usage: Total token usage across all LLM calls.
        convergence_reason: Why the loop terminated.
    """

    best_candidate: Candidate | None = None
    population: list[Candidate] = field(default_factory=list)
    pareto_front: list[Candidate] = field(default_factory=list)
    iterations: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    token_usage: dict[str, int] = field(
        default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    )
    convergence_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_candidate": self.best_candidate.to_dict() if self.best_candidate else None,
            "population_size": len(self.population),
            "pareto_front_size": len(self.pareto_front),
            "iterations": self.iterations,
            "history": self.history,
            "token_usage": self.token_usage,
            "convergence_reason": self.convergence_reason,
            "pareto_front": [c.to_dict() for c in self.pareto_front],
        }


# ---------------------------------------------------------------------------
# Evaluation — computes scores from execution data
# ---------------------------------------------------------------------------


def _evaluate_candidate(
    skill: dict[str, Any],
    traces: list[list[Any]],
    gap_reports: list[Any],
    extractions: list[dict[str, Any]],
    token_usages: list[dict[str, int]] | None = None,
) -> EvaluationResult:
    """Evaluate a candidate skill on sample data and compute scores [BLK-071].

    Args:
        skill: The skill dict.
        traces: List of execution traces (one per sample).
        gap_reports: List of gap reports (one per sample).
        extractions: List of extraction dicts (one per sample).
        token_usages: Optional list of token usage dicts per sample.

    Returns:
        EvaluationResult with scores and diagnostic side info.
    """
    total_fields = 0
    satisfied_fields = 0
    total_confidence = 0.0
    confidence_count = 0
    total_gaps = 0
    gap_severity_sum = 0.0
    total_tokens = 0
    trace_summaries: list[str] = []

    _severity_weights = {
        "missing": 1.0,
        "invariant_failed": 0.9,
        "type_error": 0.7,
        "format_error": 0.6,
        "semantic_fail": 0.8,
        "low_confidence": 0.4,
        "ungrounded": 0.5,
    }

    for i, (trace, gap_report, extraction) in enumerate(zip(traces, gap_reports, extractions)):
        # Trace summary
        trace_len = len(trace or [])
        trace_summaries.append(f"Sample {i + 1}: {trace_len} steps")

        # Gap report metrics
        gaps = _value_from(gap_report, "gaps", []) if gap_report else []
        satisfied = _value_from(gap_report, "satisfied", []) if gap_report else []
        total_fields += (
            _value_from(gap_report, "total_fields", len(satisfied) + len(gaps))
            if gap_report
            else len(extraction)
        )
        satisfied_fields += len(satisfied)
        total_gaps += len(gaps)

        for gap in gaps:
            gap_type = str(_value_from(gap, "gap_type", "other"))
            gap_severity_sum += _severity_weights.get(gap_type, 0.5)

        # Confidence metrics from extraction
        for name, value in (extraction or {}).items():
            conf = _value_from(value, "confidence", None)
            if conf is not None:
                try:
                    total_confidence += float(conf)
                    confidence_count += 1
                except (TypeError, ValueError):
                    pass

        # Token usage
        if token_usages and i < len(token_usages):
            total_tokens += token_usages[i].get("total_tokens", 0)

    # Compute aggregate scores
    field_coverage = satisfied_fields / max(total_fields, 1)
    avg_confidence = total_confidence / max(confidence_count, 1)
    token_efficiency = satisfied_fields / max(total_tokens, 1) if total_tokens > 0 else 0.0
    gap_severity = gap_severity_sum / max(total_gaps, 1) if total_gaps > 0 else 0.0

    scores = {
        "field_coverage": round(field_coverage, 4),
        "avg_confidence": round(avg_confidence, 4),
        "token_efficiency": round(token_efficiency, 6),
        "gap_severity": round(gap_severity, 4),
    }

    # Build side info (ASI) for reflection
    side_info_parts = [
        f"Field coverage: {satisfied_fields}/{total_fields} ({field_coverage:.1%})",
        f"Average confidence: {avg_confidence:.3f}",
        f"Total gaps: {total_gaps} (severity: {gap_severity:.3f})",
        f"Token usage: {total_tokens}",
        f"Traces: {'; '.join(trace_summaries)}",
    ]

    # Add gap details
    for i, gap_report in enumerate(gap_reports):
        gaps = _value_from(gap_report, "gaps", []) if gap_report else []
        for gap in gaps[:5]:  # Top 5 gaps per sample
            field_name = _value_from(gap, "field", "unknown")
            gap_type = _value_from(gap, "gap_type", "other")
            detail = _value_from(gap, "detail", "")
            side_info_parts.append(f"  Sample {i + 1} gap: {field_name} ({gap_type}) — {detail}")

    return EvaluationResult(
        scores=scores,
        side_info="\n".join(side_info_parts),
        trace_summary="; ".join(trace_summaries),
    )


# ---------------------------------------------------------------------------
# Pareto front management
# ---------------------------------------------------------------------------


def _dominates(a: Candidate, b: Candidate) -> bool:
    """Check if candidate a dominates candidate b (Pareto dominance).

    a dominates b if a is at least as good as b on all metrics AND strictly better on at least one.
    Higher is better for coverage, confidence, efficiency. Lower is better for gap_severity.
    """
    a_scores = a.scores
    b_scores = b.scores

    metrics_higher_better = ["field_coverage", "avg_confidence", "token_efficiency"]
    metrics_lower_better = ["gap_severity"]

    at_least_as_good = True
    strictly_better = False

    for m in metrics_higher_better:
        a_val = a_scores.get(m, 0.0)
        b_val = b_scores.get(m, 0.0)
        if a_val < b_val:
            at_least_as_good = False
            break
        if a_val > b_val:
            strictly_better = True

    if at_least_as_good:
        for m in metrics_lower_better:
            a_val = a_scores.get(m, float("inf"))
            b_val = b_scores.get(m, float("inf"))
            if a_val > b_val:
                at_least_as_good = False
                break
            if a_val < b_val:
                strictly_better = True

    return at_least_as_good and strictly_better


def _compute_pareto_ranks(candidates: list[Candidate]) -> None:
    """Assign Pareto ranks to all candidates (0 = best front, 1 = second, etc.)."""
    remaining = list(candidates)
    rank = 0

    while remaining:
        front = []
        for c in remaining:
            dominated = False
            for other in remaining:
                if other is c:
                    continue
                if _dominates(other, c):
                    dominated = True
                    break
            if not dominated:
                front.append(c)

        for c in front:
            c.pareto_rank = rank
            remaining.remove(c)

        rank += 1

    # Any remaining (shouldn't happen, but safety)
    for c in remaining:
        c.pareto_rank = rank


def _select_from_pareto(candidates: list[Candidate], rng: random.Random | None = None) -> Candidate:
    """Select a candidate from the Pareto front stochastically.

    Prefers candidates on the first Pareto front, with frequency-based sampling.
    """
    if not candidates:
        raise ValueError("No candidates to select from")

    rng = rng or random.Random()

    # Group by Pareto rank
    fronts: dict[int, list[Candidate]] = {}
    for c in candidates:
        fronts.setdefault(c.pareto_rank, []).append(c)

    # Sort fronts by rank
    sorted_fronts = sorted(fronts.keys())

    # Sample from the best front with probability proportional to fitness
    best_front = fronts[sorted_fronts[0]]
    weights = [max(c.fitness(), 0.01) for c in best_front]
    total_weight = sum(weights)

    if total_weight <= 0:
        return rng.choice(best_front)

    r = rng.random() * total_weight
    cumulative = 0.0
    for c, w in zip(best_front, weights):
        cumulative += w
        if r <= cumulative:
            return c

    return best_front[-1]


# ---------------------------------------------------------------------------
# Reflection — LLM reads traces and produces lessons
# ---------------------------------------------------------------------------


def _reflect(
    candidate: Candidate,
    eval_result: EvaluationResult,
) -> dict[str, Any]:
    """Use LLM to reflect on execution traces and produce lessons [BLK-071].

    Returns:
        Dict with 'lessons', 'diagnoses', and 'proposed_mutations'.
    """
    skill_json = json.dumps(candidate.skill, default=str, indent=2)
    lessons_str = (
        "\n".join(f"- {l}" for l in candidate.lessons) if candidate.lessons else "No prior lessons."
    )

    user_prompt = (
        f"## Current Skill Definition\n{skill_json}\n\n"
        f"## Evaluation Results\n{eval_result.side_info}\n\n"
        f"## Accumulated Lessons\n{lessons_str}\n\n"
        f"Analyze the skill's performance and propose actionable lessons for improvement."
    )

    response = invoke_llm(_REFLECT_PROMPT, user_prompt, max_tokens=2000)

    if not response.content:
        return {
            "lessons": [],
            "diagnoses": [],
            "proposed_mutations": {},
            "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        }

    content = response.content.strip()
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found")
        result = json.loads(content[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Reflection LLM returned invalid JSON: %s", e)
        return {
            "lessons": [],
            "diagnoses": [],
            "proposed_mutations": {},
            "_token_usage": {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
            },
        }

    result.setdefault("lessons", [])
    result.setdefault("diagnoses", [])
    result.setdefault("proposed_mutations", {})
    result["_token_usage"] = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
    }

    return result


# ---------------------------------------------------------------------------
# Mutation — LLM produces an improved skill variant
# ---------------------------------------------------------------------------


def _mutate(
    candidate: Candidate,
    reflection: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    """Use LLM to mutate the skill based on reflection lessons [BLK-071].

    Returns:
        Tuple of (new_skill_dict, token_usage).
    """
    skill_json = json.dumps(candidate.skill, default=str, indent=2)
    lessons_str = "\n".join(f"- {l}" for l in reflection.get("lessons", []))
    mutations = reflection.get("proposed_mutations", {})
    mutations_str = json.dumps(mutations, indent=2)

    user_prompt = (
        f"## Current Skill\n{skill_json}\n\n"
        f"## Lessons from Reflection\n{lessons_str}\n\n"
        f"## Proposed Mutation Hints\n{mutations_str}\n\n"
        f"Produce an improved version of the skill JSON."
    )

    response = invoke_llm(_MUTATE_PROMPT, user_prompt, max_tokens=3000)

    token_usage = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
    }

    if not response.content:
        # No LLM — return the original skill unchanged
        return candidate.skill, token_usage

    content = response.content.strip()
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found")
        new_skill = json.loads(content[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Mutation LLM returned invalid JSON: %s — keeping original", e)
        return candidate.skill, token_usage

    # Ensure required keys exist (inherit from parent if missing)
    for key in (
        "name",
        "system_prompt",
        "tool_preferences",
        "probe_order",
        "invariants",
        "failure_actions",
        "known_failures",
        "confidence_overrides",
    ):
        if key not in new_skill:
            new_skill[key] = candidate.skill.get(key)

    return new_skill, token_usage


# ---------------------------------------------------------------------------
# Merge — combine complementary candidates
# ---------------------------------------------------------------------------

_MERGE_PROMPT = """You are an expert skill merger for a document extraction agent.

You will receive two skill definitions that excel on different aspects. Your task is to produce a MERGED skill that combines the strengths of both.

Rules:
- Keep the same JSON structure
- Take the best system prompt elements from both
- Merge tool_preferences (union of both)
- Merge probe_order (take the better ordering)
- Merge invariants (union, dedup by name)
- Merge failure_actions (union)
- Merge confidence_overrides (take the stricter threshold for each field)
- Skill name MUST be snake_case
- Return ONLY the JSON, no markdown or explanation"""


def _merge_candidates(a: Candidate, b: Candidate) -> tuple[dict[str, Any], dict[str, int]]:
    """Merge two complementary candidates using LLM [BLK-071].

    Returns:
        Tuple of (merged_skill_dict, token_usage).
    """
    user_prompt = (
        f"## Skill A (excels at: {a.scores})\n{json.dumps(a.skill, default=str, indent=2)}\n\n"
        f"## Skill B (excels at: {b.scores})\n{json.dumps(b.skill, default=str, indent=2)}\n\n"
        f"Produce a merged skill that combines the strengths of both."
    )

    response = invoke_llm(_MERGE_PROMPT, user_prompt, max_tokens=3000)

    token_usage = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
    }

    if not response.content:
        # Fallback: simple heuristic merge
        return _heuristic_merge(a.skill, b.skill), token_usage

    content = response.content.strip()
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found")
        merged = json.loads(content[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Merge LLM returned invalid JSON: %s — using heuristic merge", e)
        return _heuristic_merge(a.skill, b.skill), token_usage

    return merged, token_usage


def _heuristic_merge(skill_a: dict[str, Any], skill_b: dict[str, Any]) -> dict[str, Any]:
    """Heuristic merge when LLM is unavailable."""
    merged = dict(skill_a)

    # Union tool_preferences
    merged["tool_preferences"] = {
        **skill_b.get("tool_preferences", {}),
        **skill_a.get("tool_preferences", {}),
    }

    # Merge probe_order (A first, then B entries not in A)
    a_regions = {p.get("region_type") for p in merged.get("probe_order", [])}
    for p in skill_b.get("probe_order", []):
        if p.get("region_type") not in a_regions:
            merged.setdefault("probe_order", []).append(p)

    # Union invariants (dedup by name)
    inv_names = {i.get("name") for i in merged.get("invariants", [])}
    for inv in skill_b.get("invariants", []):
        if inv.get("name") not in inv_names:
            merged.setdefault("invariants", []).append(inv)

    # Union failure_actions
    merged["failure_actions"] = {
        **skill_a.get("failure_actions", {}),
        **skill_b.get("failure_actions", {}),
    }

    # Merge confidence_overrides (take stricter threshold)
    for field_name, threshold in skill_b.get("confidence_overrides", {}).items():
        existing = merged.get("confidence_overrides", {}).get(field_name)
        if existing is None:
            merged.setdefault("confidence_overrides", {})[field_name] = threshold
        else:
            merged["confidence_overrides"][field_name] = max(existing, threshold)

    # Combine known_failures
    merged["known_failures"] = (
        f"{skill_a.get('known_failures', '')}\n{skill_b.get('known_failures', '')}"
    ).strip()

    # Longer system prompt (heuristic: take the longer one as it's more detailed)
    prompt_a = skill_a.get("system_prompt", "")
    prompt_b = skill_b.get("system_prompt", "")
    merged["system_prompt"] = prompt_a if len(prompt_a) >= len(prompt_b) else prompt_b

    return merged


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _value_from(obj: Any, key: str, default: Any = None) -> Any:
    """Read a value from either a dict key or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


# ---------------------------------------------------------------------------
# Main optimization loop
# ---------------------------------------------------------------------------


def optimize_skill(
    seed_skill: dict[str, Any],
    traces: list[list[Any]],
    gap_reports: list[Any],
    extractions: list[dict[str, Any]],
    *,
    max_iterations: int = 10,
    population_size: int = 6,
    merge_probability: float = 0.2,
    convergence_threshold: float = 0.01,
    token_usages: list[dict[str, int]] | None = None,
    rng_seed: int | None = None,
) -> GEPAResult:
    """Run the GEPA reflective prompt evolution loop on a skill [BLK-071].

    Args:
        seed_skill: The initial skill dict to optimize.
        traces: List of execution traces (one per sample document).
        gap_reports: List of gap reports (one per sample).
        extractions: List of extraction dicts (one per sample).
        max_iterations: Maximum GEPA iterations (clamped to MAX_GEPA_ITERATIONS, 50).
        population_size: Maximum number of candidates to maintain.
        merge_probability: Probability of attempting a merge instead of mutation.
        convergence_threshold: If fitness improvement is below this for 3 consecutive iterations, stop.
        token_usages: Optional per-sample token usage for efficiency scoring.
        rng_seed: Optional random seed for reproducibility.

    Returns:
        GEPAResult with the best candidate, full population, and history.
    """
    rng = random.Random(rng_seed)
    result = GEPAResult()

    if not seed_skill:
        result.convergence_reason = "No seed skill provided"
        return result

    if not traces:
        result.convergence_reason = "No execution traces provided"
        return result

    # Step 1: Initialize population with seed skill
    seed_candidate = Candidate(
        skill=seed_skill,
        candidate_id="seed",
        generation=0,
    )

    # Evaluate seed
    eval_result = _evaluate_candidate(seed_skill, traces, gap_reports, extractions, token_usages)
    seed_candidate.scores = eval_result.scores
    seed_candidate.trace_summary = eval_result.trace_summary

    population: list[Candidate] = [seed_candidate]
    _compute_pareto_ranks(population)

    result.history.append(
        {
            "iteration": 0,
            "event": "seed_evaluated",
            "scores": seed_candidate.scores,
            "fitness": seed_candidate.fitness(),
        }
    )

    # Track convergence
    best_fitness_history: list[float] = [seed_candidate.fitness()]
    candidate_counter = 0

    if max_iterations > MAX_GEPA_ITERATIONS:
        logger.warning(
            "GEPA: max_iterations=%d exceeds the limit, clamped to %d",
            max_iterations,
            MAX_GEPA_ITERATIONS,
        )
    max_iterations = min(max_iterations, MAX_GEPA_ITERATIONS)

    for iteration in range(1, max_iterations + 1):
        logger.info(
            "GEPA iteration %d/%d — population=%d", iteration, max_iterations, len(population)
        )

        # Step 2: Select a parent from the Pareto front
        parent = _select_from_pareto(population, rng)

        # Step 3: Reflect on the parent's performance
        reflection = _reflect(parent, eval_result)
        tu = reflection.pop("_token_usage", {})
        result.token_usage["input_tokens"] += tu.get("input_tokens", 0)
        result.token_usage["output_tokens"] += tu.get("output_tokens", 0)
        result.token_usage["total_tokens"] += tu.get("total_tokens", 0)

        # Accumulate lessons
        new_lessons = reflection.get("lessons", [])
        accumulated_lessons = parent.lessons + new_lessons

        # Step 4: Mutate or merge
        do_merge = rng.random() < merge_probability and len(population) >= 2

        if do_merge:
            # Select a second parent from the Pareto front
            other_parent = _select_from_pareto([c for c in population if c is not parent], rng)
            if other_parent:
                new_skill, tu = _merge_candidates(parent, other_parent)
                event = "merge"
            else:
                new_skill, tu = _mutate(parent, reflection)
                event = "mutate"
        else:
            new_skill, tu = _mutate(parent, reflection)
            event = "mutate"

        result.token_usage["input_tokens"] += tu.get("input_tokens", 0)
        result.token_usage["output_tokens"] += tu.get("output_tokens", 0)
        result.token_usage["total_tokens"] += tu.get("total_tokens", 0)

        candidate_counter += 1
        new_candidate = Candidate(
            skill=new_skill,
            lessons=accumulated_lessons,
            parent_id=parent.candidate_id,
            candidate_id=f"gen{iteration}_{candidate_counter}",
            generation=iteration,
        )

        # Step 5: Evaluate the new candidate
        eval_result = _evaluate_candidate(new_skill, traces, gap_reports, extractions, token_usages)
        new_candidate.scores = eval_result.scores
        new_candidate.trace_summary = eval_result.trace_summary

        # Step 6: Accept if improved (on minibatch — here we use all samples as the minibatch)
        parent_fitness = parent.fitness()
        new_fitness = new_candidate.fitness()

        if new_fitness > parent_fitness:
            population.append(new_candidate)
            logger.info(
                "GEPA: Accepted new candidate (fitness=%.4f > parent=%.4f)",
                new_fitness,
                parent_fitness,
            )
        else:
            logger.info(
                "GEPA: Rejected new candidate (fitness=%.4f <= parent=%.4f)",
                new_fitness,
                parent_fitness,
            )
            # Still keep it in the population with some probability (for diversity)
            if rng.random() < 0.3 and len(population) < population_size:
                population.append(new_candidate)

        # Step 7: Prune population to population_size (keep best by fitness)
        if len(population) > population_size:
            population.sort(key=lambda c: c.fitness(), reverse=True)
            population = population[:population_size]

        # Step 8: Recompute Pareto ranks
        _compute_pareto_ranks(population)

        # Record history
        best = max(population, key=lambda c: c.fitness())
        best_fitness_history.append(best.fitness())
        result.history.append(
            {
                "iteration": iteration,
                "event": event,
                "parent": parent.candidate_id,
                "new_candidate": new_candidate.candidate_id,
                "new_scores": new_candidate.scores,
                "new_fitness": new_fitness,
                "accepted": new_fitness > parent_fitness,
                "best_fitness": best.fitness(),
                "population_size": len(population),
            }
        )

        # Step 9: Check convergence
        if len(best_fitness_history) >= 4:
            recent = best_fitness_history[-3:]
            if max(recent) - min(recent) < convergence_threshold:
                result.convergence_reason = f"Converged at iteration {iteration} (fitness plateau)"
                result.iterations = iteration
                break
    else:
        result.convergence_reason = f"Reached max iterations ({max_iterations})"
        result.iterations = max_iterations

    # Finalize results
    _compute_pareto_ranks(population)
    result.population = population
    result.pareto_front = [c for c in population if c.pareto_rank == 0]
    result.best_candidate = max(population, key=lambda c: c.fitness()) if population else None

    return result
