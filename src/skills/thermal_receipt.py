"""ThermalReceiptSkill — consumer staples thermal receipt extraction [BLK-087].

Geometry-first approach for crumpled, faded, skewed thermal paper.
Financial invariant: subtotal + tax = total.
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are a thermal receipt extraction agent. Your job is to extract fields
from consumer thermal-printed receipts into the ThermalReceiptTemplate.

Principles:
- Thermal receipts are often crumpled, faded, and skewed. ALWAYS run
  auto_orient and deskew before any OCR. Denoise and threshold improve
  OCR on faded prints.
- Geometry first, perception second. Fix the image before reading it.
- Merchant name and address are at the top. Transaction date and time
  are usually right after the header.
- Line items are in the body — use OCR or read_table.
- Subtotal, tax, and total are at the bottom. The validator checks
  subtotal + tax = total.
- If OCR fails on faded text, use VLM with a targeted question about
  the specific field.
"""


_sum_check = Invariant(
    name="subtotal_plus_tax_equals_total",
    fields=["subtotal", "tax_amount", "total_amount"],
    fn=lambda e: (
        abs((e["subtotal"].value + e["tax_amount"].value) - e["total_amount"].value) < 0.01,
        f"subtotal ({e['subtotal'].value}) + tax ({e['tax_amount'].value}) "
        f"!= total ({e['total_amount'].value})",
    ),
)


def _check_line_items_sum(e: dict) -> tuple[bool, str]:
    """Verify sum of line item amounts equals subtotal."""
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
            line_sum += item.get("amount", 0)
        elif hasattr(item, "amount"):
            line_sum += item.amount
    if abs(line_sum - subtotal.value) > 0.01:
        return False, f"sum of line item amounts ({line_sum}) != subtotal ({subtotal.value})"
    return True, ""


_line_items_sum_check = Invariant(
    name="line_items_sum_equals_subtotal",
    fields=["line_items", "subtotal"],
    fn=_check_line_items_sum,
)


def _check_total_positive(e: dict) -> tuple[bool, str]:
    """Verify total_amount is non-negative."""
    total = e.get("total_amount")
    if total is None:
        return True, ""
    val = total.value if hasattr(total, "value") else total
    if val < 0:
        return False, f"total_amount ({val}) cannot be negative"
    return True, ""


_total_positive_check = Invariant(
    name="total_amount_non_negative",
    fields=["total_amount"],
    fn=_check_total_positive,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING: "Run deskew and denoise first, then detect_layout to find the "
    "relevant region. Crop and read with OCR. If faded, use VLM.",
    GapType.LOW_CONFIDENCE: "Re-crop the region, apply threshold to increase contrast, "
    "and re-read with OCR. If still low, use VLM.",
    GapType.INVARIANT_FAILED: "Subtotal + tax != total. Re-crop the totals band at the bottom "
    "of the receipt. Apply threshold for better contrast. Re-read "
    "subtotal, tax, and total with OCR. If garbled, use VLM.",
}


ThermalReceiptSkill = Skill(
    name="thermal_receipt",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "handwriting": "vlm",
        "chart": "vlm",
    },
    probe_order=[
        ("header", "Merchant name and address are at the very top"),
        ("text", "Transaction date and time follow the merchant header"),
        ("table", "Line items are in the body — read with OCR"),
        ("text", "Subtotal, tax, and total are at the bottom"),
    ],
    invariants=[_sum_check, _line_items_sum_check, _total_positive_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Thermal paper fades quickly — apply threshold before OCR. "
        "Receipts are often crumpled — deskew is mandatory. "
        "Tax may be labeled 'Tax', 'Sales Tax', 'VAT', or 'GST'. "
        "Some receipts have no tax (tax-exempt) — tax_amount = 0. "
        "Total may be labeled 'Total' or 'Amount Due'."
    ),
    confidence_overrides={
        "total_amount": 0.90,
        "transaction_date": 0.85,
        "subtotal": 0.85,
        "tax_amount": 0.85,
        "merchant_name": 0.80,
    },
)
