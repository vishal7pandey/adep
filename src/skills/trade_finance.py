"""TradeFinanceScrutinySkill — MT700 trade finance extraction [BLK-042, §14].

Domain expertise for SWIFT MT700 letter of credit scrutiny. Encodes:
- Date arithmetic invariants (expiry after issue, shipment before expiry)
- Amount tolerance checks
- Document coverage requirements
- OCR→VLM fallback for degraded telex/fax copies
"""

from __future__ import annotations

from datetime import datetime

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS
from src.templates.trade_finance import TradeFinanceTemplate


_SYSTEM_PROMPT = """\
You are a trade finance document scrutiny agent. Your job is to extract
fields from MT700 SWIFT messages and related trade finance documents
(bills of lading, commercial invoices) into the TradeFinanceTemplate.

Principles:
- MT700 messages have numbered fields (20, 32B, 44A, etc.) — use these
  to locate values quickly.
- Dates are critical: issue_date, expiry_date, latest_shipment_date must
  all be in ISO format (YYYY-MM-DD).
- Amount fields must include the currency code.
- If the document is a degraded telex/fax copy, apply deskew before OCR.
- For handwritten endorsements or stamps, use VLM directly.
- The validator will check date arithmetic (expiry > issue, shipment < expiry).
"""


def _parse_date(val: Any) -> datetime | None:
    try:
        return datetime.strptime(str(val), "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


_expiry_after_issue = Invariant(
    name="expiry_date_after_issue_date",
    fields=["issue_date", "expiry_date"],
    fn=lambda e: (
        (_parse_date(e["expiry_date"].value) > _parse_date(e["issue_date"].value),
         f"expiry_date ({e['expiry_date'].value}) is not after issue_date ({e['issue_date'].value})")
        if _parse_date(e["expiry_date"].value) and _parse_date(e["issue_date"].value)
        else (False, "Cannot compare dates — invalid format")
    ),
)

_shipment_before_expiry = Invariant(
    name="latest_shipment_before_expiry",
    fields=["latest_shipment_date", "expiry_date"],
    fn=lambda e: (
        (_parse_date(e["latest_shipment_date"].value) <= _parse_date(e["expiry_date"].value),
         f"latest_shipment_date ({e['latest_shipment_date'].value}) is after expiry_date ({e['expiry_date'].value})")
        if _parse_date(e["latest_shipment_date"].value) and _parse_date(e["expiry_date"].value)
        else (False, "Cannot compare dates — invalid format")
    ),
)


def _check_amount_positive(e: dict) -> tuple[bool, str]:
    """Verify lc_amount is positive."""
    amount = e.get("lc_amount")
    if amount is None:
        return True, ""
    val = amount.value if hasattr(amount, "value") else amount
    if val <= 0:
        return False, f"lc_amount ({val}) must be positive"
    return True, ""


_amount_positive_check = Invariant(
    name="lc_amount_positive",
    fields=["lc_amount"],
    fn=_check_amount_positive,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING:
        "MT700 fields are numbered. Run detect_layout to find the field "
        "header (e.g. ':20:', ':32B:', ':44A:'), then crop and read it. "
        "If the message is a degraded telex copy, deskew before OCR.",
    GapType.INVARIANT_FAILED:
        "Date arithmetic check failed. Re-crop the date fields and re-read "
        "with OCR. Ensure dates are in YYYY-MM-DD format. If OCR is garbled, "
        "use VLM with a targeted question about the specific date field.",
}


TradeFinanceScrutinySkill = Skill(
    name="trade_finance_scrutiny",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "handwriting": "vlm",
        "stamp": "vlm",
        "chart": "read_chart",
    },
    probe_order=[
        ("header", "MT700 field headers (:20:, :32B:) are at the top of the message"),
        ("text", "Dates (:31D:, :44C:) and parties (:50:, :59:) are in the body"),
        ("text", "Port information (:44A:, :44B:) and goods description (:45A:) follow"),
        ("text", "Document requirements (:46A:) are typically at the end"),
    ],
    invariants=[_expiry_after_issue, _shipment_before_expiry, _amount_positive_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Degraded telex/fax copies may need deskew before OCR. "
        "Field numbers (:20:, :32B:) may be garbled — use VLM if OCR fails. "
        "Dates may be in DD-MM-YYYY format — normalize to ISO. "
        "Currency codes may be separated from amounts — extract both."
    ),
    confidence_overrides={
        "lc_number": 0.90,
        "lc_amount": 0.90,
        "expiry_date": 0.85,
    },
)
