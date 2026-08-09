"""BankStatementSkill — playbook for bank statement extraction [BLK-106]."""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


BANK_STATEMENT_SYSTEM_PROMPT = """\
You are a bank statement extraction agent. Your job is to fill the
BankStatementTemplate schema by reasoning over the document image and
calling atomic tools.

Principles:
- Call detect_layout first to build a region map. Bank statements have
  a header (bank name, account info) and a transaction table.
- Use OCR for the transaction table; use read_table if available for
  structured tabular data.
- Every value must be grounded to its bounding box.
- Verify that opening_balance + total_credits - total_debits == closing_balance.
- If the balance check fails, re-read the summary section and the last
  transaction's running balance.
- Transaction dates should be in ISO YYYY-MM-DD format.
"""


def _check_balance_continuity(e: dict) -> tuple[bool, str]:
    """Verify opening + credits - debits == closing balance."""
    opening = e.get("opening_balance")
    credits = e.get("total_credits")
    debits = e.get("total_debits")
    closing = e.get("closing_balance")
    if not all([opening, credits, debits, closing]):
        return True, ""
    expected = opening.value + credits.value - debits.value
    if abs(expected - closing.value) > 0.01:
        return False, (
            f"opening ({opening.value}) + credits ({credits.value}) - "
            f"debits ({debits.value}) = {expected} != closing ({closing.value})"
        )
    return True, ""


_balance_check = Invariant(
    name="balance_continuity",
    fields=["opening_balance", "total_credits", "total_debits", "closing_balance"],
    fn=_check_balance_continuity,
)


BANK_STATEMENT_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Run detect_layout to find the header or transaction table region.",
    GapType.TYPE_ERROR: "Re-crop the region and re-read with ocr. Ensure numeric values are parsed as floats.",
    GapType.FORMAT_ERROR: "Re-read the date region and normalize to ISO YYYY-MM-DD format.",
    GapType.UNGROUNDED: "Call the ground tool to trace this value to its bounding box.",
    GapType.LOW_CONFIDENCE: "Re-crop the region tightly and re-read with ocr. Use vlm if OCR is garbled.",
    GapType.INVARIANT_FAILED: "The balance continuity check failed. Re-read the opening balance, total credits, total debits, and closing balance.",
    GapType.SEMANTIC_FAIL: "The semantic check flagged this value. Re-crop and re-read with vlm.",
}

BankStatementSkill = Skill(
    name="bank_statement",
    system_prompt=BANK_STATEMENT_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "header": "ocr",
    },
    probe_order=[
        ("header", "Bank name, account number, and statement period are in the header."),
        ("text", "Account holder name is usually near the top."),
        ("text", "Opening and closing balances are in a summary section."),
        ("table", "Transactions are in the main table — read with ocr or read_table."),
    ],
    invariants=[_balance_check],
    failure_actions=BANK_STATEMENT_FAILURE_ACTIONS,
    known_failures=(
        "Bank statements vary in layout across institutions. "
        "Transaction tables may span multiple pages. "
        "Running balances may not always be present."
    ),
    confidence_overrides={
        "opening_balance": 0.85,
        "closing_balance": 0.85,
        "account_number": 0.85,
    },
)
