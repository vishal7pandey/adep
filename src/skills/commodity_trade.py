"""CommodityTradeSkill — commodity trade reconciliation [BLK-087].

Volumetric reconciliation across multiple documents (assay, BoL, LC).
Temperature corrections and cross-document matching.
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are a commodity trade reconciliation agent. Your job is to extract
and cross-check fields from assay certificates, bills of lading, and
letter of credit documents into the CommodityTradeTemplate.

Principles:
- Multiple documents are involved: assay certificate, bill of lading,
  and LC. Use detect_layout on each, then extract fields.
- Volumetric reconciliation: loaded_volume_barrels must be within ±5%
  of the LC tolerance amount.
- Vessel name, loading_port, and discharge_port must match across all
  documents. Use cross_check to verify.
- Temperature correction: volume_at_15c is derived from observed volume
  and temperature. This is a deterministic calculation, not LLM.
- API gravity is a key quality parameter — extract precisely.
- Use read_table for assay composition tables.
"""


def _check_volume_tolerance(e: dict) -> tuple[bool, str]:
    """Verify loaded volume is within ±5% of LC amount."""
    loaded = e["loaded_volume_barrels"].value
    lc_amount = e.get("lc_amount")
    if lc_amount is None:
        return True, ""  # No LC amount to compare — skip
    lc_val = lc_amount.value if hasattr(lc_amount, "value") else lc_amount
    if lc_val == 0:
        return True, ""
    deviation = abs(loaded - lc_val) / lc_val
    if deviation > 0.05:
        return (
            False,
            f"loaded_volume ({loaded}) deviates {deviation:.1%} from LC amount ({lc_val}) — exceeds ±5%",
        )
    return True, ""


_volume_check = Invariant(
    name="volume_within_lc_tolerance",
    fields=["loaded_volume_barrels"],
    fn=_check_volume_tolerance,
)


def _check_total_value(e: dict) -> tuple[bool, str]:
    """Verify total_value = volume × unit_price."""
    volume = e.get("loaded_volume_barrels")
    price = e.get("unit_price")
    total = e.get("total_value")
    if not all([volume, price, total]):
        return True, ""
    vol_val = volume.value if hasattr(volume, "value") else volume
    price_val = price.value if hasattr(price, "value") else price
    total_val = total.value if hasattr(total, "value") else total
    if abs((vol_val * price_val) - total_val) > 0.01:
        return False, f"volume ({vol_val}) × unit_price ({price_val}) != total_value ({total_val})"
    return True, ""


_total_value_check = Invariant(
    name="total_value_equals_volume_times_price",
    fields=["loaded_volume_barrels", "unit_price", "total_value"],
    fn=_check_total_value,
)


def _check_delivery_after_trade(e: dict) -> tuple[bool, str]:
    """Verify delivery_date > trade_date."""
    from datetime import datetime

    trade = e.get("trade_date")
    delivery = e.get("delivery_date")
    if not trade or not delivery:
        return True, ""
    try:
        t = datetime.strptime(str(trade.value), "%Y-%m-%d")
        d = datetime.strptime(str(delivery.value), "%Y-%m-%d")
        if d <= t:
            return (
                False,
                f"delivery_date ({delivery.value}) is not after trade_date ({trade.value})",
            )
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid date format for delivery vs trade date check"


_delivery_date_check = Invariant(
    name="delivery_date_after_trade_date",
    fields=["trade_date", "delivery_date"],
    fn=_check_delivery_after_trade,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING: "Run detect_layout on the relevant document (assay, BoL, or LC). "
    "Crop the field region and read with OCR. Use read_table for "
    "assay composition tables.",
    GapType.INVARIANT_FAILED: "Volume tolerance check failed. Re-crop the loaded volume from "
    "the BoL and the LC amount. Verify units (barrels vs metric tons). "
    "Use cross_check to compare across documents.",
}


CommodityTradeSkill = Skill(
    name="commodity_trade",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "read_table",
        "handwriting": "vlm",
        "figure": "vlm",
    },
    probe_order=[
        ("header", "Certificate number, commodity type, and vessel name are in the header"),
        ("table", "Assay composition and volume data are in tables — use read_table"),
        ("text", "Temperature and API gravity are near the volume data"),
        ("text", "Inspector company is usually at the bottom/footer"),
    ],
    invariants=[_volume_check, _total_value_check, _delivery_date_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Cross-document matching: vessel name and ports must match across "
        "assay, BoL, and LC. Use cross_check. "
        "Temperature corrections are deterministic — never use LLM. "
        "API gravity may be labeled 'API' or 'API Gravity at 60°F'. "
        "Volume units vary: barrels, metric tons, cubic meters."
    ),
    confidence_overrides={
        "loaded_volume_barrels": 0.95,
        "api_gravity": 0.90,
        "vessel_name": 0.90,
    },
)
