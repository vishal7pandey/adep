"""InsurancePolicyTemplate — outcome contract for insurance declaration page [BLK-106]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class CoverageLine(Template):
    """A single coverage line on an insurance policy declaration."""
    coverage_type: str = Field(description="Type of coverage (e.g. Liability, Collision, Comprehensive)")
    limit: str = Field(description="Coverage limit (e.g. $100,000 or $500 deductible)")
    premium: float = Field(description="Premium amount for this coverage")


class InsurancePolicyTemplate(Template):
    """Outcome schema for insurance policy declaration page extraction."""
    policy_number: str = Field(description="Policy number")
    policy_period_start: str = Field(description="Policy effective date (ISO YYYY-MM-DD)")
    policy_period_end: str = Field(description="Policy expiration date (ISO YYYY-MM-DD)")
    insurance_company: str = Field(description="Name of the insurance company")
    insured_name: str = Field(description="Name of the insured party")
    insured_address: str = Field(description="Address of the insured")
    agent_name: str = Field(description="Insurance agent or broker name")
    total_premium: float = Field(description="Total premium for the policy period")
    deductible: float = Field(description="General deductible amount")
    coverages: list[CoverageLine] = Field(description="Itemized coverage lines")
    policy_type: str = Field(description="Policy type (e.g. Auto, Home, Commercial)")
