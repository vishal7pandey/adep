"""UtilityBillSkill — utility bill extraction with chart integration [BLK-042, §14].

Domain expertise for utility bills (electricity, gas, water). Encodes:
- read_chart integration for 12-month consumption history
- Usage comparison invariants (current vs previous)
- Amount due and due date extraction
- Geometry-first probe for thermal-printed bills
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS
from src.templates.utility_bill import UtilityBillTemplate


_SYSTEM_PROMPT = """\
You are a utility bill extraction agent. Your job is to extract fields
from utility bills (electricity, gas, water) into the UtilityBillTemplate.

Principles:
- Account number and service address are usually in the header.
- Billing period dates define the current usage period.
- Current and previous usage values may be in a table or chart.
- The consumption history chart should be read with read_chart (VLM-only).
- The validator will check that amount_due and due_date are present.
- If the bill is a thermal print, apply deskew before OCR.
- For handwritten meter readings, use VLM directly.
"""


_usage_decrease_check = Invariant(
    name="usage_not_negative",
    fields=["current_usage", "previous_usage"],
    fn=lambda e: (
        e["current_usage"].value >= 0 and e["previous_usage"].value >= 0,
        "Usage values cannot be negative",
    ),
)


def _check_billing_period(e: dict) -> tuple[bool, str]:
    """Verify billing period is <= 45 days."""
    from datetime import datetime

    try:
        start = datetime.strptime(str(e["billing_period_start"].value), "%Y-%m-%d")
        end = datetime.strptime(str(e["billing_period_end"].value), "%Y-%m-%d")
        delta = (end - start).days
        if delta < 0:
            return (
                False,
                f"billing_period_start ({e['billing_period_start'].value}) > billing_period_end ({e['billing_period_end'].value})",
            )
        if delta > 45:
            return False, f"billing period ({delta} days) exceeds 45 days"
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid date format for billing period check"


_billing_period_check = Invariant(
    name="billing_period_within_45_days",
    fields=["billing_period_start", "billing_period_end"],
    fn=_check_billing_period,
)


def _check_amount_due_positive(e: dict) -> tuple[bool, str]:
    """Verify amount_due is non-negative."""
    amount = e["amount_due"].value
    if amount < 0:
        return False, f"amount_due ({amount}) cannot be negative"
    return True, ""


_amount_check = Invariant(
    name="amount_due_non_negative",
    fields=["amount_due"],
    fn=_check_amount_due_positive,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING: "Run detect_layout to find the relevant region. Account numbers "
    "are in the header. Usage values may be in a table or chart — "
    "use read_chart for the consumption history graph.",
    GapType.LOW_CONFIDENCE: "If OCR confidence is low on numeric fields, crop the region, "
    "deskew, and re-read. For chart-based consumption history, "
    "use read_chart (VLM interprets chart geometry directly).",
}


UtilityBillSkill = Skill(
    name="utility_bill",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "chart": "read_chart",
        "handwriting": "vlm",
        "figure": "read_chart",
    },
    probe_order=[
        ("header", "Account number, service address, and billing dates are in the header"),
        ("text", "Current and previous usage values are usually near the meter details"),
        ("text", "Amount due and due date are typically at the bottom right"),
        ("chart", "Consumption history chart — use read_chart to extract 12-month data"),
    ],
    invariants=[_usage_decrease_check, _billing_period_check, _amount_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Thermal-printed bills may need deskew before OCR. "
        "Consumption history is often a bar chart — use read_chart, not OCR. "
        "Meter readings may be handwritten — use VLM. "
        "Usage units vary (kWh, m³, gallons) — extract the unit field."
    ),
    confidence_overrides={
        "account_number": 0.90,
        "amount_due": 0.90,
        "current_usage": 0.85,
        "previous_usage": 0.85,
        "consumption_history": 0.75,
    },
)
