"""PurchaseOrderSkill — playbook for purchase order extraction [BLK-106]."""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


PO_SYSTEM_PROMPT = """\
You are a purchase order extraction agent. Your job is to fill the
PurchaseOrderTemplate schema by reasoning over the document image and
calling atomic tools.

Principles:
- Call detect_layout first. POs have a header (PO number, date, buyer/vendor)
  and a line items table.
- Use OCR for text regions; use read_table for the line items table.
- Every value must be grounded.
- Verify that subtotal + tax + shipping == total.
- Verify that sum of line item amounts == subtotal.
"""


def _check_po_totals(e: dict) -> tuple[bool, str]:
    """Verify subtotal + tax + shipping == total."""
    subtotal = e.get("subtotal")
    tax = e.get("tax")
    shipping = e.get("shipping")
    total = e.get("total")
    if not all([subtotal, tax, shipping, total]):
        return True, ""
    expected = subtotal.value + tax.value + shipping.value
    if abs(expected - total.value) > 0.01:
        return False, (
            f"subtotal ({subtotal.value}) + tax ({tax.value}) + "
            f"shipping ({shipping.value}) = {expected} != total ({total.value})"
        )
    return True, ""


def _check_line_items_sum(e: dict) -> tuple[bool, str]:
    """Verify sum of line item amounts equals subtotal."""
    items = e.get("line_items")
    subtotal = e.get("subtotal")
    if not items or not subtotal:
        return True, ""
    item_list = items.value if hasattr(items, "value") else items
    if not isinstance(item_list, list) or len(item_list) == 0:
        return True, ""
    line_sum = sum(
        i.get("amount", 0) if isinstance(i, dict) else getattr(i, "amount", 0) for i in item_list
    )
    if abs(line_sum - subtotal.value) > 0.01:
        return False, f"sum of line items ({line_sum}) != subtotal ({subtotal.value})"
    return True, ""


_po_totals_check = Invariant(
    name="subtotal_plus_tax_plus_shipping_equals_total",
    fields=["subtotal", "tax", "shipping", "total"],
    fn=_check_po_totals,
)

_line_sum_check = Invariant(
    name="line_items_sum_equals_subtotal",
    fields=["line_items", "subtotal"],
    fn=_check_line_items_sum,
)

PO_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Run detect_layout to find the header or line items table.",
    GapType.TYPE_ERROR: "Re-crop and re-read with ocr. Ensure numeric values are parsed as floats.",
    GapType.FORMAT_ERROR: "Re-read the date region and normalize to ISO YYYY-MM-DD.",
    GapType.UNGROUNDED: "Call the ground tool to trace this value to its bounding box.",
    GapType.LOW_CONFIDENCE: "Re-crop tightly and re-read with ocr. Use vlm if garbled.",
    GapType.INVARIANT_FAILED: "The totals check failed. Re-read subtotal, tax, shipping, and total.",
    GapType.SEMANTIC_FAIL: "Re-crop and re-read with vlm.",
}

PurchaseOrderSkill = Skill(
    name="purchase_order",
    system_prompt=PO_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
    },
    probe_order=[
        ("header", "PO number and date are usually in the top-right or top-center."),
        ("text", "Buyer and vendor names are near the top."),
        ("text", "Ship-to address is usually below the vendor info."),
        ("table", "Line items are in the main body table."),
        ("text", "Subtotal, tax, shipping, and total are near the bottom."),
    ],
    invariants=[_po_totals_check, _line_sum_check],
    failure_actions=PO_FAILURE_ACTIONS,
    known_failures=(
        "POs may not always include shipping. If shipping is absent, "
        "the total check should be subtotal + tax == total."
    ),
    confidence_overrides={
        "po_number": 0.85,
        "total": 0.85,
    },
)
