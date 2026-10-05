"""UtilityBillTemplate — utility bill extraction schema [BLK-042, §14].

Extraction contract for utility bills (electricity, gas, water).
Includes consumption history extracted from charts via read_chart.
"""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class UtilityBillTemplate(Template):
    """Schema for utility bill extraction."""

    account_number: str = Field(description="Customer account number")
    service_address: str = Field(description="Service address")
    billing_period_start: str = Field(description="Billing period start (YYYY-MM-DD)")
    billing_period_end: str = Field(description="Billing period end (YYYY-MM-DD)")
    utility_type: str = Field(description="Type of utility: electricity, gas, water")
    current_usage: float = Field(description="Current period usage (kWh, m³, gallons)")
    usage_unit: str = Field(description="Unit of measurement (kWh, m³, gal)")
    previous_usage: float = Field(description="Previous period usage")
    amount_due: float = Field(description="Total amount due")
    due_date: str = Field(description="Payment due date (YYYY-MM-DD)")
    consumption_history: list[dict] = Field(
        description="12-month consumption history from chart: [{'month': 'Jan', 'usage': 350}, ...]"
    )
