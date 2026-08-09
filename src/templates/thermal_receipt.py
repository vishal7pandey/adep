"""ThermalReceiptTemplate — consumer staples thermal receipt schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class ReceiptItem(Template):
    """A single line item on a thermal receipt."""

    description: str = Field(description="Item name or description")
    quantity: float = Field(default=1.0, description="Quantity purchased")
    unit_price: float = Field(description="Price per unit")
    amount: float = Field(description="Line total (quantity * unit_price)")


class ThermalReceiptTemplate(Template):
    """Outcome schema for thermal receipt extraction."""

    merchant_name: str = Field(description="Name of the merchant/store")
    merchant_address: str = Field(default="", description="Merchant street address")
    transaction_date: str = Field(description="Date of transaction in YYYY-MM-DD format")
    transaction_time: str = Field(default="", description="Time of transaction in HH:MM format")
    items: list[ReceiptItem] = Field(description="Itemized purchases")
    subtotal: float = Field(description="Sum of all item amounts before tax")
    tax_amount: float = Field(default=0.0, description="Total tax charged")
    total_amount: float = Field(description="Total amount paid (subtotal + tax)")
    payment_method: str = Field(default="", description="Payment method (cash, card, etc.)")
    receipt_number: str = Field(default="", description="Receipt or transaction ID")
