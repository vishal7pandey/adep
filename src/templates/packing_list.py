"""PackingListTemplate — outcome contract for packing list extraction [BLK-106]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class PackingItem(Template):
    """A single item on a packing list."""

    item_code: str = Field(description="SKU or product code")
    description: str = Field(description="Item description")
    quantity: float = Field(description="Quantity packed")
    unit: str = Field(description="Unit of measure (e.g. pcs, kg, box)")
    weight: float = Field(description="Weight of this line (kg)")
    carton_number: str = Field(description="Carton or package number")


class PackingListTemplate(Template):
    """Outcome schema for packing list extraction."""

    pl_number: str = Field(description="Packing list number")
    pl_date: str = Field(description="Issue date in ISO YYYY-MM-DD format")
    shipper: str = Field(description="Name of the shipping company")
    consignee: str = Field(description="Name of the receiving party (consignee)")
    origin: str = Field(description="Origin port or location")
    destination: str = Field(description="Destination port or location")
    container_number: str = Field(description="Shipping container number")
    total_packages: int = Field(description="Total number of packages or cartons")
    total_weight: float = Field(description="Total gross weight (kg)")
    items: list[PackingItem] = Field(description="Packed items")
