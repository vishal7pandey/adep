"""Standard VLM fallback patterns for degraded documents [BLK-044, §13].

Provides reusable failure action strings and probe order constants that
skills can reference to implement the OCR→crop→deskew→denoise→threshold→VLM
escalation pattern.

Usage:
    from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS, GEOMETRY_FIRST_PROBE_ORDER
    from src.skills.base import Skill

    MySkill = Skill(
        failure_actions={**VLM_FALLBACK_ACTIONS, GapType.MISSING: "..."},
        probe_order=GEOMETRY_FIRST_PROBE_ORDER,
        ...
    )
"""

from __future__ import annotations

from src.agent.validator import GapType


# ---------------------------------------------------------------------------
# Standard VLM fallback failure actions [BLK-044]
# ---------------------------------------------------------------------------

VLM_FALLBACK_ACTIONS: dict[GapType, str] = {
    GapType.LOW_CONFIDENCE:
        "OCR confidence is low. Crop the region tightly around this field, "
        "then deskew and denoise the crop, and re-read with ocr. If still "
        "low confidence, escalate to vlm with a targeted question about "
        "the expected field value.",

    GapType.MISSING:
        "Run detect_layout to find the relevant region. If the document is "
        "degraded (faded, skewed, dot-matrix), crop the region, apply deskew "
        "and denoise, then read with ocr. If OCR fails, escalate to vlm.",

    GapType.TYPE_ERROR:
        "Re-crop the region for this field. If the value is non-numeric, "
        "apply threshold to isolate the text, then re-read with ocr. "
        "If still wrong, ask vlm with a targeted question.",

    GapType.FORMAT_ERROR:
        "Re-read the region with ocr after applying deskew. If the format "
        "is still wrong, ask vlm to normalize the value to the required "
        "format (e.g. ISO date YYYY-MM-DD).",

    GapType.UNGROUNDED:
        "Call the ground tool to trace this value to its bounding box "
        "in the source image. If the region is degraded, crop and deskew "
        "before grounding.",

    GapType.INVARIANT_FAILED:
        "Re-crop the relevant regions for the fields involved in the "
        "invariant. Apply deskew and denoise if the document is degraded, "
        "then re-read with ocr. If OCR is garbled, use vlm.",

    GapType.SEMANTIC_FAIL:
        "The semantic check flagged this value as implausible. Re-crop "
        "the region and re-read with vlm, asking a targeted question "
        "about the expected value.",
}


# ---------------------------------------------------------------------------
# Geometry-first probe order for degraded documents [BLK-044]
# ---------------------------------------------------------------------------

GEOMETRY_FIRST_PROBE_ORDER: list[tuple[str, str]] = [
    ("header",
     "Auto-orient and deskew the page first — degraded documents are "
     "often rotated or skewed. Then detect_layout and read the header."),
    ("text",
     "Read text regions with ocr. If confidence is low, crop the specific "
     "region, denoise, and re-read. If still low, escalate to vlm."),
    ("table",
     "For tables, crop the table region, deskew, and use read_table or ocr. "
     "If the table is garbled, use vlm to extract structured data."),
    ("handwriting",
     "Handwriting regions bypass OCR entirely — route directly to vlm "
     "for native visual interpretation."),
    ("figure",
     "Figures and charts route to read_chart (VLM-only, no OCR)."),
]


# ---------------------------------------------------------------------------
# Handwriting bypass — skip OCR for HANDWRITING regions [BLK-044]
# ---------------------------------------------------------------------------

HANDWRITING_TOOL_PREFERENCE = "vlm"
"""Tool preference for HANDWRITING regions — bypasses OCR entirely."""

HANDWRITING_BYPASS_REGION_TYPES = {"handwriting", "stamp", "logo"}
"""Region types that should bypass OCR and route directly to VLM."""


def should_bypass_ocr(region_type: str) -> bool:
    """Check if a region type should bypass OCR and go directly to VLM [BLK-044].

    Args:
        region_type: The type of the region (e.g. "handwriting", "text").

    Returns:
        True if the region should bypass OCR and route to VLM.
    """
    return region_type.lower() in HANDWRITING_BYPASS_REGION_TYPES


def get_escalation_steps(failed_tool: str, confidence: float, threshold: float = 0.5) -> list[str]:
    """Get the standard escalation steps for a failed OCR attempt [BLK-044].

    Args:
        failed_tool: The tool that failed (e.g. "ocr").
        confidence: The confidence score of the failed attempt.
        threshold: Confidence threshold below which escalation is triggered.

    Returns:
        Ordered list of tool names to try as escalation.
    """
    if confidence >= threshold:
        return []

    if failed_tool == "ocr":
        return ["crop", "deskew", "denoise", "threshold", "ocr", "vlm"]

    return ["vlm"]
