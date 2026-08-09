"""InvoiceSkill — the v1 vertical slice playbook [§3.2, §9].

This is the reusable know-how for invoice extraction. It bundles the system
prompt, tool preferences, probe order, verification rules (invariants),
failure actions, and known failure modes. The agent uses this as advice,
not a fixed pipeline.

Built to be tested against L2's invoice.png. The subtotal + tax == total
cross-check is the verification rule from the vision's success criteria [§7].
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


# ---------------------------------------------------------------------------
# System prompt — frames the agent for invoice extraction [PE]
# ---------------------------------------------------------------------------

INVOICE_SYSTEM_PROMPT = """\
You are an invoice extraction agent. Your job is to fill the InvoiceTemplate
schema by reasoning over the document image and calling atomic tools.

Principles:
- You see the document through tools, not directly. Call detect_layout first
  to build a region map, then crop and read specific regions.
- Every value you extract MUST be grounded: call the ground tool to trace it
  to its bounding box. No grounding, no value.
- Prefer OCR for text regions; prefer VLM for anything OCR struggles with
  (handwriting, stamps, logos, garbled text).
- After extracting numeric fields, the validator will check that
  subtotal + tax == total. If this fails, re-crop the totals band and
  re-read the values.
- If a field is illegible after reasonable effort, leave it unresolved.
  A partial result with explicit gaps is better than a fabricated fill.
"""


# ---------------------------------------------------------------------------
# Invariants — deterministic math checks [§4.1]
# ---------------------------------------------------------------------------

_sum_check = Invariant(
    name="subtotal_plus_tax_equals_total",
    fields=["subtotal", "tax", "total"],
    fn=lambda e: (
        abs((e["subtotal"].value + e["tax"].value) - e["total"].value) < 0.01,
        f"subtotal ({e['subtotal'].value}) + tax ({e['tax'].value}) "
        f"!= total ({e['total'].value})",
    ),
)


def _check_date_range(e: dict) -> tuple[bool, str]:
    """Verify invoice_date <= due_date and due_date within 365 days of invoice_date."""
    from datetime import datetime, timedelta
    try:
        inv_date = datetime.strptime(str(e["invoice_date"].value), "%Y-%m-%d")
        due_date = datetime.strptime(str(e["due_date"].value), "%Y-%m-%d")
        if inv_date > due_date:
            return False, f"invoice_date ({e['invoice_date'].value}) > due_date ({e['due_date'].value})"
        if (due_date - inv_date).days > 365:
            return False, f"due_date ({e['due_date'].value}) is more than 365 days after invoice_date ({e['invoice_date'].value})"
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid date format for date comparison"


_date_range_check = Invariant(
    name="invoice_date_before_due_date_within_365_days",
    fields=["invoice_date", "due_date"],
    fn=_check_date_range,
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
        elif hasattr(item, "__dict__") and "amount" in item.__dict__:
            line_sum += item.__dict__["amount"]
    if abs(line_sum - subtotal.value) > 0.01:
        return False, f"sum of line item amounts ({line_sum}) != subtotal ({subtotal.value})"
    return True, ""


_line_items_sum_check = Invariant(
    name="line_items_sum_equals_subtotal",
    fields=["line_items", "subtotal"],
    fn=_check_line_items_sum,
)


# ---------------------------------------------------------------------------
# Failure actions — GapType -> suggested action [§3.2]
# ---------------------------------------------------------------------------

INVOICE_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING:
        "Run detect_layout to find the relevant region, then crop and "
        "read it with ocr or vlm.",
    GapType.TYPE_ERROR:
        "Re-crop the region for this field and re-read with ocr. "
        "If the value is non-numeric where a number is expected, "
        "ask vlm with a targeted question.",
    GapType.FORMAT_ERROR:
        "Re-read the region and ask vlm to normalize the value to the "
        "required format (e.g. ISO date YYYY-MM-DD).",
    GapType.UNGROUNDED:
        "Call the ground tool to trace this value to its bounding box "
        "in the source image.",
    GapType.LOW_CONFIDENCE:
        "Re-crop the region tightly around this value, deskew if needed, "
        "and re-read with ocr. If still low, ask vlm with a sharp question.",
    GapType.INVARIANT_FAILED:
        "The subtotal + tax == total check failed. Re-crop the totals "
        "band at the bottom of the invoice and re-read subtotal, tax, "
        "and total with ocr. If OCR is garbled, use vlm.",
    GapType.SEMANTIC_FAIL:
        "The semantic check flagged this value as implausible. Re-crop "
        "the region and re-read with vlm, asking a targeted question "
        "about the expected value.",
}


# ---------------------------------------------------------------------------
# The Skill
# ---------------------------------------------------------------------------

InvoiceSkill = Skill(
    name="invoice",
    system_prompt=INVOICE_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "handwriting": "vlm",
        "stamp": "vlm",
        "logo": "vlm",
        "chart": "vlm",
    },
    probe_order=[
        ("header", "Invoice number and date are usually in the top-right "
                   "or top-center header region."),
        ("text", "Vendor name is typically near the top, possibly with a "
                 "logo."),
        ("table", "Line items are in the main body table — read with ocr "
                  "or read_table."),
        ("text", "Subtotal, tax, and total are usually in a totals band "
                 "near the bottom."),
    ],
    invariants=[_sum_check, _date_range_check, _line_items_sum_check],
    failure_actions=INVOICE_FAILURE_ACTIONS,
    known_failures=(
        "Thermal-printed receipts may need deskew before ocr. "
        "Tax fields are sometimes labeled 'Tax @' or 'Sales Tax' — "
        "ocr may garble the label; use vlm if the label is unclear. "
        "Subtotal may be misread as 'Sub Total' — ensure the total field "
        "captures the grand total, not the subtotal (L2 lesson)."
    ),
    confidence_overrides={
        # Invoice number and total are high-stakes; require higher confidence.
        "invoice_number": 0.85,
        "total": 0.85,
        "vendor": 0.80,
        "line_items": 0.80,
    },
)
