"""MetallurgicalAssaySkill — metallurgical assay certificate extraction [BLK-087].

Degraded scans from remote sites with dot-matrix print. OCR fallback
to VLM for unreadable sections. Composition values within spec range.
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are a metallurgical assay extraction agent. Your job is to extract
composition data and certificate metadata from metallurgical assay
certificates into the MetallurgicalAssayTemplate.

Principles:
- Assay certificates from remote sites are often degraded scans with
  dot-matrix print. Apply deskew and denoise before OCR.
- If OCR fails on dot-matrix text, route to VLM directly.
- Composition tables have element, value, spec_min, spec_max columns.
  Use read_table for structured extraction.
- Each composition value must be within [spec_min, spec_max].
- The validator checks that all values are within spec range.
- Heat number and certificate number are critical for traceability.
"""


def _check_composition_in_spec(e: dict) -> tuple[bool, str]:
    """Verify all composition values are within spec range."""
    elements = e.get("composition_elements")
    values = e.get("composition_values")
    spec_mins = e.get("spec_min")
    spec_maxs = e.get("spec_max")

    if not all([elements, values, spec_mins, spec_maxs]):
        return True, ""  # Not all fields present — skip

    elem_list = elements.value if hasattr(elements, "value") else elements
    val_list = values.value if hasattr(values, "value") else values
    min_list = spec_mins.value if hasattr(spec_mins, "value") else spec_mins
    max_list = spec_maxs.value if hasattr(spec_maxs, "value") else spec_maxs

    if not isinstance(val_list, list) or not isinstance(min_list, list) or not isinstance(max_list, list):
        return True, ""

    for i, (val, smin, smax) in enumerate(zip(val_list, min_list, max_list)):
        try:
            v, lo, hi = float(val), float(smin), float(smax)
            if v < lo or v > hi:
                return False, f"Element {i}: value {v} outside spec range [{lo}, {hi}]"
        except (ValueError, TypeError):
            continue
    return True, ""


_spec_check = Invariant(
    name="composition_within_spec",
    fields=["composition_elements", "composition_values", "spec_min", "spec_max"],
    fn=_check_composition_in_spec,
)


def _check_composition_sum(e: dict) -> tuple[bool, str]:
    """Verify sum of all composition values = 100% (±0.5%)."""
    values = e.get("composition_values")
    if not values:
        return True, ""
    val_list = values.value if hasattr(values, "value") else values
    if not isinstance(val_list, list) or len(val_list) == 0:
        return True, ""
    try:
        total = sum(float(v) for v in val_list)
        if abs(total - 100.0) > 0.5:
            return False, f"sum of composition values ({total}) != 100% (±0.5%)"
        return True, ""
    except (ValueError, TypeError):
        return True, ""


_composition_sum_check = Invariant(
    name="composition_values_sum_to_100_percent",
    fields=["composition_values"],
    fn=_check_composition_sum,
)


def _check_density_positive(e: dict) -> tuple[bool, str]:
    """Verify density is positive if provided."""
    density = e.get("density")
    if density is None:
        return True, ""
    val = density.value if hasattr(density, "value") else density
    if val <= 0:
        return False, f"density ({val}) must be positive"
    return True, ""


_density_check = Invariant(
    name="density_positive",
    fields=["density"],
    fn=_check_density_positive,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING:
        "Run deskew and denoise first, then detect_layout. For dot-matrix "
        "text, use VLM if OCR fails. Use read_table for composition tables.",
    GapType.INVARIANT_FAILED:
        "Composition value outside spec range. Re-crop the composition "
        "table and re-read with read_table. If OCR garbles numbers, "
        "use VLM to extract specific values.",
    GapType.LOW_CONFIDENCE:
        "Dot-matrix print is hard for OCR. Apply deskew, denoise, and "
        "threshold. If still low confidence, use VLM.",
}


MetallurgicalAssaySkill = Skill(
    name="metallurgical_assay",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "read_table",
        "handwriting": "vlm",
        "figure": "vlm",
    },
    probe_order=[
        ("header", "Certificate number, material grade, and heat number are in the header"),
        ("table", "Composition table with elements, values, spec ranges — use read_table"),
        ("text", "Test date is usually near the header or footer"),
        ("text", "Inspector company is in the footer"),
    ],
    invariants=[_spec_check, _composition_sum_check, _density_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Dot-matrix print: OCR often fails — have VLM ready as fallback. "
        "Degraded scans from remote sites: always deskew and denoise first. "
        "Composition tables may span multiple pages. "
        "Spec ranges may use '<' and '>' instead of min/max columns."
    ),
    confidence_overrides={
        "certificate_number": 0.95,
        "heat_number": 0.95,
        "material_grade": 0.90,
    },
)
