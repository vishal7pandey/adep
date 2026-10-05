"""CommercialLeaseSkill — commercial lease abstraction [BLK-087].

60+ page leases with context dilution. Field-driven working set with
hierarchical state for multi-page navigation.
"""

from __future__ import annotations

from datetime import datetime

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are a commercial lease abstraction agent. Your job is to extract
key terms from commercial lease documents into the CommercialLeaseTemplate.

Principles:
- Leases are long (60+ pages). Use locate to find specific clauses by
  keyword (e.g. "commencement date", "base rent", "security deposit").
- Crop specific clause sections rather than reading entire pages.
- Dates must be in ISO format (YYYY-MM-DD).
- The validator checks that expiration_date = commencement_date + lease_term_months.
- Rent escalation percentage may be in a separate clause from base rent.
- CAM fees, termination clauses, and renewal options are often in
  later sections — use locate to find them.
"""


def _check_lease_term(e: dict) -> tuple[bool, str]:
    """Verify expiration_date ≈ commencement_date + lease_term_months."""
    try:
        comm = datetime.strptime(str(e["commencement_date"].value), "%Y-%m-%d")
        exp = datetime.strptime(str(e["expiration_date"].value), "%Y-%m-%d")
        months = e["lease_term_months"].value
        # Approximate: add months to commencement, compare to expiration
        from dateutil.relativedelta import relativedelta

        expected_exp = comm + relativedelta(months=months)
        diff_days = abs((exp - expected_exp).days)
        if diff_days > 31:  # Allow ~1 month tolerance
            return False, (
                f"expiration_date ({e['expiration_date'].value}) != "
                f"commencement_date + {months} months (expected ~{expected_exp.date()})"
            )
        return True, ""
    except (ValueError, TypeError):
        # Fallback without dateutil
        try:
            comm = datetime.strptime(str(e["commencement_date"].value), "%Y-%m-%d")
            exp = datetime.strptime(str(e["expiration_date"].value), "%Y-%m-%d")
            months = e["lease_term_months"].value
            expected_days = months * 30
            actual_days = (exp - comm).days
            if abs(actual_days - expected_days) > 31:
                return False, f"Lease term mismatch: {months} months vs {actual_days} days"
            return True, ""
        except (ValueError, TypeError):
            return False, "Cannot compare dates — invalid format"


_lease_term_check = Invariant(
    name="expiration_equals_commencement_plus_term",
    fields=["commencement_date", "expiration_date", "lease_term_months"],
    fn=_check_lease_term,
)


def _check_escalation_rate(e: dict) -> tuple[bool, str]:
    """Verify rent_escalation_percent is between 0 and 20."""
    esc = e.get("rent_escalation_percent")
    if esc is None:
        return True, ""
    val = esc.value if hasattr(esc, "value") else esc
    if val < 0 or val > 20:
        return False, f"rent_escalation_percent ({val}) outside valid range [0, 20]"
    return True, ""


_escalation_check = Invariant(
    name="rent_escalation_within_bounds",
    fields=["rent_escalation_percent"],
    fn=_check_escalation_rate,
)


def _check_cam_ratio(e: dict) -> tuple[bool, str]:
    """Verify CAM charges <= 30% of base rent (rule of thumb)."""
    cam = e.get("cam_charges_annual")
    rent = e.get("base_rent_monthly")
    if cam is None or rent is None:
        return True, ""
    cam_val = cam.value if hasattr(cam, "value") else cam
    rent_val = rent.value if hasattr(rent, "value") else rent
    annual_rent = rent_val * 12
    if annual_rent > 0 and cam_val / annual_rent > 0.30:
        return False, f"CAM charges ({cam_val}) exceed 30% of annual rent ({annual_rent})"
    return True, ""


_cam_check = Invariant(
    name="cam_charges_within_30_percent_of_rent",
    fields=["cam_charges_annual", "base_rent_monthly"],
    fn=_check_cam_ratio,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING: "Use locate with keywords: 'landlord', 'tenant', 'premises', "
    "'commencement', 'base rent', 'security deposit', 'renewal', "
    "'termination'. Crop the matching clause and read with OCR.",
    GapType.INVARIANT_FAILED: "Lease term date arithmetic failed. Re-crop the commencement "
    "date, expiration date, and lease term sections. Verify all "
    "dates are in YYYY-MM-DD format.",
}


CommercialLeaseSkill = Skill(
    name="commercial_lease",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "handwriting": "vlm",
        "figure": "vlm",
    },
    probe_order=[
        ("header", "Landlord, tenant, and premises address are in the first few pages"),
        ("text", "Use locate to find 'commencement date' and 'lease term' clauses"),
        ("text", "Base rent and escalation are usually in the rent section"),
        ("text", "Security deposit, renewal, and termination are in later sections"),
    ],
    invariants=[_lease_term_check, _escalation_check, _cam_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "60+ page leases: always use locate, never read full pages. "
        "Context dilution: crop specific clauses, not entire sections. "
        "Dates may be written as 'January 1, 2026' — normalize to ISO. "
        "CAM fees may be in a separate exhibit or schedule."
    ),
    confidence_overrides={
        "commencement_date": 0.90,
        "expiration_date": 0.90,
        "base_rent_monthly": 0.90,
        "security_deposit": 0.85,
    },
)
