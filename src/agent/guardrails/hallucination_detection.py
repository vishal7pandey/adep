"""Hallucination detection & grounding enforcement [BLK-081].

Every extracted field must have a grounding bbox that points to actual
document content. Fields without grounding, or with grounding that
doesn't match the OCR/text layer, are flagged as hallucinations.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

HALLUCINATION_CONFIDENCE_CAP = 0.3
FUZZY_MATCH_THRESHOLD = 2  # Levenshtein distance


@dataclass
class GroundingCheckResult:
    """Result of a grounding verification check [BLK-081].

    Attributes:
        status: 'grounded', 'ungrounded', 'hallucination_suspected', or 'invariant_violation'.
        confidence: Adjusted confidence (capped if hallucination suspected).
        source_text: Raw OCR text at the bbox location (if available).
        message: Human-readable explanation.
    """

    status: str
    confidence: float
    source_text: str = ""
    message: str = ""


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


def check_grounding(
    field_name: str,
    value: Any,
    bbox: tuple[int, int, int, int] | None,
    page: int | None,
    ocr_text: str | None = None,
    claimed_confidence: float = 1.0,
) -> GroundingCheckResult:
    """Verify that an extracted field has proper grounding [BLK-081].

    Args:
        field_name: Name of the field being checked.
        value: The extracted value.
        bbox: Bounding box (x1, y1, x2, y2) or None if missing.
        page: Page number or None if missing.
        ocr_text: OCR text from the bbox region (if available).
        claimed_confidence: Confidence claimed by the LLM.

    Returns:
        GroundingCheckResult with status and adjusted confidence.
    """
    # 1. Mandatory grounding check
    if bbox is None or page is None:
        return GroundingCheckResult(
            status="ungrounded",
            confidence=0.0,
            message=f"Field '{field_name}' has no grounding bbox/page",
        )

    # 2. Grounding verification via fuzzy text match
    if ocr_text is not None and value is not None:
        value_str = str(value).strip().lower()
        ocr_str = ocr_text.strip().lower()

        if value_str and ocr_str:
            # Check if value appears in OCR text with fuzzy matching
            distance = _levenshtein(value_str, ocr_str)
            if distance > FUZZY_MATCH_THRESHOLD:
                # Also check if value is a substring of OCR text
                if value_str not in ocr_str:
                    logger.warning(
                        "Hallucination suspected for field '%s': value '%s' not found in OCR text '%s' (distance=%d) [BLK-081]",
                        field_name,
                        value_str,
                        ocr_str,
                        distance,
                    )
                    return GroundingCheckResult(
                        status="hallucination_suspected",
                        confidence=min(claimed_confidence, HALLUCINATION_CONFIDENCE_CAP),
                        source_text=ocr_text,
                        message=f"Value '{value}' not found in OCR text at bbox (Levenshtein={distance})",
                    )

    return GroundingCheckResult(
        status="grounded",
        confidence=claimed_confidence,
        source_text=ocr_text or "",
        message=f"Field '{field_name}' is properly grounded",
    )


@dataclass
class InvariantCheck:
    """A cross-field invariant to validate [BLK-081].

    Attributes:
        name: Human-readable invariant name.
        fields: List of field names involved.
        check_fn: Function that takes a dict of field_name -> value
            and returns (passed: bool, message: str).
    """

    name: str
    fields: list[str]
    check_fn: Any  # Callable[[dict[str, Any]], tuple[bool, str]]


def check_invariants(
    extraction: dict[str, Any],
    invariants: list[InvariantCheck],
) -> list[tuple[str, str]]:
    """Validate cross-field invariants [BLK-081].

    Args:
        extraction: Dict of field_name -> extracted value.
        invariants: List of invariant checks to run.

    Returns:
        List of (invariant_name, error_message) for violated invariants.
    """
    violations: list[tuple[str, str]] = []

    for invariant in invariants:
        # Only check if all required fields are present
        field_values = {f: extraction.get(f) for f in invariant.fields}
        if any(v is None for v in field_values.values()):
            continue

        passed, message = invariant.check_fn(field_values)
        if not passed:
            violations.append((invariant.name, message))
            logger.warning(
                "Invariant violation: %s — %s [BLK-081]",
                invariant.name,
                message,
            )

    return violations


def compute_hallucination_rate(
    fields: list[dict[str, Any]],
) -> float:
    """Compute the hallucination rate for a run [BLK-081].

    Args:
        fields: List of field dicts with 'status' keys.

    Returns:
        Percentage of fields with hallucination-related statuses.
    """
    if not fields:
        return 0.0

    hallucination_statuses = {"ungrounded", "hallucination_suspected", "invariant_violation"}
    flagged = sum(1 for f in fields if f.get("status") in hallucination_statuses)
    return (flagged / len(fields)) * 100.0
