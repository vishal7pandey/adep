"""BankStatementTemplate — outcome contract for bank statement extraction [BLK-106]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class Transaction(Template):
    """A single transaction line on a bank statement."""

    date: str = Field(description="Transaction date in ISO YYYY-MM-DD format")
    description: str = Field(description="Transaction description or memo")
    amount: float = Field(
        description="Transaction amount (negative for debit, positive for credit)"
    )
    balance: float = Field(description="Running balance after this transaction")


class BankStatementTemplate(Template):
    """Outcome schema for bank statement extraction."""

    bank_name: str = Field(description="Name of the issuing bank")
    account_number: str = Field(description="Bank account number (masked or full)")
    account_holder: str = Field(description="Name of the account holder")
    statement_period_start: str = Field(description="Statement period start date (ISO YYYY-MM-DD)")
    statement_period_end: str = Field(description="Statement period end date (ISO YYYY-MM-DD)")
    opening_balance: float = Field(
        description="Account balance at the start of the statement period"
    )
    closing_balance: float = Field(description="Account balance at the end of the statement period")
    total_credits: float = Field(description="Sum of all credit transactions in the period")
    total_debits: float = Field(
        description="Sum of all debit transactions in the period (absolute value)"
    )
    transactions: list[Transaction] = Field(description="List of individual transactions")
