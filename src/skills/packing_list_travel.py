"""TravelPackingChecklistSkill — extraction playbook for travel checklists."""

from __future__ import annotations

from src.agent.validator import GapType
from src.skills.base import Skill


_SYSTEM_PROMPT = """\
You are an extraction agent for travel packing checklist documents.
Focus on checklist section structure and item coverage.

Principles:
- Identify standard checklist sections (documents, clothing, toiletries,
  electronics, health/safety, extras).
- Extract an approximate item count from checklist lines.
"""


_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Locate section headings and checklist lines in the body.",
    GapType.LOW_CONFIDENCE: "Re-crop and re-read section headings; use a wider crop for multi-line labels.",
}


TravelPackingChecklistSkill = Skill(
    name="packing_list_travel",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={"text": "ocr"},
    probe_order=[
        ("header", "Checklist title is usually at the top"),
        ("text", "Section headings are uppercase and separated by blocks"),
    ],
    invariants=[],
    failure_actions=_FAILURE_ACTIONS,
    known_failures="Travel checklists are not shipment manifests; avoid forcing logistics-specific line-item semantics.",
    confidence_overrides={
        "checklist_title": 0.85,
        "item_count_estimate": 0.75,
    },
)
