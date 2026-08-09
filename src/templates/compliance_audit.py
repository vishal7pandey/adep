"""ComplianceAuditTemplate — SOC 2 / OSPAR compliance audit schema [BLK-087]."""

from __future__ import annotations

from pydantic import Field

from src.templates.base import Template


class ComplianceAuditTemplate(Template):
    """Outcome schema for compliance audit extraction."""

    encryption_at_rest: bool = Field(description="Whether AES-256 encryption at rest is confirmed")
    encryption_in_transit: bool = Field(description="Whether TLS 1.3 encryption in transit is confirmed")
    access_controls: bool = Field(description="Whether access controls are implemented")
    penetration_testing: bool = Field(description="Whether annual penetration testing is conducted")
    data_isolation: bool = Field(description="Whether tenant data isolation is confirmed")
    audit_log_retention: int = Field(description="Audit log retention period in days (≥ 365 for SOC 2)")
    outsourcing_registered: bool = Field(default=False, description="Whether outsourcing is registered (OSPAR)")
    control_count_total: int = Field(description="Total number of controls assessed")
    control_count_passed: int = Field(default=0, description="Number of controls that passed")
