"""W2TaxFormSkill — playbook for W-2 tax form extraction [BLK-106]."""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


W2_SYSTEM_PROMPT = """\
You are a W-2 tax form extraction agent. Your job is to fill the
W2TaxFormTemplate schema by reasoning over the document image and
calling atomic tools.

Principles:
- W-2 forms have a fixed IRS layout with numbered boxes.
- Call detect_layout first to identify the form regions.
- Use OCR for text fields. The form is typically high-contrast and OCR-friendly.
- Every value must be grounded.
- Verify that social_security_tax_withheld is approximately 6.2% of
  social_security_wages (within rounding).
- Verify that medicare_tax_withheld is approximately 1.45% of medicare_wages.
"""


def _check_ss_tax(e: dict) -> tuple[bool, str]:
    """Verify SS tax is ~6.2% of SS wages."""
    wages = e.get("social_security_wages")
    tax = e.get("social_security_tax_withheld")
    if not wages or not tax:
        return True, ""
    expected = wages.value * 0.062
    if abs(expected - tax.value) > 0.50:
        return False, (
            f"SS tax ({tax.value}) != 6.2% of SS wages ({wages.value}), expected ~{expected:.2f}"
        )
    return True, ""


def _check_medicare_tax(e: dict) -> tuple[bool, str]:
    """Verify Medicare tax is ~1.45% of Medicare wages."""
    wages = e.get("medicare_wages")
    tax = e.get("medicare_tax_withheld")
    if not wages or not tax:
        return True, ""
    expected = wages.value * 0.0145
    if abs(expected - tax.value) > 0.50:
        return False, (
            f"Medicare tax ({tax.value}) != 1.45% of Medicare wages ({wages.value}), "
            f"expected ~{expected:.2f}"
        )
    return True, ""


_ss_tax_check = Invariant(
    name="ss_tax_is_6.2_percent_of_ss_wages",
    fields=["social_security_wages", "social_security_tax_withheld"],
    fn=_check_ss_tax,
)

_medicare_tax_check = Invariant(
    name="medicare_tax_is_1.45_percent_of_medicare_wages",
    fields=["medicare_wages", "medicare_tax_withheld"],
    fn=_check_medicare_tax,
)

W2_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Run detect_layout to find the form regions. W-2 has a fixed layout.",
    GapType.TYPE_ERROR: "Re-crop the box region and re-read with ocr. Ensure numeric values are floats.",
    GapType.FORMAT_ERROR: "Re-read the SSN/EIN and normalize format.",
    GapType.UNGROUNDED: "Call the ground tool to trace this value to its bounding box.",
    GapType.LOW_CONFIDENCE: "Re-crop the box tightly and re-read with ocr.",
    GapType.INVARIANT_FAILED: "The tax rate check failed. Re-read the wage and tax boxes.",
    GapType.SEMANTIC_FAIL: "Re-crop and re-read with vlm.",
}

W2TaxFormSkill = Skill(
    name="w2_tax_form",
    system_prompt=W2_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "header": "ocr",
    },
    probe_order=[
        ("header", "Employee and employer names, addresses, and IDs are at the top."),
        ("text", "Control number (box a) is usually top-left."),
        ("text", "Box 1 (wages) and box 2 (federal tax) are the key fields."),
        ("text", "Boxes 3-6 (SS and Medicare wages/taxes) are in the middle."),
        ("text", "Boxes 7-11 are less common but should be checked."),
    ],
    invariants=[_ss_tax_check, _medicare_tax_check],
    failure_actions=W2_FAILURE_ACTIONS,
    known_failures=(
        "W-2 forms have a standard IRS layout but may vary slightly by "
        "payroll provider (ADP, Paychex, etc.). SSNs may be masked. "
        "Some boxes may be blank — leave unresolved if not present."
    ),
    confidence_overrides={
        "wages": 0.85,
        "federal_tax_withheld": 0.85,
        "employee_ssn": 0.80,
    },
)
