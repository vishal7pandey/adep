"""ComplianceAuditSkill — SOC 2 / OSPAR compliance audit extraction [BLK-087].

Handles 100+ page compliance documents with hierarchical navigation.
Extracts control statuses, encryption confirmations, and audit metrics.
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are a compliance audit extraction agent. Your job is to extract
control statuses and audit metrics from SOC 2 / OSPAR compliance
reports into the ComplianceAuditTemplate.

Principles:
- Compliance documents are long (100+ pages). Use locate to find
  relevant sections by keyword (e.g. "encryption", "access control").
- Crop specific sections rather than reading entire pages.
- Boolean fields (encryption_at_rest, etc.) require explicit confirmation
  in the text (e.g. "AES-256 is used for encryption at rest").
- audit_log_retention must be a number in days (≥ 365 for SOC 2).
- control_count_passed is derived from counting passed controls.
- Use VLM for diagrams or architecture screenshots that show security
  controls visually.
"""


_retention_check = Invariant(
    name="audit_log_retention_minimum",
    fields=["audit_log_retention"],
    fn=lambda e: (
        e["audit_log_retention"].value >= 365,
        f"audit_log_retention ({e['audit_log_retention'].value}) < 365 days minimum",
    ),
)


def _check_control_counts(e: dict) -> tuple[bool, str]:
    """Verify control_count_passed <= control_count_total."""
    passed = e.get("control_count_passed")
    total = e.get("control_count_total")
    if passed is None or total is None:
        return True, ""
    p_val = passed.value if hasattr(passed, "value") else passed
    t_val = total.value if hasattr(total, "value") else total
    if p_val > t_val:
        return False, f"control_count_passed ({p_val}) > control_count_total ({t_val})"
    return True, ""


_control_count_check = Invariant(
    name="passed_controls_leq_total",
    fields=["control_count_passed", "control_count_total"],
    fn=_check_control_counts,
)


def _check_encryption_consistency(e: dict) -> tuple[bool, str]:
    """Verify encryption_at_rest and encryption_in_transit are both set."""
    rest = e.get("encryption_at_rest")
    transit = e.get("encryption_in_transit")
    if rest is None or transit is None:
        return True, ""
    rest_val = rest.value if hasattr(rest, "value") else rest
    transit_val = transit.value if hasattr(transit, "value") else transit
    if not isinstance(rest_val, bool) or not isinstance(transit_val, bool):
        return False, "Encryption fields must be boolean"
    return True, ""


_encryption_check = Invariant(
    name="encryption_fields_are_boolean",
    fields=["encryption_at_rest", "encryption_in_transit"],
    fn=_check_encryption_consistency,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING:
        "Use locate with keywords like 'encryption', 'access control', "
        "'penetration testing', 'data isolation', 'audit log'. Crop the "
        "matching section and read with OCR.",
    GapType.FORMAT_ERROR:
        "Re-crop the section and re-read. Boolean fields need explicit "
        "confirmation text. audit_log_retention must be an integer in days.",
    GapType.INVARIANT_FAILED:
        "Retention period check failed. Re-read the audit log retention "
        "section. SOC 2 requires ≥ 365 days.",
}


ComplianceAuditSkill = Skill(
    name="compliance_audit",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "ocr",
        "figure": "vlm",
        "chart": "vlm",
    },
    probe_order=[
        ("header", "Report title, auditor, and date are in the header"),
        ("text", "Executive summary has high-level compliance status"),
        ("text", "Use locate to find specific control sections by keyword"),
        ("text", "Audit log retention is usually in the logging section"),
    ],
    invariants=[_retention_check, _control_count_check, _encryption_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "100+ page documents: use locate, never read full pages. "
        "Boolean fields: look for explicit 'yes'/'confirmed'/'implemented'. "
        "Controls may be in tables with pass/fail columns. "
        "OSPAR outsourcing may be in an appendix."
    ),
    confidence_overrides={
        "encryption_at_rest": 0.95,
        "encryption_in_transit": 0.95,
        "audit_log_retention": 0.90,
        "control_count_total": 0.85,
    },
)
