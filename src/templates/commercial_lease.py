"""CommercialLeaseTemplate — commercial lease abstraction schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class CommercialLeaseTemplate(Template):
    """Outcome schema for commercial lease abstraction."""

    landlord: str = Field(description="Landlord or lessor name")
    tenant: str = Field(description="Tenant or lessee name")
    premises_address: str = Field(description="Address of the leased premises")
    lease_term_months: int = Field(description="Lease term duration in months")
    commencement_date: str = Field(description="Lease commencement date in YYYY-MM-DD format")
    expiration_date: str = Field(description="Lease expiration date in YYYY-MM-DD format")
    base_rent_monthly: float = Field(description="Monthly base rent amount")
    rent_escalation_pct: float = Field(default=0.0, description="Annual rent escalation percentage")
    cam_fees: str = Field(default="", description="Common Area Maintenance fees description")
    security_deposit: float = Field(description="Security deposit amount")
    renewal_option: bool = Field(default=False, description="Whether tenant has a renewal option")
    termination_clause: str = Field(default="", description="Termination clause summary")
