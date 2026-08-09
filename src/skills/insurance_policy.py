"""InsurancePolicySkill — playbook for insurance declaration page extraction [BLK-106]."""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill


INSURANCE_POLICY_SYSTEM_PROMPT = """\
You are an insurance policy declaration page extraction agent. Your job
is to fill the InsurancePolicyTemplate schema by reasoning over the
document image and calling atomic tools.

Principles:
- Declaration pages are multi-page documents with a summary section and
  itemized coverage lines.
- Call detect_layout first to build a region map across all pages.
- Use OCR for text fields; use read_table for the coverage table.
- Every value must be grounded.
- Verify that the sum of individual coverage premiums equals total_premium.
- Policy period dates should be in ISO YYYY-MM-DD format.
"""


def _check_premium_sum(e: dict) -> tuple[bool, str]:
    """Verify sum of coverage premiums equals total premium."""
    coverages = e.get("coverages")
    total_premium = e.get("total_premium")
    if not coverages or not total_premium:
        return True, ""
    cov_list = coverages.value if hasattr(coverages, "value") else coverages
    if not isinstance(cov_list, list) or len(cov_list) == 0:
        return True, ""
    premium_sum = sum(
        c.get("premium", 0) if isinstance(c, dict) else getattr(c, "premium", 0)
        for c in cov_list
    )
    if abs(premium_sum - total_premium.value) > 0.50:
        return False, (
            f"sum of coverage premiums ({premium_sum}) != "
            f"total_premium ({total_premium.value})"
        )
    return True, ""


_premium_check = Invariant(
    name="coverage_premiums_sum_equals_total",
    fields=["coverages", "total_premium"],
    fn=_check_premium_sum,
)

INSURANCE_POLICY_FAILURE_ACTIONS: dict[GapType, str] = {
    GapType.MISSING: "Run detect_layout to find the summary or coverage table region.",
    GapType.TYPE_ERROR: "Re-crop and re-read with ocr. Ensure premium amounts are floats.",
    GapType.FORMAT_ERROR: "Re-read the date and normalize to ISO YYYY-MM-DD.",
    GapType.UNGROUNDED: "Call the ground tool to trace this value to its bounding box.",
    GapType.LOW_CONFIDENCE: "Re-crop tightly and re-read with ocr. Use vlm for garbled text.",
    GapType.INVARIANT_FAILED: "The premium sum check failed. Re-read coverage premiums and total premium.",
    GapType.SEMANTIC_FAIL: "Re-crop and re-read with vlm.",
}

InsurancePolicySkill = Skill(
    name="insurance_policy",
    system_prompt=INSURANCE_POLICY_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
    },
    probe_order=[
        ("header", "Policy number, insurance company, and policy period are at the top."),
        ("text", "Insured name and address are usually in the first section."),
        ("text", "Agent name may be in a sidebar or footer."),
        ("table", "Coverage lines are in a table with type, limit, and premium columns."),
        ("text", "Total premium is usually at the bottom of the coverage section."),
    ],
    invariants=[_premium_check],
    failure_actions=INSURANCE_POLICY_FAILURE_ACTIONS,
    known_failures=(
        "Declaration pages can be 2-5 pages. Coverage tables may span "
        "multiple pages. Some policies include endorsements that modify "
        "coverage — focus on the main declaration page."
    ),
    confidence_overrides={
        "policy_number": 0.85,
        "total_premium": 0.85,
    },
)
