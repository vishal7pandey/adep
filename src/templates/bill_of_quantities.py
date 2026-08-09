"""BillOfQuantitiesTemplate — BOQ extraction schema [BLK-042, §14].

Extraction contract for construction bill of quantities documents.
Defines line item fields with the qty × rate = total invariant.
"""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class BillOfQuantitiesTemplate(Template):
    """Schema for bill of quantities extraction."""

    project_name: str = Field(description="Project name or title")
    boq_reference: str = Field(description="BOQ reference number")
    date: str = Field(description="Document date (YYYY-MM-DD)")
    contractor: str = Field(description="Contractor or bidder name")
    line_items: list[dict] = Field(
        description="List of line items, each with: item_no, description, "
        "unit, quantity, rate, total"
    )
    subtotal: float = Field(description="Sum of all line item totals")
    vat_percent: float = Field(description="VAT percentage rate")
    vat_amount: float = Field(description="VAT amount")
    grand_total: float = Field(description="Grand total including VAT")
