"""PurchaseOrderSF1449Template — government SF-1449 extraction contract."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class PurchaseOrderSF1449Template(Template):
    """Outcome schema for U.S. government SF-1449 purchase/order forms."""

    form_title: str = Field(description="Canonical SF-1449 form title")
    form_revision: str = Field(description="Form revision string, e.g. REV. 11/2021")
    solicitation_number_present: bool = Field(description="Whether a solicitation number field is present")
    order_number_present: bool = Field(description="Whether an order number field is present")
    contract_number_present: bool = Field(description="Whether a contract number field is present")
    method_of_solicitation_section_present: bool = Field(description="Whether the method-of-solicitation section is present")
    schedule_table_present: bool = Field(description="Whether line-item schedule columns are present")
