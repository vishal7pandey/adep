"""MetallurgicalAssayTemplate — metallurgical assay certificate schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class MetallurgicalAssayTemplate(Template):
    """Outcome schema for metallurgical assay extraction."""

    certificate_number: str = Field(description="Assay certificate number")
    material_grade: str = Field(description="Material grade or specification")
    composition_elements: list[str] = Field(description="Chemical element names (e.g. C, Mn, Si)")
    composition_values: list[float] = Field(
        description="Measured composition values (parallel to elements)"
    )
    spec_min: list[float] = Field(description="Minimum spec values for each element")
    spec_max: list[float] = Field(description="Maximum spec values for each element")
    heat_number: str = Field(description="Heat or batch number for traceability")
    test_date: str = Field(description="Date of testing in YYYY-MM-DD format")
    inspector: str = Field(description="Inspector or testing company name")
