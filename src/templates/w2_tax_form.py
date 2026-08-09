"""W2TaxFormTemplate — outcome contract for W-2 tax form extraction [BLK-106]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class W2TaxFormTemplate(Template):
    """Outcome schema for W-2 tax form extraction."""
    employee_ssn: str = Field(description="Employee Social Security Number (masked)")
    employer_ein: str = Field(description="Employer Identification Number (EIN)")
    employee_name: str = Field(description="Employee full name")
    employee_address: str = Field(description="Employee street address")
    employer_name: str = Field(description="Employer name")
    employer_address: str = Field(description="Employer address")
    control_number: str = Field(description="Control number (box a)")
    wages: float = Field(description="Wages, tips, other compensation (box 1)")
    federal_tax_withheld: float = Field(description="Federal income tax withheld (box 2)")
    social_security_wages: float = Field(description="Social security wages (box 3)")
    social_security_tax_withheld: float = Field(description="Social security tax withheld (box 4)")
    medicare_wages: float = Field(description="Medicare wages and tips (box 5)")
    medicare_tax_withheld: float = Field(description="Medicare tax withheld (box 6)")
    social_security_tips: float = Field(description="Social security tips (box 7)")
    allocated_tips: float = Field(description="Allocated tips (box 8)")
    dependent_care_benefits: float = Field(description="Dependent care benefits (box 10)")
    nonqualified_plans: float = Field(description="Nonqualified plans (box 11)")
    tax_year: str = Field(description="Tax year (YYYY)")
