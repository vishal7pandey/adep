"""BillOfQuantitiesSkill — construction BOQ extraction [BLK-042, §14].

Domain expertise for bill of quantities documents. Encodes:
- qty × rate = total invariant per line item
- subtotal + vat_amount = grand_total invariant
- Table extraction focus (read_table for structured BOQ tables)
- Geometry-first probe for degraded scanned BOQs
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS
from src.templates.bill_of_quantities import BillOfQuantitiesTemplate


_SYSTEM_PROMPT = """\
You are a bill of quantities extraction agent. Your job is to extract
structured line items from construction BOQ documents into the
BillOfQuantitiesTemplate.

Principles:
- BOQ documents are primarily tables — use read_table or detect_layout
  to find the table region, then extract line items.
- Each line item has: item_no, description, unit, quantity, rate, total.
- The validator will check that quantity × rate = total for each line.
- The validator will check that subtotal + vat_amount = grand_total.
- If the BOQ is a degraded scan, apply deskew and denoise before OCR.
- For large multi-page BOQs, use the document hierarchy to navigate pages.
"""


def _check_line_items(e: dict) -> tuple[bool, str]:
    """Verify qty × rate = total for each line item."""
    items = e["line_items"].value
    if not isinstance(items, list):
        return False, "line_items is not a list"
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        qty = item.get("quantity", 0)
        rate = item.get("rate", 0)
        total = item.get("total", 0)
        if abs((qty * rate) - total) > 0.01:
            return False, (f"Line item {i}: quantity ({qty}) × rate ({rate}) != total ({total})")
    return True, ""


_qty_rate_check = Invariant(
    name="qty_times_rate_equals_total",
    fields=["line_items"],
    fn=_check_line_items,
)


_subtotal_vat_check = Invariant(
    name="subtotal_plus_vat_equals_grand_total",
    fields=["subtotal", "vat_amount", "grand_total"],
    fn=lambda e: (
        abs((e["subtotal"].value + e["vat_amount"].value) - e["grand_total"].value) < 0.01,
        f"subtotal ({e['subtotal'].value}) + VAT ({e['vat_amount'].value}) "
        f"!= grand_total ({e['grand_total'].value})",
    ),
)


def _check_line_items_subtotal(e: dict) -> tuple[bool, str]:
    """Verify sum of line item totals equals subtotal."""
    items = e.get("line_items")
    subtotal = e.get("subtotal")
    if not items or not subtotal:
        return True, ""
    item_list = items.value if hasattr(items, "value") else items
    if not isinstance(item_list, list) or len(item_list) == 0:
        return True, ""
    line_sum = 0.0
    for item in item_list:
        if isinstance(item, dict):
            line_sum += item.get("total", 0)
        elif hasattr(item, "total"):
            line_sum += item.total
    if abs(line_sum - subtotal.value) > 0.01:
        return False, f"sum of line item totals ({line_sum}) != subtotal ({subtotal.value})"
    return True, ""


_line_items_subtotal_check = Invariant(
    name="line_items_sum_equals_subtotal",
    fields=["line_items", "subtotal"],
    fn=_check_line_items_subtotal,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING: "BOQ documents are table-heavy. Run detect_layout to find the table "
    "region, then use read_table to extract structured line items. "
    "If the scan is degraded, deskew and denoise first.",
    GapType.INVARIANT_FAILED: "Math check failed. Re-crop the relevant line items or totals band. "
    "Use read_table for structured extraction. If OCR is garbled, "
    "use VLM to extract the specific numeric values.",
}


BillOfQuantitiesSkill = Skill(
    name="bill_of_quantities",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "table": "read_table",
        "text": "ocr",
        "handwriting": "vlm",
        "figure": "read_chart",
    },
    probe_order=[
        ("header", "Project name, BOQ reference, and date are in the header"),
        ("table", "Line items are in the main BOQ table — use read_table"),
        ("text", "Subtotal, VAT, and grand total are in the totals band"),
    ],
    invariants=[_qty_rate_check, _subtotal_vat_check, _line_items_subtotal_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Degraded BOQ scans may need deskew before OCR. "
        "Line item totals may be calculated incorrectly by OCR — "
        "always verify qty × rate = total. "
        "VAT percentage may be labeled differently across regions. "
        "Multi-page BOQs: use document hierarchy to navigate."
    ),
    confidence_overrides={
        "grand_total": 0.90,
        "subtotal": 0.85,
        "line_items": 0.80,
        "vat_amount": 0.85,
        "project_name": 0.80,
    },
)
