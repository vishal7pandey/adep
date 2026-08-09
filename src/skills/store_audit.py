"""StoreAuditSkill — retail store audit checklist extraction [BLK-087].

Blended structured checklists + unstructured photo evidence.
Cross-reference visual evidence against textual notes.
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are a store audit extraction agent. Your job is to extract audit
checklist data and photo evidence counts from retail store audit
reports into the StoreAuditTemplate.

Principles:
- Store audits blend structured checklists with unstructured photos.
  Use detect_layout to find checklist tables and detect_figures for
  photo evidence.
- Cleanliness score is 1-5 integer scale.
- Compliance items are boolean (pass/fail) per checklist item.
- Photo evidence count: count the number of photos/figures in the report.
- overall_pass is derived: all mandatory compliance items must pass.
- Use VLM to interpret photo evidence (e.g. shelf stocking, cleanliness).
"""


def _check_cleanliness_range(e: dict) -> tuple[bool, str]:
    """Verify cleanliness_score is 1-5."""
    score = e["cleanliness_score"].value
    if not (1 <= score <= 5):
        return False, f"cleanliness_score ({score}) outside valid range [1, 5]"
    return True, ""


_cleanliness_check = Invariant(
    name="cleanliness_score_in_range",
    fields=["cleanliness_score"],
    fn=_check_cleanliness_range,
)


def _check_photo_count_positive(e: dict) -> tuple[bool, str]:
    """Verify photo_evidence_count is non-negative."""
    count = e.get("photo_evidence_count")
    if count is None:
        return True, ""
    val = count.value if hasattr(count, "value") else count
    if val < 0:
        return False, f"photo_evidence_count ({val}) cannot be negative"
    return True, ""


_photo_count_check = Invariant(
    name="photo_evidence_count_non_negative",
    fields=["photo_evidence_count"],
    fn=_check_photo_count_positive,
)


def _check_overall_pass(e: dict) -> tuple[bool, str]:
    """Verify overall_pass is True only if all compliance items pass."""
    items = e.get("compliance_items")
    overall = e.get("overall_pass")
    if items is None or overall is None:
        return True, ""
    item_list = items.value if hasattr(items, "value") else items
    overall_val = overall.value if hasattr(overall, "value") else overall
    if not isinstance(item_list, list):
        return True, ""
    all_pass = all(
        item.get("status", "fail") == "pass"
        for item in item_list
        if isinstance(item, dict) and item.get("mandatory", True)
    )
    if overall_val and not all_pass:
        return False, "overall_pass is True but some mandatory compliance items failed"
    return True, ""


_overall_pass_check = Invariant(
    name="overall_pass_requires_all_mandatory_pass",
    fields=["compliance_items", "overall_pass"],
    fn=_check_overall_pass,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING:
        "Run detect_layout to find the checklist table. Store ID and "
        "audit date are in the header. Use detect_figures to count "
        "photo evidence.",
    GapType.FORMAT_ERROR:
        "Cleanliness score must be 1-5. Compliance items are boolean. "
        "Re-crop and re-read the checklist.",
}


StoreAuditSkill = Skill(
    name="store_audit",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "figure": "vlm",
        "handwriting": "vlm",
    },
    probe_order=[
        ("header", "Store ID, audit date, and inspector name are in the header"),
        ("table", "Compliance checklist items are in a table — read with OCR"),
        ("figure", "Photo evidence: use detect_figures to count and VLM to interpret"),
        ("text", "Violations and notes are usually at the bottom"),
    ],
    invariants=[_cleanliness_check, _photo_count_check, _overall_pass_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Photos may be low quality — use VLM for interpretation. "
        "Checklist items may use checkmarks (✓/✗) — OCR may garble these. "
        "Compliance items may be spread across multiple pages. "
        "Overall pass/fail may be a derived field, not explicitly stated."
    ),
    confidence_overrides={
        "store_id": 0.95,
        "audit_date": 0.90,
        "cleanliness_score": 0.85,
    },
)
