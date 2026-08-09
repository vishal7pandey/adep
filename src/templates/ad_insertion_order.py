"""AdInsertionOrderTemplate — advertising insertion order schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class LocalMarket(Template):
    """A single local market entry in an ad insertion order."""

    market: str = Field(description="Market name or DMA designation")
    spend: float = Field(description="Spend for this market in currency units")
    impressions: int = Field(description="Expected impressions for this market")


class AdInsertionOrderTemplate(Template):
    """Outcome schema for advertising insertion order extraction."""

    advertiser: str = Field(description="Advertiser/brand name")
    agency: str = Field(default="", description="Advertising agency name")
    campaign_name: str = Field(description="Campaign name or identifier")
    campaign_start: str = Field(description="Campaign start date in YYYY-MM-DD format")
    campaign_end: str = Field(description="Campaign end date in YYYY-MM-DD format")
    total_budget: float = Field(description="Total campaign budget")
    local_markets: list[LocalMarket] = Field(description="Per-market spend and impressions")
    total_impressions: int = Field(description="Total expected impressions (sum of local markets)")
    rate_type: str = Field(description="Rate type: CPM, CPC, or CPA")
