"""Surrogate Verifier — information-isolated skill evaluator [BLK-070].

Evaluates a generated skill's execution trace and generates diagnostic
signatures without requiring ground-truth labels. Used by the AI Skill
Composer (BLK-068) in a co-evolution loop.

Analyzes: tool selection patterns, probe order efficiency, missing
invariants, failure action coverage, common failure signatures.
Returns: diagnoses + proposed tests + skill patches.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.providers.llm import invoke_llm

logger = logging.getLogger(__name__)


def _value_from(obj: Any, key: str, default: Any = None) -> Any:
    """Read a value from either a dict key or an object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


_SYSTEM_PROMPT = """You are an expert skill verifier for an AI document extraction agent. Your job is to analyze a skill's execution trace and identify weaknesses — WITHOUT access to ground-truth labels.

You will receive:
1. The skill definition (system prompt, tools, probe order, invariants, failure actions)
2. An execution trace from a sample document run
3. The gap report (which fields were satisfied vs missing)
4. The extracted output

Analyze the following aspects:
- **Tool selection patterns**: Did the agent use the right tools? Did it use OCR when VLM would be better? Did it waste cycles on redundant calls?
- **Probe order efficiency**: Was the probe order optimal? Did the agent probe low-value regions first?
- **Missing invariants**: Are there mathematical or logical invariants that should be checked but aren't declared? (e.g., total == sum(line_items) + tax)
- **Failure action coverage**: When a tool failed, did the skill have a fallback? Were failure actions comprehensive?
- **Common failure signatures**: Are there patterns in the trace that suggest systematic issues?

Return your analysis as JSON with this structure:
{
  "diagnoses": [
    {"type": "tool_selection|invariant|probe_order|failure_action|other", "severity": "high|medium|low", "message": "Description of the issue", "field": "affected field if applicable"}
  ],
  "proposed_tests": [
    {"assertion": "A test assertion to validate", "reason": "Why this test matters"}
  ],
  "skill_patch": {
    "invariants_to_add": [{"name": "...", "fields": [...], "description": "..."}],
    "failure_actions_to_add": {"condition": "action"},
    "probe_order_adjustments": [{"region_type": "...", "rationale": "...", "position": "first|last|after:field"}],
    "system_prompt_suggestions": "Optional improvements to the system prompt"
  }
}

Return ONLY the JSON. Do not use ground truth — base all diagnoses on the trace and skill definition."""


def _heuristic_verify(
    skill: dict[str, Any], trace: list[Any], gap_report: Any, extraction: dict[str, Any]
) -> dict[str, Any]:
    """Produce a deterministic verifier result when no LLM is available."""
    diagnoses: list[dict[str, Any]] = []
    proposed_tests: list[dict[str, Any]] = []
    skill_patch: dict[str, Any] = {
        "invariants_to_add": [],
        "failure_actions_to_add": {},
        "probe_order_adjustments": [],
        "system_prompt_suggestions": "",
    }

    # A missing report, or a report whose `gaps` / `satisfied` is None, counts as empty.
    gaps = _value_from(gap_report, "gaps", None) or []
    satisfied = _value_from(gap_report, "satisfied", None) or []
    trace_len = len(trace or [])

    if trace_len <= 1:
        diagnoses.append(
            {
                "type": "tool_selection",
                "severity": "medium",
                "message": "Execution trace is shallow; the run likely used a deterministic fallback or failed before multi-step probing.",
                "field": "",
            }
        )

    for gap in gaps[:8]:
        gap_type = _value_from(gap, "gap_type", "other")
        field_name = _value_from(gap, "field", "")
        detail = _value_from(gap, "detail", "")
        severity = "high" if gap_type in {"missing", "invariant_failed"} else "medium"
        diagnoses.append(
            {
                "type": "failure_action" if gap_type == "missing" else "other",
                "severity": severity,
                "message": f"Gap remains for {field_name}: {gap_type}. {detail}".strip(),
                "field": field_name,
            }
        )
        proposed_tests.append(
            {
                "assertion": f"{field_name} should be extracted with grounding"
                if field_name
                else "Missing fields should have grounded values",
                "reason": f"Run ended with unresolved {gap_type} gap.",
            }
        )

    if extraction and not gaps:
        proposed_tests.append(
            {
                "assertion": "Extracted values should maintain current field coverage on regression samples",
                "reason": f"Current run satisfied {len(satisfied)} fields without unresolved gaps.",
            }
        )

    if not skill.get("failure_actions"):
        skill_patch["system_prompt_suggestions"] = (
            "Add explicit failure actions for missing and low-confidence fields so the planner has deterministic recovery hints."
        )
    elif gaps:
        skill_patch["system_prompt_suggestions"] = (
            "Tighten the system prompt around unresolved fields and add stronger field-specific recovery instructions."
        )

    return {
        "diagnoses": diagnoses,
        "proposed_tests": proposed_tests,
        "skill_patch": skill_patch,
        "_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }


def _format_trace(trace: list[Any]) -> str:
    """Format execution trace entries for the LLM prompt."""
    if not trace:
        return "No trace entries (run may have failed before any tool calls)."

    lines = []
    for entry in trace:
        step = _value_from(entry, "step", "?")
        tool = _value_from(entry, "tool_name", _value_from(entry, "tool", "?"))
        thought = _value_from(entry, "thought", "")
        args = _value_from(entry, "tool_args", _value_from(entry, "args", {}))
        result_ok = _value_from(entry, "result", None)
        result_summary = _value_from(
            entry,
            "result_summary",
            str(result_ok)[:200] if result_ok else "N/A",
        )

        lines.append(
            f"  Step {step}: thought='{thought[:100]}', tool={tool}, "
            f"args={json.dumps(args, default=str)[:200]}, result={result_summary}"
        )
    return "\n".join(lines)


def _format_gap_report(gap_report: Any) -> str:
    """Format a gap report for the LLM prompt."""
    if gap_report is None:
        return "No gap report available."

    total = _value_from(gap_report, "total_fields", 0)
    satisfied = _value_from(gap_report, "satisfied", [])
    gaps = _value_from(gap_report, "gaps", [])

    satisfied_names = [_value_from(g, "field", str(g)) for g in satisfied] if satisfied else []
    gap_names = [_value_from(g, "field", str(g)) for g in gaps] if gaps else []

    return (
        f"Total fields: {total}\n"
        f"Satisfied ({len(satisfied_names)}): {', '.join(satisfied_names) or 'none'}\n"
        f"Gaps ({len(gap_names)}): {', '.join(gap_names) or 'none'}"
    )


def _format_extraction(extraction: dict[str, Any]) -> str:
    """Format extracted field values for the LLM prompt."""
    if not extraction:
        return "No fields extracted."

    lines = []
    for name, value in extraction.items():
        if hasattr(value, "value") or (isinstance(value, dict) and "value" in value):
            val = _value_from(value, "value")
            conf = _value_from(value, "confidence", 0.0)
            lines.append(f"  {name}: {val} (confidence={conf})")
        else:
            lines.append(f"  {name}: {value}")
    return "\n".join(lines)


def verify_skill(
    skill: dict[str, Any],
    trace: list[Any],
    gap_report: Any,
    extraction: dict[str, Any],
) -> dict[str, Any]:
    """Run the Surrogate Verifier on a skill + execution data [BLK-070].

    Args:
        skill: Skill definition dict (system_prompt, tools, probe_order, etc.).
        trace: Execution trace entries from a sample run.
        gap_report: GapReport from the run.
        extraction: Extracted field values.

    Returns:
        Diagnostic report dict with diagnoses, proposed_tests, skill_patch.
    """
    # Build the user prompt with all context
    skill_json = json.dumps(skill, default=str, indent=2)
    trace_str = _format_trace(trace)
    gap_str = _format_gap_report(gap_report)
    extraction_str = _format_extraction(extraction)

    user_prompt = (
        f"## Skill Definition\n{skill_json}\n\n"
        f"## Execution Trace\n{trace_str}\n\n"
        f"## Gap Report\n{gap_str}\n\n"
        f"## Extracted Output\n{extraction_str}\n\n"
        f"Analyze this skill's execution and provide your diagnostic report."
    )

    response = invoke_llm(_SYSTEM_PROMPT, user_prompt, max_tokens=3000)

    if not response.content:
        return _heuristic_verify(
            skill=skill, trace=trace, gap_report=gap_report, extraction=extraction
        )

    # Parse JSON from LLM response
    content = response.content.strip()
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning(
                "LLM response contained no JSON object — falling back to heuristic verifier"
            )
            return _heuristic_verify(
                skill=skill, trace=trace, gap_report=gap_report, extraction=extraction
            )
        result = json.loads(content[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Falling back to heuristic verifier after JSON parse failure: %s", e)
        return _heuristic_verify(
            skill=skill, trace=trace, gap_report=gap_report, extraction=extraction
        )

    # Ensure required keys exist
    result.setdefault("diagnoses", [])
    result.setdefault("proposed_tests", [])
    result.setdefault("skill_patch", {})

    result["_token_usage"] = {
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "total_tokens": response.total_tokens,
    }

    return result
