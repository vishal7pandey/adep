"""CommodityTradeTemplate — commodity trade reconciliation schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class CommodityTradeTemplate(Template):
    """Outcome schema for commodity trade reconciliation."""

    commodity_type: str = Field(description="Type of commodity (e.g. crude oil, LNG)")
    loaded_volume_barrels: float = Field(description="Loaded volume in barrels (from BoL)")
    loaded_volume_metric_tons: float = Field(
        default=0.0, description="Loaded volume in metric tons (from assay)"
    )
    api_gravity: float = Field(description="API gravity of the commodity")
    temperature_observed: float = Field(description="Observed temperature in degrees Celsius")
    volume_at_15c: float = Field(description="Volume corrected to 15°C standard temperature")
    vessel_name: str = Field(description="Name of the vessel")
    loading_port: str = Field(description="Port where cargo was loaded")
    discharge_port: str = Field(description="Port where cargo will be discharged")
    inspector_company: str = Field(description="Independent inspection company name")
