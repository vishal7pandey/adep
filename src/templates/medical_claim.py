"""MedicalClaimTemplate — CMS-1500 medical claim form schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class MedicalClaimTemplate(Template):
    """Outcome schema for CMS-1500 medical claim extraction."""

    patient_name: str = Field(description="Full patient name")
    patient_dob: str = Field(description="Patient date of birth in YYYY-MM-DD format")
    patient_gender: str = Field(description="Patient gender (M/F/X)")
    provider_npi: str = Field(description="Provider National Provider Identifier (10 digits)")
    provider_name: str = Field(description="Provider or facility name")
    diagnosis_codes: list[str] = Field(description="ICD-10 diagnosis codes")
    procedure_codes: list[str] = Field(description="CPT procedure codes")
    service_date_from: str = Field(description="Service start date in YYYY-MM-DD format")
    service_date_to: str = Field(description="Service end date in YYYY-MM-DD format")
    billed_amount: float = Field(description="Total amount billed")
