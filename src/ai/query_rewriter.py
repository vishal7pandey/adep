"""Agentic Query Rewriting — DocETL-style pipeline optimization [BLK-073, SCRUM-80].

When an extraction pipeline consistently fails on a class of documents, this
module automatically rewrites the skill into smaller sub-tasks with validation.

The system monitors run outcomes over a sliding window. When a definition's
failure rate exceeds a threshold, the query rewriter:

1. Analyzes the gap report patterns (which fields fail, which gap types dominate)
2. Asks the LLM to decompose the failing skill into sub-skills
3. Each sub-skill handles a subset of fields with focused probe order
4. Generates validation criteria for each sub-skill
5. Returns a rewritten skill definition for review or auto-save

Inspired by DocETL (ICLR 2025) — "Agentic Query Rewriting for Data Processing
Pipelines" — which shows that LLM-based pipeline decomposition can improve
extraction accuracy by 15-40% on complex documents.

Depends on:
- BLK-008 (Agent Runtime / graph.py) — for run execution
- BLK-072 (Workflow Optimizer) — for topology search integration
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from src.providers.llm import invoke_llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_FAILURE_THRESHOLD = 0.4  # Trigger rewriting when >40% of runs fail
DEFAULT_MIN_SAMPLE_SIZE = 5  # Need at least 5 runs to trigger
DEFAULT_SLIDING_WINDOW = 20  # Look at last 20 runs


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class FailurePattern:
    """A detected failure pattern for a definition.

    Attributes:
        definition_id: The agent definition that is failing.
        failure_rate: Fraction of runs that failed (0.0-1.0).
        total_runs: Total runs in the sliding window.
        failed_runs: Number of failed runs.
        gap_type_counts: Most common gap types across failed runs.
        failing_fields: Most commonly failing fields.
        avg_cycles_per_run: Average cycles consumed before failure.
    """

    definition_id: str
    failure_rate: float
    total_runs: int
    failed_runs: int
    gap_type_counts: dict[str, int] = field(default_factory=dict)
    failing_fields: dict[str, int] = field(default_factory=dict)
    avg_cycles_per_run: float = 0.0


@dataclass
class SubSkill:
    """A decomposed sub-skill produced by query rewriting.

    Attributes:
        name: Sub-skill name (snake_case).
        description: What this sub-skill extracts.
        system_prompt: Focused system prompt for this sub-skill.
        field_subset: Fields this sub-skill is responsible for.
        probe_order: Ordered probe steps for this sub-skill.
        validation_criteria: Criteria to validate sub-skill output.
    """

    name: str
    description: str
    system_prompt: str
    field_subset: list[str]
    probe_order: list[dict[str, str]] = field(default_factory=list)
    validation_criteria: list[str] = field(default_factory=list)


@dataclass
class RewriteResult:
    """Result of a query rewriting operation.

    Attributes:
        original_definition_id: The definition that was rewritten.
        failure_pattern: The detected failure pattern that triggered the rewrite.
        sub_skills: Decomposed sub-skills.
        rewritten_skill: The complete rewritten skill dict (for review/save).
        rationale: Explanation of why the rewrite was proposed.
        estimated_improvement: Estimated accuracy improvement (0.0-1.0).
    """

    original_definition_id: str
    failure_pattern: FailurePattern
    sub_skills: list[SubSkill] = field(default_factory=list)
    rewritten_skill: dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    estimated_improvement: float = 0.0


# ---------------------------------------------------------------------------
# Failure analysis
# ---------------------------------------------------------------------------


def analyze_failures(
    definition_id: str,
    runs: list[dict[str, Any]],
    min_sample: int = DEFAULT_MIN_SAMPLE_SIZE,
    failure_threshold: float = DEFAULT_FAILURE_THRESHOLD,
) -> FailurePattern | None:
    """Analyze run history for a definition to detect failure patterns.

    Args:
        definition_id: The agent definition ID to analyze.
        runs: List of run dicts (from the store) for this definition.
        min_sample: Minimum number of runs required to trigger analysis.
        failure_threshold: Failure rate above which rewriting is recommended.

    Returns:
        FailurePattern if rewriting should be triggered, None otherwise.
    """
    if len(runs) < min_sample:
        logger.debug(
            "Skipping failure analysis for %s: only %d runs (need %d)",
            definition_id,
            len(runs),
            min_sample,
        )
        return None

    failed = [r for r in runs if r.get("status") in ("failed", "max_iterations_reached")]
    failure_rate = len(failed) / len(runs)

    if failure_rate < failure_threshold:
        logger.debug(
            "Failure rate %.2f for %s below threshold %.2f",
            failure_rate,
            definition_id,
            failure_threshold,
        )
        return None

    # Aggregate gap types and failing fields
    gap_counter: Counter[str] = Counter()
    field_counter: Counter[str] = Counter()
    total_cycles = 0

    for run in failed:
        # Extract gap info from run trace
        trace = run.get("trace", [])
        for entry in trace:
            gaps = entry.get("gaps", [])
            for gap in gaps:
                gap_type = gap.get("gap_type", "unknown")
                gap_counter[gap_type] += 1
                field_name = gap.get("field", "")
                if field_name:
                    field_counter[field_name] += 1

        total_cycles += run.get("total_cycles", 0)

    avg_cycles = total_cycles / len(failed) if failed else 0

    pattern = FailurePattern(
        definition_id=definition_id,
        failure_rate=failure_rate,
        total_runs=len(runs),
        failed_runs=len(failed),
        gap_type_counts=dict(gap_counter.most_common(10)),
        failing_fields=dict(field_counter.most_common(10)),
        avg_cycles_per_run=avg_cycles,
    )

    logger.info(
        "Failure pattern detected for %s: %.1f%% failure rate (%d/%d runs), "
        "top gaps: %s, top failing fields: %s",
        definition_id,
        failure_rate * 100,
        len(failed),
        len(runs),
        list(gap_counter.most_common(3)),
        list(field_counter.most_common(3)),
    )

    return pattern


# ---------------------------------------------------------------------------
# Skill decomposition (LLM-powered)
# ---------------------------------------------------------------------------

_DECOMPOSE_SYSTEM_PROMPT = """You are an AI assistant that decomposes failing document extraction skills into smaller sub-skills.

Given a failing skill definition and a failure analysis, produce a set of focused sub-skills that each handle a subset of fields. The goal is to reduce cognitive load on the agent and improve extraction accuracy.

For each sub-skill, provide:
1. name: snake_case identifier
2. description: What this sub-skill extracts
3. system_prompt: Focused instructions for this subset of fields
4. field_subset: List of field names this sub-skill handles
5. probe_order: Ordered list of {region_type, rationale} entries
6. validation_criteria: List of validation rules for this sub-skill's output

Guidelines:
- Split fields by visual proximity (fields in the same document region go together)
- Split fields by extraction complexity (simple OCR fields vs complex VLM fields)
- Each sub-skill should have 2-6 fields
- Include validation criteria that check for the specific failure patterns observed
- The union of all sub-skills' field_subset should cover all original fields

Return a JSON object:
{
  "rationale": "Why this decomposition was chosen",
  "estimated_improvement": 0.15,
  "sub_skills": [
    {
      "name": "extract_header_fields",
      "description": "Extract invoice header fields",
      "system_prompt": "You are extracting header fields from an invoice...",
      "field_subset": ["invoice_number", "invoice_date", "vendor_name"],
      "probe_order": [{"region_type": "header", "rationale": "Header contains metadata"}],
      "validation_criteria": ["invoice_number must be non-empty", "invoice_date must be ISO format"]
    }
  ]
}

Return ONLY the JSON, no markdown or explanation."""


def decompose_skill(
    skill: dict[str, Any],
    failure_pattern: FailurePattern,
    template_fields: list[str] | None = None,
) -> RewriteResult:
    """Decompose a failing skill into sub-skills using LLM.

    Args:
        skill: The original skill dict (from the store).
        failure_pattern: The detected failure pattern.
        template_fields: List of template field names (if available).

    Returns:
        RewriteResult with decomposed sub-skills and rewritten skill.
    """
    field_list = template_fields or list(skill.get("confidence_overrides", {}).keys())
    if not field_list:
        # Try to infer from probe order or system prompt
        field_list = [p.get("region_type", "") for p in skill.get("probe_order", [])]

    user_prompt = json.dumps(
        {
            "skill_name": skill.get("name", "unknown"),
            "skill_description": skill.get("description", ""),
            "system_prompt": skill.get("system_prompt", ""),
            "probe_order": skill.get("probe_order", []),
            "invariants": skill.get("invariants", []),
            "failure_actions": skill.get("failure_actions", {}),
            "confidence_overrides": skill.get("confidence_overrides", {}),
            "template_fields": field_list,
            "failure_analysis": {
                "failure_rate": failure_pattern.failure_rate,
                "total_runs": failure_pattern.total_runs,
                "failed_runs": failure_pattern.failed_runs,
                "gap_type_counts": failure_pattern.gap_type_counts,
                "failing_fields": failure_pattern.failing_fields,
                "avg_cycles_per_run": failure_pattern.avg_cycles_per_run,
            },
        },
        indent=2,
    )

    try:
        response = invoke_llm(
            system_prompt=_DECOMPOSE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=4000,
        )
        response_text = response.content
    except Exception as e:
        logger.error("LLM decomposition failed: %s", e)
        return RewriteResult(
            original_definition_id=failure_pattern.definition_id,
            failure_pattern=failure_pattern,
            rationale=f"LLM decomposition failed: {e}",
        )

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Try to extract JSON from response
        match = re.search(r"\{[\s\S]*\}", response_text)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM decomposition response")
                return RewriteResult(
                    original_definition_id=failure_pattern.definition_id,
                    failure_pattern=failure_pattern,
                    rationale="Failed to parse LLM response",
                )
        else:
            logger.error("No JSON found in LLM decomposition response")
            return RewriteResult(
                original_definition_id=failure_pattern.definition_id,
                failure_pattern=failure_pattern,
                rationale="No JSON in LLM response",
            )

    # Parse sub-skills
    sub_skills = []
    for ss in result.get("sub_skills", []):
        sub_skills.append(
            SubSkill(
                name=ss.get("name", "unknown"),
                description=ss.get("description", ""),
                system_prompt=ss.get("system_prompt", ""),
                field_subset=ss.get("field_subset", []),
                probe_order=ss.get("probe_order", []),
                validation_criteria=ss.get("validation_criteria", []),
            )
        )

    # Build rewritten skill dict
    rewritten = dict(skill)
    rewritten["name"] = f"{skill.get('name', 'unknown')}_rewritten"
    rewritten["description"] = f"[Auto-rewritten] {skill.get('description', '')}"
    rewritten["sub_skills"] = [
        {
            "name": ss.name,
            "description": ss.description,
            "system_prompt": ss.system_prompt,
            "field_subset": ss.field_subset,
            "probe_order": ss.probe_order,
            "validation_criteria": ss.validation_criteria,
        }
        for ss in sub_skills
    ]

    return RewriteResult(
        original_definition_id=failure_pattern.definition_id,
        failure_pattern=failure_pattern,
        sub_skills=sub_skills,
        rewritten_skill=rewritten,
        rationale=result.get("rationale", ""),
        estimated_improvement=result.get("estimated_improvement", 0.0),
    )


# ---------------------------------------------------------------------------
# Heuristic decomposition (no LLM required)
# ---------------------------------------------------------------------------


def heuristic_decompose(
    skill: dict[str, Any],
    failure_pattern: FailurePattern,
    template_fields: list[str] | None = None,
) -> RewriteResult:
    """Decompose a skill heuristically without LLM.

    Splits fields into groups based on failure patterns:
    - Frequently failing fields get their own focused sub-skill
    - Remaining fields are grouped by probe order proximity

    Args:
        skill: The original skill dict.
        failure_pattern: The detected failure pattern.
        template_fields: List of template field names.

    Returns:
        RewriteResult with heuristic sub-skills.
    """
    field_list = template_fields or list(skill.get("confidence_overrides", {}).keys())
    if not field_list:
        field_list = [p.get("region_type", "") for p in skill.get("probe_order", [])]

    # Identify frequently failing fields (>30% of failures)
    failing_fields = set()
    for field_name, count in failure_pattern.failing_fields.items():
        if count >= failure_pattern.failed_runs * 0.3:
            failing_fields.add(field_name)

    sub_skills: list[SubSkill] = []

    # Group 1: Failing fields (each gets focused attention)
    if failing_fields:
        sub_skills.append(
            SubSkill(
                name="extract_failing_fields",
                description=f"Focused extraction of frequently failing fields: {', '.join(failing_fields)}",
                system_prompt=(
                    f"You are extracting specific fields that have been failing: {', '.join(failing_fields)}. "
                    "Focus on these fields with maximum attention. Use VLM for any ambiguous regions. "
                    "Double-check grounding for every value extracted."
                ),
                field_subset=list(failing_fields),
                probe_order=[
                    {
                        "region_type": "full_page",
                        "rationale": "Scan entire page for failing fields",
                    },
                ],
                validation_criteria=[
                    f"Field '{f}' must have a non-empty value" for f in failing_fields
                ],
            )
        )

    # Group 2: Remaining fields (split into chunks of 3-5)
    remaining = [f for f in field_list if f not in failing_fields]
    chunk_size = 4
    for i in range(0, len(remaining), chunk_size):
        chunk = remaining[i : i + chunk_size]
        if not chunk:
            continue
        sub_skills.append(
            SubSkill(
                name=f"extract_fields_group_{i // chunk_size + 1}",
                description=f"Extract fields: {', '.join(chunk)}",
                system_prompt=(
                    f"You are extracting these fields: {', '.join(chunk)}. "
                    "Use OCR for text fields and VLM for complex regions. "
                    "Ensure every value has proper grounding."
                ),
                field_subset=chunk,
                probe_order=skill.get("probe_order", [])[:3],
                validation_criteria=[f"Field '{f}' must be grounded with a bbox" for f in chunk],
            )
        )

    # Build rewritten skill
    rewritten = dict(skill)
    rewritten["name"] = f"{skill.get('name', 'unknown')}_rewritten"
    rewritten["description"] = f"[Heuristic rewrite] {skill.get('description', '')}"
    rewritten["sub_skills"] = [
        {
            "name": ss.name,
            "description": ss.description,
            "system_prompt": ss.system_prompt,
            "field_subset": ss.field_subset,
            "probe_order": ss.probe_order,
            "validation_criteria": ss.validation_criteria,
        }
        for ss in sub_skills
    ]

    return RewriteResult(
        original_definition_id=failure_pattern.definition_id,
        failure_pattern=failure_pattern,
        sub_skills=sub_skills,
        rewritten_skill=rewritten,
        rationale=(
            f"Heuristic decomposition: {len(failing_fields)} frequently failing fields "
            f"isolated into focused sub-skill, {len(remaining)} remaining fields "
            f"split into {(len(remaining) + chunk_size - 1) // chunk_size} groups."
        ),
        estimated_improvement=0.1,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def rewrite_failing_skill(
    definition_id: str,
    runs: list[dict[str, Any]],
    skill: dict[str, Any],
    template_fields: list[str] | None = None,
    use_llm: bool = True,
    min_sample: int = DEFAULT_MIN_SAMPLE_SIZE,
    failure_threshold: float = DEFAULT_FAILURE_THRESHOLD,
) -> RewriteResult | None:
    """Analyze failures and rewrite a failing skill into sub-skills.

    This is the main entry point for agentic query rewriting [BLK-073].

    Args:
        definition_id: The agent definition ID.
        runs: List of run dicts for this definition.
        skill: The current skill dict.
        template_fields: List of template field names (optional).
        use_llm: If True, use LLM for decomposition; if False, use heuristic.
        min_sample: Minimum runs to trigger analysis.
        failure_threshold: Failure rate threshold to trigger rewriting.

    Returns:
        RewriteResult if rewriting was triggered, None if no action needed.
    """
    pattern = analyze_failures(definition_id, runs, min_sample, failure_threshold)
    if pattern is None:
        return None

    if use_llm:
        result = decompose_skill(skill, pattern, template_fields)
        # Fall back to heuristic if LLM decomposition produced no sub-skills
        if not result.sub_skills:
            logger.info("LLM decomposition produced no sub-skills, falling back to heuristic")
            result = heuristic_decompose(skill, pattern, template_fields)
        return result
    else:
        return heuristic_decompose(skill, pattern, template_fields)
