"""PackingListSkill — playbook for packing list extraction [BLK-106]."""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


PACKING_LIST_SYSTEM_PROMPT = """\
You are a packing list extraction agent. Your job is to fill the
PackingListTemplate schema by reasoning over the document image and
calling atomic tools.

Principles:
- Call detect_layout first. Packing lists have a header (PL number,
  shipper, consignee) and an items table.
- Use OCR for text; use read_table for the items table.
- Packing lists may span multiple pages — check for continuation pages.
- Verify that total_packages matches the number of unique carton numbers.
- Verify that total_weight equals the sum of item weights.
"""


def _check_total_weight(e: dict) -> tuple[bool, str]:
    """Verify sum of item weights equals total weight."""
    items = e.get("items")
    total_weight = e.get("total_weight")
    if not items or not total_weight:
        return True, ""
    item_list = items.value if hasattr(items, "value") else items
    if not isinstance(item_list, list) or len(item_list) == 0:
        return True, ""
    weight_sum = sum(
        i.get("weight", 0) if isinstance(i, dict) else getattr(i, "weight", 0)
        for i in item_list
    )
    if abs(weight_sum - total_weight.value) > 0.01:
        return False, f"sum of item weights ({weight_sum}) != total_weight ({total_weight.value})"
    return True, ""


_weight_check = Invariant(
    name="item_weights_sum_equals_total_weight",
    fields=["items", "total_weight"],
    fn=_check_total_weight,
)

PACKING_LIST_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Run detect_layout to find the header or items table.",
    GapType.TYPE_ERROR: "Re-crop and re-read with ocr. Ensure numeric values are parsed correctly.",
    GapType.FORMAT_ERROR: "Re-read the date and normalize to ISO YYYY-MM-DD.",
    GapType.UNGROUNDED: "Call the ground tool to trace this value to its bounding box.",
    GapType.LOW_CONFIDENCE: "Re-crop tightly and re-read with ocr.",
    GapType.INVARIANT_FAILED: "The weight check failed. Re-read item weights and total weight.",
    GapType.SEMANTIC_FAIL: "Re-crop and re-read with vlm.",
}

PackingListSkill = Skill(
    name="packing_list",
    system_prompt=PACKING_LIST_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
    },
    probe_order=[
        ("header", "PL number, date, shipper, and consignee are in the header."),
        ("text", "Origin and destination are usually below the parties."),
        ("text", "Container number may be in the header or footer."),
        ("table", "Items are in the main table — read with ocr or read_table."),
        ("text", "Total packages and total weight are usually at the bottom."),
    ],
    invariants=[_weight_check],
    failure_actions=PACKING_LIST_FAILURE_ACTIONS,
    known_failures=(
        "Packing lists vary in format across freight forwarders. "
        "Some use multi-page tables. Weights may be in kg or lbs."
    ),
    confidence_overrides={
        "pl_number": 0.85,
        "container_number": 0.80,
    },
)
