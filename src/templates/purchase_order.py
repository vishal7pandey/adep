"""PurchaseOrderTemplate — outcome contract for purchase order extraction [BLK-106]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class POLineItem(Template):
    """A single line item on a purchase order."""
    description: str = Field(description="Item or service description")
    quantity: float = Field(description="Quantity ordered")
    unit_price: float = Field(description="Price per unit")
    amount: float = Field(description="Line total (quantity * unit_price)")


class PurchaseOrderTemplate(Template):
    """Outcome schema for purchase order extraction."""
    po_number: str = Field(description="Purchase order number")
    po_date: str = Field(description="Issue date in ISO YYYY-MM-DD format")
    expected_delivery_date: str = Field(description="Expected delivery date (ISO YYYY-MM-DD)")
    buyer: str = Field(description="Name of the buying company")
    vendor: str = Field(description="Name of the supplying vendor")
    ship_to_address: str = Field(description="Delivery address")
    line_items: list[POLineItem] = Field(description="Ordered items")
    subtotal: float = Field(description="Sum of line item amounts before tax")
    tax: float = Field(description="Total tax charged")
    shipping: float = Field(description="Shipping/handling charges")
    total: float = Field(description="Total amount (subtotal + tax + shipping)")
