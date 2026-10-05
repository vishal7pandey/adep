"""PayStubTemplate — outcome contract for pay stub extraction [BLK-106]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class Deduction(Template):
    """A single deduction line on a pay stub."""

    description: str = Field(description="Deduction description (e.g. Federal Tax, 401k)")
    amount: float = Field(description="Deduction amount for this period")


class PayStubTemplate(Template):
    """Outcome schema for pay stub extraction."""

    employee_name: str = Field(description="Employee full name")
    employer_name: str = Field(description="Employer name")
    pay_period_start: str = Field(description="Pay period start date (ISO YYYY-MM-DD)")
    pay_period_end: str = Field(description="Pay period end date (ISO YYYY-MM-DD)")
    pay_date: str = Field(description="Pay date (ISO YYYY-MM-DD)")
    gross_pay: float = Field(description="Gross pay for this period")
    net_pay: float = Field(description="Net pay (take-home) for this period")
    ytd_gross: float = Field(description="Year-to-date gross pay")
    ytd_net: float = Field(description="Year-to-date net pay")
    federal_tax: float = Field(description="Federal income tax withheld")
    state_tax: float = Field(description="State income tax withheld")
    social_security: float = Field(description="Social security tax")
    medicare: float = Field(description="Medicare tax")
    deductions: list[Deduction] = Field(description="Itemized deductions (401k, health, etc.)")
