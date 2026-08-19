"""Prebuilt agent definitions for all 11 GICS sectors [BLK-087].

This module creates and registers prebuilt AgentDefinition objects
in the Definition Store so they appear immediately in the UI via
GET /api/v1/definitions.

Each definition wires a skill + template + tool set + system prompt +
max iterations for a specific industry sector.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from src.definitions.base import AgentConfig, AgentDefinition

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Template field extraction — serializes Pydantic model_fields into dicts [BLK-108]
# ---------------------------------------------------------------------------

def _pydantic_type_to_str(annotation: Any) -> str:
    """Convert a Pydantic field annotation to a readable string."""
    import typing
    origin = typing.get_origin(annotation)
    if origin is list:
        args = typing.get_args(annotation)
        inner = _pydantic_type_to_str(args[0]) if args else "Any"
        return f"list[{inner}]"
    if origin is dict:
        args = typing.get_args(annotation)
        key = _pydantic_type_to_str(args[0]) if args else "str"
        val = _pydantic_type_to_str(args[1]) if len(args) > 1 else "Any"
        return f"dict[{key}, {val}]"
    if hasattr(annotation, "__name__"):
        return annotation.__name__
    return str(annotation).replace("typing.", "")


def _extract_template_fields(template_cls: Any) -> list[dict[str, Any]]:
    """Extract field schemas from a Template Pydantic model class [BLK-108]."""
    fields = []
    for name, field_info in template_cls.model_fields.items():
        fields.append({
            "name": name,
            "type": _pydantic_type_to_str(field_info.annotation),
            "description": field_info.description or "",
            "required": field_info.is_required(),
        })
    return fields


# ---------------------------------------------------------------------------
# Skill serialization — converts Skill dataclass to dict [BLK-108]
# ---------------------------------------------------------------------------

def _serialize_skill(skill: Any) -> dict[str, Any]:
    """Serialize a Skill dataclass instance to a JSON-compatible dict [BLK-108]."""
    return {
        "id": skill.name,
        "name": skill.name.replace("_", " ").title(),
        "description": _skill_descriptions.get(skill.name, ""),
        "tools": _skill_tools.get(skill.name, []),
        "system_prompt": skill.system_prompt,
        "tool_preferences": dict(skill.tool_preferences),
        "probe_order": [{"region_type": rt, "rationale": rat} for rt, rat in skill.probe_order],
        "invariants": [
            {
                "name": inv.name,
                "fields": inv.fields,
            }
            for inv in skill.invariants
        ],
        "failure_actions": {
            gap_type.value: action for gap_type, action in skill.failure_actions.items()
        },
        "known_failures": skill.known_failures,
        "confidence_overrides": dict(skill.confidence_overrides),
    }


# Skill ID → description mapping (used for serializing skill metadata)
_skill_descriptions: dict[str, str] = {
    "invoice": "General invoice extraction",
    "trade_finance_scrutiny": "MT700 / LC scrutiny",
    "bill_of_quantities": "Construction BOQ",
    "utility_bill": "Utility bill with chart extraction",
    "thermal_receipt": "Consumer thermal receipt (geometry-first)",
    "medical_claim": "CMS-1500 medical claim forms",
    "compliance_audit": "SOC 2 / OSPAR compliance audit",
    "commercial_lease": "Commercial lease abstraction",
    "commodity_trade": "Commodity trade reconciliation",
    "metallurgical_assay": "Metallurgical assay certificate",
    "store_audit": "Retail store audit checklist",
    "ad_buy": "Advertising insertion order",
    "purchase_order_sf1449": "Government SF-1449 purchase/order form",
    "packing_list_travel": "Travel packing checklist",
}

# Skill ID → tools list mapping (used for serializing skill metadata)
_skill_tools: dict[str, list[str]] = {
    "invoice": ["detect_layout", "ocr", "vlm", "crop"],
    "trade_finance_scrutiny": ["detect_layout", "ocr", "vlm", "crop"],
    "bill_of_quantities": ["detect_layout", "detect_tables", "ocr", "read_table", "crop"],
    "utility_bill": ["detect_layout", "ocr", "read_chart", "vlm", "crop"],
    "thermal_receipt": ["auto_orient", "deskew", "denoise", "threshold", "ocr", "vlm", "crop"],
    "medical_claim": ["detect_layout", "ocr", "vlm", "crop"],
    "compliance_audit": ["detect_layout", "ocr", "vlm", "crop"],
    "commercial_lease": ["detect_layout", "ocr", "vlm", "crop"],
    "commodity_trade": ["detect_layout", "ocr", "vlm", "read_table", "crop"],
    "metallurgical_assay": ["detect_layout", "detect_tables", "ocr", "read_table", "vlm", "crop", "deskew"],
    "store_audit": ["detect_layout", "ocr", "vlm", "crop"],
    "ad_buy": ["detect_layout", "detect_tables", "ocr", "read_table"],
    "purchase_order_sf1449": ["detect_layout", "ocr", "read_table", "crop"],
    "packing_list_travel": ["detect_layout", "ocr", "crop"],
}

PREBUILT_DEFINITIONS: list[dict] = [
    {
        "id": "def-invoice",
        "name": "Invoice Extraction",
        "version": "1.0.0",
        "skill_id": "invoice",
        "template_id": "invoice",
        "tool_names": ["detect_layout", "ocr", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 20,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-trade-finance-scrutiny",
        "name": "Trade Finance Scrutiny (MT700)",
        "version": "1.0.0",
        "skill_id": "trade_finance_scrutiny",
        "template_id": "trade_finance_mt700",
        "tool_names": ["detect_layout", "ocr", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 25,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-boq-estimator",
        "name": "Bill of Quantities Estimator",
        "version": "1.0.0",
        "skill_id": "bill_of_quantities",
        "template_id": "bill_of_quantities",
        "tool_names": ["detect_layout", "detect_tables", "ocr", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 30,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-compliance-audit",
        "name": "Compliance Audit (SOC 2 / OSPAR)",
        "version": "1.0.0",
        "skill_id": "compliance_audit",
        "template_id": "compliance_audit_soc2",
        "tool_names": ["detect_layout", "ocr", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 40,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-commercial-lease",
        "name": "Commercial Lease Abstraction",
        "version": "1.0.0",
        "skill_id": "commercial_lease",
        "template_id": "commercial_lease",
        "tool_names": ["detect_layout", "ocr", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 35,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-commodity-trade",
        "name": "Commodity Trade Reconciliation",
        "version": "1.0.0",
        "skill_id": "commodity_trade",
        "template_id": "commodity_trade_assay",
        "tool_names": ["detect_layout", "ocr", "vlm", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 20,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-metallurgical-assay",
        "name": "Metallurgical Assay Certificate",
        "version": "1.0.0",
        "skill_id": "metallurgical_assay",
        "template_id": "metallurgical_assay",
        "tool_names": ["detect_layout", "detect_tables", "ocr", "read_table", "vlm", "crop", "deskew"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 20,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-medical-claim",
        "name": "Medical Claim (CMS-1500)",
        "version": "1.0.0",
        "skill_id": "medical_claim",
        "template_id": "medical_claim_cms1500",
        "tool_names": ["detect_layout", "ocr", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 15,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-store-audit",
        "name": "Store Audit Checklist",
        "version": "1.0.0",
        "skill_id": "store_audit",
        "template_id": "store_audit_checklist",
        "tool_names": ["detect_layout", "ocr", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 4,
            "max_cycles_per_document": 15,
            "confidence_threshold": 0.80,
        },
    },
    {
        "id": "def-thermal-receipt",
        "name": "Thermal Receipt Extraction",
        "version": "1.0.0",
        "skill_id": "thermal_receipt",
        "template_id": "thermal_receipt",
        "tool_names": ["auto_orient", "deskew", "denoise", "threshold", "ocr", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 4,
            "max_cycles_per_document": 12,
            "confidence_threshold": 0.80,
        },
    },
    {
        "id": "def-ad-buy",
        "name": "Advertising Insertion Order",
        "version": "1.0.0",
        "skill_id": "ad_buy",
        "template_id": "ad_insertion_order",
        "tool_names": ["detect_layout", "detect_tables", "ocr", "read_table"],
        "agent_config": {
            "max_cycles_per_field": 4,
            "max_cycles_per_document": 15,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-utility-bill",
        "name": "Utility Bill with Chart Extraction",
        "version": "1.0.0",
        "skill_id": "utility_bill",
        "template_id": "utility_bill",
        "tool_names": ["detect_layout", "ocr", "read_chart", "vlm", "crop"],
        "agent_config": {
            "max_cycles_per_field": 4,
            "max_cycles_per_document": 15,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-bank-statement",
        "name": "Bank Statement Parser",
        "version": "1.0.0",
        "skill_id": "bank_statement",
        "template_id": "bank_statement",
        "tool_names": ["detect_layout", "ocr", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 30,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-purchase-order",
        "name": "Purchase Order Parser",
        "version": "1.0.0",
        "skill_id": "purchase_order",
        "template_id": "purchase_order",
        "tool_names": ["detect_layout", "ocr", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 25,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-purchase-order-sf1449",
        "name": "Purchase Order Parser (SF-1449)",
        "version": "1.0.0",
        "skill_id": "purchase_order_sf1449",
        "template_id": "purchase_order_sf1449",
        "tool_names": ["detect_layout", "ocr", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 4,
            "max_cycles_per_document": 20,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-packing-list",
        "name": "Packing List Parser",
        "version": "1.0.0",
        "skill_id": "packing_list",
        "template_id": "packing_list",
        "tool_names": ["detect_layout", "ocr", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 30,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-packing-list-travel",
        "name": "Packing List Parser (Travel Checklist)",
        "version": "1.0.0",
        "skill_id": "packing_list_travel",
        "template_id": "packing_list_travel",
        "tool_names": ["detect_layout", "ocr", "crop"],
        "agent_config": {
            "max_cycles_per_field": 4,
            "max_cycles_per_document": 20,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-w2-tax-form",
        "name": "W-2 Tax Form Parser",
        "version": "1.0.0",
        "skill_id": "w2_tax_form",
        "template_id": "w2_tax_form",
        "tool_names": ["detect_layout", "ocr", "crop"],
        "agent_config": {
            "max_cycles_per_field": 4,
            "max_cycles_per_document": 25,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-pay-stub",
        "name": "Pay Stub Parser",
        "version": "1.0.0",
        "skill_id": "pay_stub",
        "template_id": "pay_stub",
        "tool_names": ["detect_layout", "ocr", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 30,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-insurance-policy",
        "name": "Insurance Policy Declaration Parser",
        "version": "1.0.0",
        "skill_id": "insurance_policy",
        "template_id": "insurance_policy",
        "tool_names": ["detect_layout", "ocr", "read_table", "crop"],
        "agent_config": {
            "max_cycles_per_field": 5,
            "max_cycles_per_document": 35,
            "confidence_threshold": 0.85,
        },
    },
    {
        "id": "def-pnid-to-dexpi",
        "name": "P&ID to DEXPI Converter",
        "version": "1.0.0",
        "task_type": "graph_extraction",
        "skill_id": "pid_to_dexpi",
        "template_id": "pid_to_dexpi",
        "tool_names": [
            "detect_layout", "detect_symbols", "classify_symbol",
            "ocr", "vlm", "read_tag", "trace_line", "detect_connections",
            "build_graph", "validate_topology", "serialize_graph",
            "crop", "deskew"
        ],
        "agent_config": {
            "max_cycles_per_field": 10,
            "max_cycles_per_document": 50,
            "confidence_threshold": 0.75,
        },
    },
]


def get_prebuilt_definitions() -> list[AgentDefinition]:
    """Return all 18 prebuilt AgentDefinition objects [BLK-087]."""
    definitions: list[AgentDefinition] = []
    for data in PREBUILT_DEFINITIONS:
        data_copy = {**data}
        config_data = data_copy.pop("agent_config", {})
        config = AgentConfig(**config_data)
        definitions.append(AgentDefinition(**data_copy, agent_config=config))
    return definitions


# ---------------------------------------------------------------------------
# Skill and template metadata for seeding [BLK-092, BLK-108]
# ---------------------------------------------------------------------------

def _build_prebuilt_skills() -> list[dict]:
    """Build PREBUILT_SKILLS by serializing actual Skill objects [BLK-108]."""
    from src.skills.invoice import InvoiceSkill
    from src.skills.trade_finance import TradeFinanceScrutinySkill
    from src.skills.bill_of_quantities import BillOfQuantitiesSkill
    from src.skills.utility_bill import UtilityBillSkill
    from src.skills.thermal_receipt import ThermalReceiptSkill
    from src.skills.medical_claim import MedicalClaimSkill
    from src.skills.compliance_audit import ComplianceAuditSkill
    from src.skills.commercial_lease import CommercialLeaseSkill
    from src.skills.commodity_trade import CommodityTradeSkill
    from src.skills.metallurgical_assay import MetallurgicalAssaySkill
    from src.skills.store_audit import StoreAuditSkill
    from src.skills.ad_buy import AdBuySkill
    from src.skills.bank_statement import BankStatementSkill
    from src.skills.purchase_order import PurchaseOrderSkill
    from src.skills.purchase_order_sf1449 import PurchaseOrderSF1449Skill
    from src.skills.packing_list import PackingListSkill
    from src.skills.packing_list_travel import TravelPackingChecklistSkill
    from src.skills.w2_tax_form import W2TaxFormSkill
    from src.skills.pay_stub import PayStubSkill
    from src.skills.insurance_policy import InsurancePolicySkill
    from src.skills.pid_diagram import PnIDSkill

    skill_objects = [
        InvoiceSkill, TradeFinanceScrutinySkill, BillOfQuantitiesSkill,
        UtilityBillSkill, ThermalReceiptSkill, MedicalClaimSkill,
        ComplianceAuditSkill, CommercialLeaseSkill, CommodityTradeSkill,
        MetallurgicalAssaySkill, StoreAuditSkill, AdBuySkill,
        BankStatementSkill, PurchaseOrderSkill, PackingListSkill,
        PurchaseOrderSF1449Skill, TravelPackingChecklistSkill,
        W2TaxFormSkill, PayStubSkill, InsurancePolicySkill,
        PnIDSkill,
    ]
    return [_serialize_skill(s) for s in skill_objects]


PREBUILT_SKILLS: list[dict] = _build_prebuilt_skills()


def _build_prebuilt_templates() -> list[dict]:
    """Build PREBUILT_TEMPLATES by extracting fields from Template classes [BLK-108]."""
    from src.templates.invoice import InvoiceTemplate
    from src.templates.trade_finance import TradeFinanceTemplate
    from src.templates.bill_of_quantities import BillOfQuantitiesTemplate
    from src.templates.utility_bill import UtilityBillTemplate
    from src.templates.thermal_receipt import ThermalReceiptTemplate
    from src.templates.medical_claim import MedicalClaimTemplate
    from src.templates.compliance_audit import ComplianceAuditTemplate
    from src.templates.commercial_lease import CommercialLeaseTemplate
    from src.templates.commodity_trade import CommodityTradeTemplate
    from src.templates.metallurgical_assay import MetallurgicalAssayTemplate
    from src.templates.store_audit import StoreAuditTemplate
    from src.templates.ad_insertion_order import AdInsertionOrderTemplate
    from src.templates.bank_statement import BankStatementTemplate
    from src.templates.purchase_order import PurchaseOrderTemplate
    from src.templates.purchase_order_sf1449 import PurchaseOrderSF1449Template
    from src.templates.packing_list import PackingListTemplate
    from src.templates.packing_list_travel import TravelPackingChecklistTemplate
    from src.templates.w2_tax_form import W2TaxFormTemplate
    from src.templates.pay_stub import PayStubTemplate
    from src.templates.insurance_policy import InsurancePolicyTemplate
    from src.templates.pid_diagram import PnIDContract

    template_specs = [
        ("invoice", "Invoice", "Standard invoice template", InvoiceTemplate),
        ("trade_finance_mt700", "Trade Finance MT700", "MT700 letter of credit template", TradeFinanceTemplate),
        ("bill_of_quantities", "Bill of Quantities", "Construction BOQ template", BillOfQuantitiesTemplate),
        ("utility_bill", "Utility Bill", "Utility bill template", UtilityBillTemplate),
        ("thermal_receipt", "Thermal Receipt", "Consumer thermal receipt template", ThermalReceiptTemplate),
        ("medical_claim_cms1500", "Medical Claim CMS-1500", "CMS-1500 claim form template", MedicalClaimTemplate),
        ("compliance_audit_soc2", "Compliance Audit SOC 2", "SOC 2 / OSPAR audit template", ComplianceAuditTemplate),
        ("commercial_lease", "Commercial Lease", "Commercial lease template", CommercialLeaseTemplate),
        ("commodity_trade_assay", "Commodity Trade Assay", "Commodity trade reconciliation template", CommodityTradeTemplate),
        ("metallurgical_assay", "Metallurgical Assay", "Metallurgical assay certificate template", MetallurgicalAssayTemplate),
        ("store_audit_checklist", "Store Audit Checklist", "Retail store audit template", StoreAuditTemplate),
        ("ad_insertion_order", "Ad Insertion Order", "Advertising insertion order template", AdInsertionOrderTemplate),
        ("bank_statement", "Bank Statement", "Bank statement with transactions and running balances", BankStatementTemplate),
        ("purchase_order", "Purchase Order", "Purchase order with line items and totals", PurchaseOrderTemplate),
        ("purchase_order_sf1449", "Purchase Order SF-1449", "U.S. government SF-1449 structure", PurchaseOrderSF1449Template),
        ("packing_list", "Packing List", "Shipping packing list with items and weights", PackingListTemplate),
        ("packing_list_travel", "Travel Packing Checklist", "Travel checklist structure and section coverage", TravelPackingChecklistTemplate),
        ("w2_tax_form", "W-2 Tax Form", "IRS W-2 wage and tax statement", W2TaxFormTemplate),
        ("pay_stub", "Pay Stub", "Employee pay stub with earnings and deductions", PayStubTemplate),
        ("insurance_policy", "Insurance Policy Declaration", "Insurance declaration page with coverages and premiums", InsurancePolicyTemplate),
        ("pid_to_dexpi", "P&ID to DEXPI", "P&ID graph extraction to DEXPI XML and Smart P&ID JSON", PnIDContract),
    ]
    return [
        {
            "id": tid,
            "name": name,
            "description": desc,
            "fields": _extract_template_fields(cls),
        }
        for tid, name, desc, cls in template_specs
    ]


PREBUILT_TEMPLATES: list[dict] = _build_prebuilt_templates()
