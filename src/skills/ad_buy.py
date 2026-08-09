"""AdBuySkill — advertising insertion order extraction [BLK-087].

Stylized tabular documents with local market tiers that must sum to
national total. Tabular sum invariants enforced deterministically.
"""

from __future__ import annotations

from src.agent.validator import GapType, Invariant
from src.skills.base import Skill
from src.skills.vlm_fallback import VLM_FALLBACK_ACTIONS


_SYSTEM_PROMPT = """\
You are an advertising insertion order extraction agent. Your job is to
extract campaign details and local market spend data from ad insertion
orders into the AdInsertionOrderTemplate.

Principles:
- Insertion orders are highly stylized tabular documents. Use detect_tables
  and read_table for structured extraction.
- Local markets table: each row has market name, spend, and impressions.
- The validator checks that sum(local_markets.spend) = total_budget.
- The validator checks that sum(local_markets.impressions) = total_impressions.
- Campaign start date must be before end date.
- Rate type is CPM (cost per mille), CPC (cost per click), or CPA (cost per action).
- Use cross_check for all sum invariants — never use LLM for arithmetic.
"""


def _check_budget_sum(e: dict) -> tuple[bool, str]:
    """Verify sum(local_markets.spend) = total_budget."""
    markets = e["local_markets"].value
    total = e["total_budget"].value
    if not isinstance(markets, list):
        return False, "local_markets is not a list"
    market_sum = sum(m.get("spend", 0) for m in markets if isinstance(m, dict))
    if abs(market_sum - total) > 0.01:
        return False, f"sum(local_markets.spend) ({market_sum}) != total_budget ({total})"
    return True, ""


_budget_check = Invariant(
    name="local_markets_sum_to_total_budget",
    fields=["local_markets", "total_budget"],
    fn=_check_budget_sum,
)


def _check_impressions_sum(e: dict) -> tuple[bool, str]:
    """Verify sum(local_markets.impressions) = total_impressions."""
    markets = e["local_markets"].value
    total = e["total_impressions"].value
    if not isinstance(markets, list):
        return False, "local_markets is not a list"
    imp_sum = sum(m.get("impressions", 0) for m in markets if isinstance(m, dict))
    if abs(imp_sum - total) > 1:
        return False, f"sum(local_markets.impressions) ({imp_sum}) != total_impressions ({total})"
    return True, ""


_impressions_check = Invariant(
    name="local_impressions_sum_to_total",
    fields=["local_markets", "total_impressions"],
    fn=_check_impressions_sum,
)


def _check_campaign_dates(e: dict) -> tuple[bool, str]:
    """Verify campaign_start <= campaign_end."""
    from datetime import datetime
    start = e.get("campaign_start")
    end = e.get("campaign_end")
    if not start or not end:
        return True, ""
    try:
        d_start = datetime.strptime(str(start.value), "%Y-%m-%d")
        d_end = datetime.strptime(str(end.value), "%Y-%m-%d")
        if d_start > d_end:
            return False, f"campaign_start ({start.value}) > campaign_end ({end.value})"
        return True, ""
    except (ValueError, TypeError):
        return False, "Invalid date format for campaign date comparison"


_campaign_date_check = Invariant(
    name="campaign_start_before_end",
    fields=["campaign_start", "campaign_end"],
    fn=_check_campaign_dates,
)


_FAILURE_ACTIONS: dict[GapType, str] = {
    **VLM_FALLBACK_ACTIONS,
    GapType.MISSING:
        "Run detect_tables to find the local markets table. Use read_table "
        "for structured extraction. Advertiser and campaign info are in "
        "the header.",
    GapType.INVARIANT_FAILED:
        "Sum invariant failed. Re-read the local markets table with "
        "read_table. Verify each row's spend and impressions. Use "
        "cross_check to compute sums deterministically.",
}


AdBuySkill = Skill(
    name="ad_buy",
    system_prompt=_SYSTEM_PROMPT,
    tool_preferences={
        "text": "ocr",
        "table": "read_table",
        "figure": "vlm",
    },
    probe_order=[
        ("header", "Advertiser, agency, campaign name, and dates are in the header"),
        ("table", "Local markets table with spend and impressions — use read_table"),
        ("text", "Total budget and total impressions are usually at the bottom"),
        ("text", "Rate type (CPM/CPC/CPA) is in the header or near the table"),
    ],
    invariants=[_budget_check, _impressions_check, _campaign_date_check],
    failure_actions=_FAILURE_ACTIONS,
    known_failures=(
        "Stylized tables: column headers may use logos or images. "
        "Local markets may be tiered (e.g. DMA, region, national). "
        "Spend values may be in different currencies — check for currency symbols. "
        "Impressions may be in thousands (e.g. '1,500' means 1.5M)."
    ),
    confidence_overrides={
        "total_budget": 0.95,
        "total_impressions": 0.90,
        "campaign_start": 0.85,
        "campaign_end": 0.85,
    },
)
