"""StoreAuditTemplate — retail store audit checklist schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class StoreAuditTemplate(Template):
    """Outcome schema for store audit extraction."""

    store_id: str = Field(description="Unique store identifier")
    audit_date: str = Field(description="Date of audit in YYYY-MM-DD format")
    inspector_name: str = Field(description="Name of the auditor/inspector")
    cleanliness_score: int = Field(description="Cleanliness rating on 1-5 scale")
    compliance_items: list[bool] = Field(description="Boolean pass/fail for each checklist item")
    photo_evidence_count: int = Field(
        default=0, description="Number of photos/figures in the report"
    )
    violations: list[str] = Field(default_factory=list, description="List of identified violations")
    overall_pass: bool = Field(description="Derived: true if all mandatory items pass")
