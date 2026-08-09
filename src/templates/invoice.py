"""InvoiceTemplate — the v1 vertical slice outcome contract [§3.1, §9].

This is the declarative extraction spec for invoices. It says *what* a valid
result looks like, nothing about *how* to obtain it. The agent and skill
handle the how.

Built to be tested against L2's invoice.png.
"""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class LineItem(Template):
    """A single line item on an invoice."""

    description: str = Field(description="Item or service description")
    quantity: float = Field(description="Quantity ordered")
    unit_price: float = Field(description="Price per unit")
    amount: float = Field(description="Line total (quantity * unit_price)")


class InvoiceTemplate(Template):
    """Outcome schema for invoice extraction.

    Every field must be grounded (carry a bbox) and meet the confidence
    threshold. The subtotal + tax == total invariant is enforced by the
    InvoiceSkill, not here — templates are pure data contracts.
    """

    invoice_number: str = Field(description="Vendor invoice ID or number")
    invoice_date: str = Field(description="Issue date in ISO YYYY-MM-DD format")
    due_date: str = Field(description="Payment due date in ISO YYYY-MM-DD format")
    vendor: str = Field(description="Name of the issuing company or vendor")
    line_items: list[LineItem] = Field(
        description="Itemized charges on the invoice"
    )
    subtotal: float = Field(description="Sum of line item amounts before tax")
    tax: float = Field(description="Total tax charged")
    total: float = Field(description="Total amount due (subtotal + tax)")
