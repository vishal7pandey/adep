"""PurchaseOrderSF1449Skill — extraction playbook for SF-1449 forms."""

from __future__ import annotations

from src.agent.validator import GapType
from src.skills.base import Skill


_SYSTEM_PROMPT = """\
You are an extraction agent for U.S. Standard Form 1449 documents.
Focus on form structure markers rather than business line-item semantics.

Principles:
- Detect the SF-1449 title and revision block first.
- Verify presence of major numbered sections (solicitation, order,
  contract, method-of-solicitation, schedule table).
- Treat this as a form-structure extraction task.
"""


_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Locate the missing section header and extract as structural presence/absence.",
    GapType.LOW_CONFIDENCE: "Crop the relevant form block and re-read the heading text.",
}


PurchaseOrderSF1449Skill = Skill(
    name="purchase_order_sf1449",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={"text": "ocr", "table": "read_table"},
    probe_order=[
        ("header", "SF-1449 title and revision appear near the top"),
        ("text", "Section markers are distributed through the first page"),
        ("table", "Schedule columns appear in the line-item section"),
    ],
    invariants=[],
    failure_actions=_FAILURE_ACTIONS,
    known_failures="Some forms are blank templates; extraction should still mark structural sections as present.",
    confidence_overrides={
        "form_title": 0.85,
        "form_revision": 0.85,
    },
)
