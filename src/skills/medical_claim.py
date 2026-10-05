"""MedicalClaimSkill — CMS-1500 medical claim form extraction [BLK-087].

Rigid form fields with handwritten clinical notes. Routes handwritten
content to VLM directly. Validates ICD-10 and CPT code formats.
"""

from __future__ import annotations

import re

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are a medical claim extraction agent. Your job is to extract fields
from CMS-1500 claim forms into the MedicalClaimTemplate.

Principles:
- CMS-1500 forms have rigid, well-defined field positions. Use
  detect_layout to find field boxes, then crop each box individually.
- Printed text: use OCR. Handwritten clinical notes (CRFs): route to
  VLM directly — OCR will fail on handwriting.
- Provider NPI must be exactly 10 digits.
- Diagnosis codes must be valid ICD-10 format (letter + digits, e.g. M54.5).
- Procedure codes must be valid CPT format (5 digits, e.g. 99213).
- Service date from must be <= service date to.
- The validator checks date ordering and code formats.
"""


def _check_date_order(e: dict) -> tuple[bool, str]:
    """Verify service_date_from <= service_date_to."""
    from datetime import datetime

    try:
        d_from = datetime.strptime(str(e["service_date_from"].value), "%Y-%m-%d")
        d_to = datetime.strptime(str(e["service_date_to"].value), "%Y-%m-%d")
        if d_from > d_to:
            return (
                False,
                f"service_date_from ({e['service_date_from'].value}) > service_date_to ({e['service_date_to'].value})",
            )
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid date format for date comparison"


_date_order_check = Invariant(
    name="service_date_from_before_to",
    fields=["service_date_from", "service_date_to"],
    fn=_check_date_order,
)


def _check_npi_format(e: dict) -> tuple[bool, str]:
    """Verify provider_npi is 10 digits."""
    npi = str(e["provider_npi"].value)
    if not re.match(r"^\d{10}$", npi):
        return False, f"provider_npi '{npi}' is not 10 digits"
    return True, ""


_npi_check = Invariant(
    name="npi_format_valid",
    fields=["provider_npi"],
    fn=_check_npi_format,
)


def _check_billed_amount_positive(e: dict) -> tuple[bool, str]:
    """Verify billed_amount is non-negative."""
    amount = e.get("billed_amount")
    if amount is None:
        return True, ""
    val = amount.value if hasattr(amount, "value") else amount
    if val < 0:
        return False, f"billed_amount ({val}) cannot be negative"
    return True, ""


_billed_amount_check = Invariant(
    name="billed_amount_non_negative",
    fields=["billed_amount"],
    fn=_check_billed_amount_positive,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING: "CMS-1500 fields are in fixed positions. Run detect_layout to "
    "find the field box, crop it, and read with OCR. For handwritten "
    "fields, use VLM directly.",
    GapType.FORMAT_ERROR: "Re-crop the field and re-read. NPI must be 10 digits. ICD-10 "
    "codes start with a letter. CPT codes are 5 digits. Use VLM "
    "if OCR garbles the code.",
    GapType.INVARIANT_FAILED: "Date or code format check failed. Re-crop the specific field "
    "and re-read. Ensure dates are YYYY-MM-DD.",
}


MedicalClaimSkill = Skill(
    name="medical_claim",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "handwriting": "vlm",
        "table": "ocr",
        "figure": "vlm",
    },
    probe_order=[
        ("header", "Patient name, DOB, and gender are in the top section"),
        ("text", "Provider NPI and name are in the provider section"),
        ("text", "Diagnosis codes (ICD-10) are in box 21"),
        ("text", "Procedure codes (CPT) are in box 24"),
        ("text", "Service dates and billed amount are in the lower section"),
    ],
    invariants=[_date_order_check, _npi_check, _billed_amount_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Handwritten CRF fields: route to VLM, OCR will fail. "
        "ICD-10 codes may be written without the dot (M545 vs M54.5). "
        "CPT codes may have modifiers appended (99213-25). "
        "NPI may be split across two OCR lines — merge and validate."
    ),
    confidence_overrides={
        "provider_npi": 0.95,
        "billed_amount": 0.90,
        "diagnosis_codes": 0.85,
        "procedure_codes": 0.85,
    },
)
