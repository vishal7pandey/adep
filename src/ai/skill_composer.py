"""AI Skill Composer — generate skills from natural language and examples [BLK-068].

A meta-agent that generates a Skill (system prompt, tool preferences, probe
order, invariants, failure actions, known failures, confidence overrides)
from a natural language description and optional sample document metadata.

The generated skill is a candidate playbook. It can be co-evolved with the
Surrogate Verifier (BLK-070) in an iterative loop:

    generate → run → verify → patch → repeat

Uses Azure OpenAI (GPT-5.4) with a structured system prompt. The generated
skill dict is returned for user review — not auto-saved to the store.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.providers.llm import invoke_llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt — instructs the LLM to produce a skill definition as JSON
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an AI assistant that generates document extraction skill playbooks from natural language descriptions.

A skill playbook tells an autonomous extraction agent HOW to approach a document type. It contains:

1. **system_prompt**: Instructions that frame the agent for this document type. Should mention: what the document is, key regions to look for, tool preferences (OCR vs VLM), grounding requirements, and any document-specific quirks.

2. **tool_preferences**: Maps region_type -> preferred tool. Common tools: ocr, vlm, detect_layout, crop, ground, read_table. Common region types: text, table, chart, handwriting, stamp, logo, header, footer, signature.

3. **probe_order**: Ordered list of {region_type, rationale} telling the agent which regions to examine first. Each entry should explain WHY this region is probed at this position.

4. **invariants**: Declarative math/logic rules. Each has: name, fields (list of field paths), description. Examples: "subtotal + tax == total", "end_date >= start_date", "sum of line_items equals subtotal".

5. **failure_actions**: Maps gap_type -> suggested action. Gap types: missing, type_error, format_error, ungrounded, low_confidence, invariant_failed, semantic_fail. Each action should be a concrete hint for the agent.

6. **known_failures**: Free-text description of common failure modes and recovery strategies for this document type.

7. **confidence_overrides**: Maps field_name -> minimum confidence threshold (0.0-1.0). Higher for critical fields (IDs, amounts), lower for optional fields.

Produce a JSON object with this exact structure:
{
  "name": "snake_case_skill_name",
  "description": "Brief description of what this skill extracts",
  "system_prompt": "The system prompt text for the agent",
  "tool_preferences": {"region_type": "tool_name"},
  "probe_order": [{"region_type": "...", "rationale": "..."}],
  "invariants": [{"name": "...", "fields": ["field1", "field2"], "description": "..."}],
  "failure_actions": {"gap_type": "suggested action text"},
  "known_failures": "Free text about common issues",
  "confidence_overrides": {"field_name": 0.85}
}

Rules:
- Skill name MUST be snake_case
- Include ALL gap types in failure_actions (missing, type_error, format_error, ungrounded, low_confidence, invariant_failed, semantic_fail)
- Include 3-6 probe_order entries
- Include 1-4 invariants if the document type has math/logic relationships
- Include 3-8 tool_preferences
- Make the system_prompt specific and actionable (3-8 sentences)
- Return ONLY the JSON, no markdown or explanation"""


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_VALID_GAP_TYPES = {
    "missing",
    "type_error",
    "format_error",
    "ungrounded",
    "low_confidence",
    "invariant_failed",
    "semantic_fail",
}

_VALID_TOOLS = {
    "ocr",
    "vlm",
    "detect_layout",
    "crop",
    "ground",
    "read_table",
    "classify",
    "table_detection",
    "signature_detection",
}


def _normalize_name(name: str) -> str:
    """Normalize a skill name to snake_case."""
    s = re.sub(r"[^\w\s]", "", name.lower().strip())
    s = re.sub(r"[\s]+", "_", s)
    s = s.strip("_")
    return s


def _validate_tool_preferences(raw: dict[str, Any]) -> dict[str, str]:
    """Validate and normalize tool preferences."""
    result: dict[str, str] = {}
    for region_type, tool in raw.items():
        tool_lower = str(tool).lower().strip()
        if tool_lower not in _VALID_TOOLS:
            logger.debug(
                "Unknown tool '%s' for region '%s' — keeping anyway", tool_lower, region_type
            )
        result[str(region_type).lower().strip()] = tool_lower
    return result


def _validate_probe_order(raw: list[Any]) -> list[dict[str, str]]:
    """Validate and normalize probe order entries."""
    result: list[dict[str, str]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        region_type = str(entry.get("region_type", "")).strip()
        rationale = str(entry.get("rationale", "")).strip()
        if region_type:
            result.append({"region_type": region_type, "rationale": rationale})
    return result


def _validate_invariants(raw: list[Any]) -> list[dict[str, Any]]:
    """Validate and normalize invariant specs."""
    result: list[dict[str, Any]] = []
    for inv in raw:
        if not isinstance(inv, dict):
            continue
        name = str(inv.get("name", "")).strip()
        fields_list = inv.get("fields", [])
        if not isinstance(fields_list, list):
            fields_list = [str(fields_list)]
        else:
            fields_list = [str(f) for f in fields_list]
        description = str(inv.get("description", "")).strip()
        if name:
            result.append(
                {
                    "name": name,
                    "fields": fields_list,
                    "description": description,
                }
            )
    return result


def _validate_failure_actions(raw: dict[str, Any]) -> dict[str, str]:
    """Validate and normalize failure actions, ensuring all gap types are present."""
    result: dict[str, str] = {}
    for gap_type, action in raw.items():
        gt = str(gap_type).lower().strip()
        if gt in _VALID_GAP_TYPES:
            result[gt] = str(action).strip()
    # Ensure all gap types have at least a default action
    defaults = {
        "missing": "Run detect_layout to find the relevant region, then crop and read it.",
        "type_error": "Re-crop the region and re-read with ocr. If non-numeric, ask vlm.",
        "format_error": "Re-read the region and ask vlm to normalize to the required format.",
        "ungrounded": "Call the ground tool to trace this value to its bounding box.",
        "low_confidence": "Re-crop tightly and re-read. If still low, use vlm with a targeted question.",
        "invariant_failed": "Re-crop the relevant regions and re-read the affected fields.",
        "semantic_fail": "Re-crop and re-read with vlm, asking a targeted question.",
    }
    for gt, default in defaults.items():
        result.setdefault(gt, default)
    return result


def _validate_confidence_overrides(raw: dict[str, Any]) -> dict[str, float]:
    """Validate and normalize confidence overrides."""
    result: dict[str, float] = {}
    for field_name, threshold in raw.items():
        try:
            val = float(threshold)
            if 0.0 <= val <= 1.0:
                result[str(field_name).strip()] = val
        except (TypeError, ValueError):
            continue
    return result


# ---------------------------------------------------------------------------
# Heuristic fallback (no LLM available)
# ---------------------------------------------------------------------------


def _heuristic_skill(description: str, sample_fields: list[str] | None = None) -> dict[str, Any]:
    """Generate a basic skill dict without an LLM call [BLK-068].

    Produces a generic but functional skill based on the description keywords.
    """
    name = _normalize_name(description.split()[0] if description else "custom")
    if not name:
        name = "custom"

    # Try to infer document type from description keywords
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in ("invoice", "receipt", "bill")):
        doc_type = "invoice"
        system_prompt = (
            f"You are a document extraction agent for invoices/receipts. "
            f"Call detect_layout first to build a region map. Look for header "
            f"region (invoice number, date), vendor info, line items table, and "
            f"totals band. Prefer OCR for text, VLM for handwriting or stamps. "
            f"Every value must be grounded to its bounding box."
        )
        probe_order = [
            {
                "region_type": "header",
                "rationale": "Invoice number and date are usually top-right.",
            },
            {"region_type": "text", "rationale": "Vendor name is typically near the top."},
            {"region_type": "table", "rationale": "Line items are in the main body table."},
            {
                "region_type": "text",
                "rationale": "Totals (subtotal, tax, total) are near the bottom.",
            },
        ]
        invariants = [
            {
                "name": "sum_check",
                "fields": ["subtotal", "tax", "total"],
                "description": "subtotal + tax == total",
            },
        ]
        tool_prefs = {"text": "ocr", "table": "ocr", "handwriting": "vlm", "stamp": "vlm"}
        confidence = {"invoice_number": 0.85, "total": 0.85}
        known_failures = (
            "Tax fields may be labeled differently. Subtotal may be misread. "
            "Use VLM if OCR returns garbled text."
        )
    elif any(kw in desc_lower for kw in ("bank", "statement", "account")):
        doc_type = "bank_statement"
        system_prompt = (
            f"You are a document extraction agent for bank statements. "
            f"Call detect_layout first. Look for account info header, "
            f"transaction tables, and summary balances. Prefer OCR for "
            f"tabular data. Every value must be grounded."
        )
        probe_order = [
            {"region_type": "header", "rationale": "Bank name and account number are at the top."},
            {"region_type": "text", "rationale": "Statement period and account holder info."},
            {"region_type": "table", "rationale": "Transactions are in the main table."},
            {"region_type": "text", "rationale": "Opening/closing balances and totals."},
        ]
        invariants = [
            {
                "name": "balance_check",
                "fields": ["opening_balance", "closing_balance", "total_credits", "total_debits"],
                "description": "opening_balance + total_credits - total_debits == closing_balance",
            },
        ]
        tool_prefs = {"text": "ocr", "table": "ocr", "chart": "vlm"}
        confidence = {"account_number": 0.85, "closing_balance": 0.85}
        known_failures = (
            "Transaction tables may span multiple pages. Balances may be in summary boxes."
        )
    else:
        doc_type = "generic"
        system_prompt = (
            f"You are a document extraction agent. Extract fields from the "
            f"document by calling detect_layout first, then cropping and "
            f"reading specific regions. Prefer OCR for text, VLM for "
            f"handwriting, charts, or stamps. Every value must be grounded "
            f"to its bounding box."
        )
        probe_order = [
            {"region_type": "header", "rationale": "Key identifiers are usually at the top."},
            {"region_type": "text", "rationale": "Primary text content in the body."},
            {"region_type": "table", "rationale": "Tabular data if present."},
            {"region_type": "footer", "rationale": "Signatures, totals, or dates at the bottom."},
        ]
        invariants = []
        tool_prefs = {"text": "ocr", "table": "ocr", "handwriting": "vlm", "chart": "vlm"}
        confidence = {}
        known_failures = "Document quality may vary. Use VLM when OCR returns garbled text."

    # Include sample fields in confidence overrides if provided
    if sample_fields:
        for f in sample_fields:
            confidence.setdefault(f, 0.80)

    return {
        "name": name,
        "description": description[:200] if description else f"Generated skill for {doc_type}",
        "system_prompt": system_prompt,
        "tool_preferences": tool_prefs,
        "probe_order": probe_order,
        "invariants": invariants,
        "failure_actions": {},  # _validate_failure_actions will fill defaults
        "known_failures": known_failures,
        "confidence_overrides": confidence,
        "_heuristic": True,
    }


# ---------------------------------------------------------------------------
# Skill patch application (from Surrogate Verifier)
# ---------------------------------------------------------------------------


def apply_skill_patch(skill: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Apply a skill patch from the Surrogate Verifier to a skill dict [BLK-068, BLK-070].

    Args:
        skill: The current skill dict.
        patch: A skill_patch dict from the Surrogate Verifier containing
            invariants_to_add, failure_actions_to_add, probe_order_adjustments,
            and system_prompt_suggestions.

    Returns:
        A new skill dict with patches applied.
    """
    patched = json.loads(json.dumps(skill, default=str))

    # Add new invariants
    for inv in patch.get("invariants_to_add", []):
        if isinstance(inv, dict) and inv.get("name"):
            existing_names = {i.get("name") for i in patched.get("invariants", [])}
            if inv["name"] not in existing_names:
                patched.setdefault("invariants", []).append(
                    {
                        "name": inv["name"],
                        "fields": inv.get("fields", []),
                        "description": inv.get("description", ""),
                    }
                )

    # Add new failure actions
    for condition, action in patch.get("failure_actions_to_add", {}).items():
        patched.setdefault("failure_actions", {})[condition] = str(action)

    # Adjust probe order
    for adj in patch.get("probe_order_adjustments", []):
        if not isinstance(adj, dict):
            continue
        region_type = adj.get("region_type", "")
        position = adj.get("position", "last")
        rationale = adj.get("rationale", "")
        if not region_type:
            continue
        entry = {"region_type": region_type, "rationale": rationale}
        po = patched.setdefault("probe_order", [])
        if position == "first":
            po.insert(0, entry)
        elif position == "last":
            po.append(entry)
        elif position.startswith("after:"):
            after_field = position.split(":", 1)[1]
            for i, existing in enumerate(po):
                if after_field in existing.get("region_type", ""):
                    po.insert(i + 1, entry)
                    break
            else:
                po.append(entry)

    # Apply system prompt suggestions
    suggestions = patch.get("system_prompt_suggestions", "")
    if suggestions and isinstance(suggestions, str) and suggestions.strip():
        current = patched.get("system_prompt", "")
        patched["system_prompt"] = f"{current}\n\nAdditional guidance from verifier:\n{suggestions}"

    return patched


# ---------------------------------------------------------------------------
# Co-evolution result
# ---------------------------------------------------------------------------


@dataclass
class CoEvolutionResult:
    """Result of a generate → verify → patch co-evolution loop [BLK-068].

    Attributes:
        skill: The final (best) skill dict.
        iterations: Number of co-evolution iterations completed.
        verifier_reports: List of verifier reports from each iteration.
        history: List of (iteration, skill_snapshot) tuples.
        token_usage: Total token usage across all LLM calls.
    """

    skill: dict[str, Any] = field(default_factory=dict)
    iterations: int = 0
    verifier_reports: list[dict[str, Any]] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    token_usage: dict[str, int] = field(
        default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill": self.skill,
            "iterations": self.iterations,
            "verifier_reports": self.verifier_reports,
            "history": self.history,
            "token_usage": self.token_usage,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_skill(
    description: str,
    sample_fields: list[str] | None = None,
    sample_document_summary: str | None = None,
) -> dict[str, Any]:
    """Generate a skill playbook from a natural language description [BLK-068].

    Args:
        description: Natural language description of the document type and
            what to extract (e.g. "Extract invoice number, date, vendor,
            line items, and totals from commercial invoices").
        sample_fields: Optional list of field names from a template schema
            that the skill should know about.
        sample_document_summary: Optional summary of a sample document
            (e.g. "Multi-page PDF with itemized shipping charges and HTSUS codes").

    Returns:
        Generated skill dict with validated fields. If LLM is unavailable,
        falls back to a heuristic generator.
    """
    if not description or not description.strip():
        return {
            "name": "",
            "description": "",
            "system_prompt": "",
            "tool_preferences": {},
            "probe_order": [],
            "invariants": [],
            "failure_actions": {},
            "known_failures": "",
            "confidence_overrides": {},
            "error": "Description is required",
        }

    # Build user prompt with optional context
    parts = [f"## Description\n{description}"]
    if sample_fields:
        parts.append(
            f"## Template Fields\nThe skill should help extract these fields: {', '.join(sample_fields)}"
        )
    if sample_document_summary:
        parts.append(f"## Sample Document Summary\n{sample_document_summary}")
    parts.append("Generate the skill playbook JSON.")
    user_prompt = "\n\n".join(parts)

    response = invoke_llm(_SYSTEM_PROMPT, user_prompt, max_tokens=4000)

    if not response.content:
        logger.warning("LLM call failed — falling back to heuristic skill generator")
        result = _heuristic_skill(description, sample_fields)
        result["failure_actions"] = _validate_failure_actions(result.get("failure_actions", {}))
        return result

    # Parse JSON from LLM response
    content = response.content.strip()
    try:
        start = content.find("{")
        end = content.rfind("}") + 1
        if start == -1 or end == 0:
            logger.warning("LLM response contained no JSON — falling back to heuristic")
            result = _heuristic_skill(description, sample_fields)
            result["failure_actions"] = _validate_failure_actions(result.get("failure_actions", {}))
            return result
        raw = json.loads(content[start:end])
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Failed to parse LLM response as JSON: %s — falling back to heuristic", e)
        result = _heuristic_skill(description, sample_fields)
        result["failure_actions"] = _validate_failure_actions(result.get("failure_actions", {}))
        return result

    # Validate and normalize all fields
    result = {
        "name": _normalize_name(raw.get("name", "custom")),
        "description": raw.get("description", ""),
        "system_prompt": raw.get("system_prompt", ""),
        "tool_preferences": _validate_tool_preferences(raw.get("tool_preferences", {})),
        "probe_order": _validate_probe_order(raw.get("probe_order", [])),
        "invariants": _validate_invariants(raw.get("invariants", [])),
        "failure_actions": _validate_failure_actions(raw.get("failure_actions", {})),
        "known_failures": raw.get("known_failures", ""),
        "confidence_overrides": _validate_confidence_overrides(raw.get("confidence_overrides", {})),
        "_token_usage": {
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "total_tokens": response.total_tokens,
        },
    }

    return result


def co_evolve_skill(
    description: str,
    trace: list[Any],
    gap_report: Any,
    extraction: dict[str, Any],
    sample_fields: list[str] | None = None,
    max_iterations: int = 3,
) -> CoEvolutionResult:
    """Co-evolve a skill with the Surrogate Verifier [BLK-068, BLK-070].

    Runs the generate → verify → patch loop up to max_iterations times.

    Args:
        description: Natural language description of the document type.
        trace: Execution trace from a sample run.
        gap_report: GapReport from the sample run.
        extraction: Extracted field values from the sample run.
        sample_fields: Optional field names from the template schema.
        max_iterations: Maximum number of co-evolution iterations.

    Returns:
        CoEvolutionResult with the final skill and iteration history.
    """
    from src.ai.surrogate_verifier import verify_skill

    result = CoEvolutionResult()

    # Step 1: Generate initial skill
    skill = generate_skill(description, sample_fields=sample_fields)
    result.history.append({"iteration": 0, "skill": json.loads(json.dumps(skill, default=str))})

    # Accumulate token usage
    tu = skill.pop("_token_usage", {})
    result.token_usage["input_tokens"] += tu.get("input_tokens", 0)
    result.token_usage["output_tokens"] += tu.get("output_tokens", 0)
    result.token_usage["total_tokens"] += tu.get("total_tokens", 0)

    for i in range(max_iterations):
        # Step 2: Verify the skill with the Surrogate Verifier
        verifier_report = verify_skill(
            skill=skill,
            trace=trace,
            gap_report=gap_report,
            extraction=extraction,
        )
        result.verifier_reports.append(verifier_report)

        # Accumulate token usage from verifier
        vtu = verifier_report.get("_token_usage", {})
        result.token_usage["input_tokens"] += vtu.get("input_tokens", 0)
        result.token_usage["output_tokens"] += vtu.get("output_tokens", 0)
        result.token_usage["total_tokens"] += vtu.get("total_tokens", 0)

        # Step 3: Check if we should stop (no diagnoses or no patch)
        diagnoses = verifier_report.get("diagnoses", [])
        patch = verifier_report.get("skill_patch", {})
        if not diagnoses or (
            not patch.get("invariants_to_add")
            and not patch.get("failure_actions_to_add")
            and not patch.get("probe_order_adjustments")
            and not patch.get("system_prompt_suggestions")
        ):
            logger.info("Co-evolution converged at iteration %d (no more patches)", i + 1)
            break

        # Step 4: Apply the patch
        skill = apply_skill_patch(skill, patch)
        result.history.append(
            {
                "iteration": i + 1,
                "skill": json.loads(json.dumps(skill, default=str)),
                "patch_applied": patch,
            }
        )
        result.iterations = i + 1

    result.skill = skill
    return result
