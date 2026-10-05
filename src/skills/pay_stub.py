"""PayStubSkill — playbook for pay stub extraction [BLK-106]."""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


PAY_STUB_SYSTEM_PROMPT = """\
You are a pay stub extraction agent. Your job is to fill the
PayStubTemplate schema by reasoning over the document image and
calling atomic tools.

Principles:
- Call detect_layout first. Pay stubs have a header (employee/employer info,
  pay dates) and a table of earnings, taxes, and deductions.
- Use OCR for text; use read_table for the deductions table.
- Every value must be grounded.
- Verify that gross_pay - sum of all deductions and taxes == net_pay.
- Verify that YTD figures are consistent with current period amounts.
"""


def _check_net_pay(e: dict) -> tuple[bool, str]:
    """Verify gross - taxes - deductions == net pay."""
    gross = e.get("gross_pay")
    net = e.get("net_pay")
    fed_tax = e.get("federal_tax")
    state_tax = e.get("state_tax")
    ss = e.get("social_security")
    medicare = e.get("medicare")
    deductions = e.get("deductions")
    if not gross or not net:
        return True, ""
    total_deductions = 0.0
    for field in [fed_tax, state_tax, ss, medicare]:
        if field:
            total_deductions += field.value
    if deductions:
        ded_list = deductions.value if hasattr(deductions, "value") else deductions
        if isinstance(ded_list, list):
            total_deductions += sum(
                d.get("amount", 0) if isinstance(d, dict) else getattr(d, "amount", 0)
                for d in ded_list
            )
    expected = gross.value - total_deductions
    if abs(expected - net.value) > 0.50:
        return False, (
            f"gross ({gross.value}) - deductions ({total_deductions}) = "
            f"{expected:.2f} != net ({net.value})"
        )
    return True, ""


_net_pay_check = Invariant(
    name="gross_minus_deductions_equals_net",
    fields=[
        "gross_pay",
        "net_pay",
        "federal_tax",
        "state_tax",
        "social_security",
        "medicare",
        "deductions",
    ],
    fn=_check_net_pay,
)

PAY_STUB_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Run detect_layout to find the header or earnings/deductions sections.",
    GapType.TYPE_ERROR: "Re-crop and re-read with ocr. Ensure amounts are floats.",
    GapType.FORMAT_ERROR: "Re-read the date and normalize to ISO YYYY-MM-DD.",
    GapType.UNGROUNDED: "Call the ground tool to trace this value to its bounding box.",
    GapType.LOW_CONFIDENCE: "Re-crop tightly and re-read with ocr.",
    GapType.INVARIANT_FAILED: "The net pay check failed. Re-read gross, taxes, deductions, and net pay.",
    GapType.SEMANTIC_FAIL: "Re-crop and re-read with vlm.",
}

PayStubSkill = Skill(
    name="pay_stub",
    system_prompt=PAY_STUB_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
    },
    probe_order=[
        ("header", "Employee name, employer name, and pay dates are at the top."),
        ("text", "Gross pay and net pay are usually prominently displayed."),
        ("text", "Federal, state, SS, and Medicare taxes are in a taxes section."),
        ("table", "Deductions (401k, health, etc.) are in a table."),
        ("text", "YTD figures are usually at the bottom or in a summary column."),
    ],
    invariants=[_net_pay_check],
    failure_actions=PAY_STUB_FAILURE_ACTIONS,
    known_failures=(
        "Pay stubs vary widely across payroll providers. "
        "Some show year-to-date in a separate column. "
        "Deductions may be pre-tax or post-tax."
    ),
    confidence_overrides={
        "gross_pay": 0.85,
        "net_pay": 0.85,
    },
)
