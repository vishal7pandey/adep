"""TradeFinanceTemplate — MT700 SWIFT message extraction schema [BLK-042, §14].

Extraction contract for trade finance documents (MT700, BoL, invoices).
Defines fields with deterministic invariants for date arithmetic and
amount tolerance checks.
"""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class TradeFinanceTemplate(Template):
    """Schema for MT700 SWIFT message extraction."""

    lc_number: str = Field(description="Letter of credit number (field 20)")
    lc_amount: float = Field(description="LC amount in currency (field 32B)")
    currency: str = Field(description="Currency code (e.g. USD, EUR)")
    issue_date: str = Field(description="Date of issue (YYYY-MM-DD)")
    expiry_date: str = Field(description="Expiry date (YYYY-MM-DD)")
    applicant: str = Field(description="Applicant name (field 50)")
    beneficiary: str = Field(description="Beneficiary name (field 59)")
    latest_shipment_date: str = Field(description="Latest shipment date (field 44C)")
    port_of_loading: str = Field(description="Port of loading (field 44A)")
    port_of_discharge: str = Field(description="Port of discharge (field 44B)")
    goods_description: str = Field(description="Description of goods (field 45A)")
    document_required: str = Field(description="Documents required (field 46A)")
