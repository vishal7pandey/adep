"""TravelPackingChecklistTemplate — travel checklist extraction contract."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class TravelPackingChecklistTemplate(Template):
    """Outcome schema for travel-oriented packing checklist documents."""

    checklist_title: str = Field(description="Checklist heading text")
    has_documents_money_section: bool = Field(description="Whether DOCUMENTS & MONEY section is present")
    has_clothing_section: bool = Field(description="Whether CLOTHING section is present")
    has_toiletries_section: bool = Field(description="Whether TOILETRIES section is present")
    has_electronics_section: bool = Field(description="Whether ELECTRONICS section is present")
    has_health_safety_section: bool = Field(description="Whether HEALTH & SAFETY section is present")
    has_extras_section: bool = Field(description="Whether EXTRAS section is present")
    item_count_estimate: int = Field(description="Approximate count of checklist lines/items")
