"""Tests for BLK-087: Prebuilt catalogue — skills, templates, and definitions."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.skills.base import Skill
from src.agent.validator import Invariant, GapType
from src.templates.base import Template


# ---------------------------------------------------------------------------
# Skill imports
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Template imports
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Prebuilt definitions
# ---------------------------------------------------------------------------

from src.definitions.prebuilt import (
    PREBUILT_DEFINITIONS,
    get_prebuilt_definitions,
)


ALL_SKILLS = [
    InvoiceSkill,
    TradeFinanceScrutinySkill,
    BillOfQuantitiesSkill,
    UtilityBillSkill,
    ThermalReceiptSkill,
    MedicalClaimSkill,
    ComplianceAuditSkill,
    CommercialLeaseSkill,
    CommodityTradeSkill,
    MetallurgicalAssaySkill,
    StoreAuditSkill,
    AdBuySkill,
]

ALL_TEMPLATES = [
    InvoiceTemplate,
    TradeFinanceTemplate,
    BillOfQuantitiesTemplate,
    UtilityBillTemplate,
    ThermalReceiptTemplate,
    MedicalClaimTemplate,
    ComplianceAuditTemplate,
    CommercialLeaseTemplate,
    CommodityTradeTemplate,
    MetallurgicalAssayTemplate,
    StoreAuditTemplate,
    AdInsertionOrderTemplate,
]


class TestSkillStructure:
    """Verify all 12 skills follow the base pattern [BLK-087]."""

    def test_all_skills_are_skill_instances(self):
        for skill in ALL_SKILLS:
            assert isinstance(skill, Skill), f"{skill} is not a Skill instance"

    def test_all_skills_have_unique_names(self):
        names = [s.name for s in ALL_SKILLS]
        assert len(names) == len(set(names)), f"Duplicate skill names: {names}"

    def test_all_skills_have_system_prompt(self):
        for skill in ALL_SKILLS:
            assert skill.system_prompt, f"Skill '{skill.name}' has empty system_prompt"

    def test_all_skills_have_tool_preferences(self):
        for skill in ALL_SKILLS:
            assert skill.tool_preferences, f"Skill '{skill.name}' has empty tool_preferences"

    def test_all_skills_have_probe_order(self):
        for skill in ALL_SKILLS:
            assert skill.probe_order, f"Skill '{skill.name}' has empty probe_order"

    def test_all_skills_have_invariants(self):
        for skill in ALL_SKILLS:
            assert skill.invariants, f"Skill '{skill.name}' has no invariants"

    def test_all_skills_have_failure_actions(self):
        for skill in ALL_SKILLS:
            assert skill.failure_actions, f"Skill '{skill.name}' has empty failure_actions"

    def test_all_skills_have_known_failures(self):
        for skill in ALL_SKILLS:
            assert skill.known_failures, f"Skill '{skill.name}' has empty known_failures"

    def test_all_skills_have_confidence_overrides(self):
        for skill in ALL_SKILLS:
            assert skill.confidence_overrides, f"Skill '{skill.name}' has empty confidence_overrides"

    def test_expected_skill_names(self):
        expected = {
            "invoice", "trade_finance_scrutiny", "bill_of_quantities",
            "utility_bill", "thermal_receipt", "medical_claim",
            "compliance_audit", "commercial_lease", "commodity_trade",
            "metallurgical_assay", "store_audit", "ad_buy",
        }
        actual = {s.name for s in ALL_SKILLS}
        assert actual == expected


class TestTemplateStructure:
    """Verify all 11 templates follow the base pattern [BLK-087]."""

    def test_all_templates_subclass_template(self):
        for template in ALL_TEMPLATES:
            assert issubclass(template, Template), f"{template} is not a Template subclass"

    def test_all_templates_have_fields(self):
        for template in ALL_TEMPLATES:
            fields = template.model_fields
            assert len(fields) > 0, f"{template.__name__} has no fields"

    def test_all_template_fields_have_descriptions(self):
        for template in ALL_TEMPLATES:
            for field_name, field_info in template.model_fields.items():
                assert field_info.description, (
                    f"{template.__name__}.{field_name} has no description"
                )


class TestThermalReceiptSkill:
    """Verify thermal receipt skill specifics [BLK-087]."""

    def test_geometry_first_probe_order(self):
        assert ThermalReceiptSkill.probe_order[0][0] == "header"

    def test_sum_invariant(self):
        inv = ThermalReceiptSkill.invariants[0]
        assert "subtotal" in inv.fields
        assert "tax_amount" in inv.fields
        assert "total_amount" in inv.fields

    def test_confidence_overrides(self):
        assert "total_amount" in ThermalReceiptSkill.confidence_overrides
        assert ThermalReceiptSkill.confidence_overrides["total_amount"] == 0.90


class TestMedicalClaimSkill:
    """Verify medical claim skill specifics [BLK-087]."""

    def test_npi_invariant(self):
        inv_names = [inv.name for inv in MedicalClaimSkill.invariants]
        assert "npi_format_valid" in inv_names

    def test_date_order_invariant(self):
        inv_names = [inv.name for inv in MedicalClaimSkill.invariants]
        assert "service_date_from_before_to" in inv_names

    def test_vlm_for_handwriting(self):
        assert MedicalClaimSkill.tool_preferences.get("handwriting") == "vlm"


class TestComplianceAuditSkill:
    """Verify compliance audit skill specifics [BLK-087]."""

    def test_retention_invariant(self):
        inv_names = [inv.name for inv in ComplianceAuditSkill.invariants]
        assert "audit_log_retention_minimum" in inv_names

    def test_high_confidence_for_encryption(self):
        assert ComplianceAuditSkill.confidence_overrides["encryption_at_rest"] == 0.95


class TestCommercialLeaseSkill:
    """Verify commercial lease skill specifics [BLK-087]."""

    def test_lease_term_invariant(self):
        inv_names = [inv.name for inv in CommercialLeaseSkill.invariants]
        assert "expiration_equals_commencement_plus_term" in inv_names


class TestCommodityTradeSkill:
    """Verify commodity trade skill specifics [BLK-087]."""

    def test_volume_tolerance_invariant(self):
        inv_names = [inv.name for inv in CommodityTradeSkill.invariants]
        assert "volume_within_lc_tolerance" in inv_names


class TestMetallurgicalAssaySkill:
    """Verify metallurgical assay skill specifics [BLK-087]."""

    def test_spec_range_invariant(self):
        inv_names = [inv.name for inv in MetallurgicalAssaySkill.invariants]
        assert "composition_within_spec" in inv_names


class TestStoreAuditSkill:
    """Verify store audit skill specifics [BLK-087]."""

    def test_cleanliness_range_invariant(self):
        inv_names = [inv.name for inv in StoreAuditSkill.invariants]
        assert "cleanliness_score_in_range" in inv_names


class TestAdBuySkill:
    """Verify ad buy skill specifics [BLK-087]."""

    def test_budget_sum_invariant(self):
        inv_names = [inv.name for inv in AdBuySkill.invariants]
        assert "local_markets_sum_to_total_budget" in inv_names

    def test_impressions_sum_invariant(self):
        inv_names = [inv.name for inv in AdBuySkill.invariants]
        assert "local_impressions_sum_to_total" in inv_names


class TestPrebuiltDefinitions:
    """Verify prebuilt agent definitions [BLK-087]."""

    def test_21_definitions_exist(self):
        assert len(PREBUILT_DEFINITIONS) == 21

    def test_all_definition_ids_unique(self):
        ids = [d["id"] for d in PREBUILT_DEFINITIONS]
        assert len(ids) == len(set(ids))

    def test_expected_definition_ids(self):
        expected = {
            "def-trade-finance-scrutiny", "def-boq-estimator",
            "def-compliance-audit", "def-commercial-lease",
            "def-commodity-trade", "def-metallurgical-assay",
            "def-medical-claim", "def-store-audit",
            "def-thermal-receipt", "def-ad-buy",
            "def-utility-bill",
            "def-bank-statement", "def-purchase-order",
            "def-packing-list", "def-w2-tax-form",
            "def-pay-stub", "def-insurance-policy",
            "def-pnid-to-dexpi",
            "def-invoice", "def-packing-list-travel",
            "def-purchase-order-sf1449",
        }
        actual = {d["id"] for d in PREBUILT_DEFINITIONS}
        assert actual == expected

    def test_get_prebuilt_definitions_returns_objects(self):
        defs = get_prebuilt_definitions()
        assert len(defs) == 21
        from src.definitions.base import AgentDefinition
        for d in defs:
            assert isinstance(d, AgentDefinition)

    def test_all_definitions_have_skill_refs(self):
        for d in PREBUILT_DEFINITIONS:
            assert d["skill_id"], f"{d['id']} has no skill_id"

    def test_all_definitions_have_template_refs(self):
        for d in PREBUILT_DEFINITIONS:
            assert d["template_id"], f"{d['id']} has no template_id"

    def test_all_definitions_have_tool_names(self):
        for d in PREBUILT_DEFINITIONS:
            assert d["tool_names"], f"{d['id']} has no tool_names"

    def test_all_definitions_have_agent_config(self):
        for d in PREBUILT_DEFINITIONS:
            assert "agent_config" in d
            assert "max_cycles_per_document" in d["agent_config"]

    def test_store_returns_all_prebuilt_definitions(self, tmp_path: Path):
        from src.definitions.store import DefinitionStore
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        defs = store.list_definitions()
        assert len(defs) >= 18

        # Verify all prebuilt IDs are present
        ids = {d["id"] for d in defs}
        for d in PREBUILT_DEFINITIONS:
            assert d["id"] in ids

    def test_store_get_definition_returns_prebuilt(self, tmp_path: Path):
        from src.definitions.store import DefinitionStore
        store = DefinitionStore(base_dir=tmp_path / ".adep")
        first_id = PREBUILT_DEFINITIONS[0]["id"]
        result = store.get_definition(first_id)
        assert "skill_id" in result
        assert "template_id" in result


class TestSkillInvariantExecution:
    """Verify key invariants execute correctly [BLK-087]."""

    def test_thermal_receipt_sum_invariant_passes(self):
        from src.tools.base import FieldValue
        inv = ThermalReceiptSkill.invariants[0]
        extraction = {
            "subtotal": FieldValue(name="subtotal", value=100.00),
            "tax_amount": FieldValue(name="tax_amount", value=8.00),
            "total_amount": FieldValue(name="total_amount", value=108.00),
        }
        passed, msg = inv.fn(extraction)
        assert passed, msg

    def test_thermal_receipt_sum_invariant_fails(self):
        from src.tools.base import FieldValue
        inv = ThermalReceiptSkill.invariants[0]
        extraction = {
            "subtotal": FieldValue(name="subtotal", value=100.00),
            "tax_amount": FieldValue(name="tax_amount", value=8.00),
            "total_amount": FieldValue(name="total_amount", value=110.00),
        }
        passed, msg = inv.fn(extraction)
        assert not passed

    def test_medical_claim_npi_valid(self):
        from src.tools.base import FieldValue
        inv = [i for i in MedicalClaimSkill.invariants if i.name == "npi_format_valid"][0]
        extraction = {"provider_npi": FieldValue(name="provider_npi", value="1234567890")}
        passed, _ = inv.fn(extraction)
        assert passed

    def test_medical_claim_npi_invalid(self):
        from src.tools.base import FieldValue
        inv = [i for i in MedicalClaimSkill.invariants if i.name == "npi_format_valid"][0]
        extraction = {"provider_npi": FieldValue(name="provider_npi", value="12345")}
        passed, _ = inv.fn(extraction)
        assert not passed

    def test_store_audit_cleanliness_valid(self):
        from src.tools.base import FieldValue
        inv = StoreAuditSkill.invariants[0]
        extraction = {"cleanliness_score": FieldValue(name="cleanliness_score", value=4)}
        passed, _ = inv.fn(extraction)
        assert passed

    def test_store_audit_cleanliness_invalid(self):
        from src.tools.base import FieldValue
        inv = StoreAuditSkill.invariants[0]
        extraction = {"cleanliness_score": FieldValue(name="cleanliness_score", value=7)}
        passed, _ = inv.fn(extraction)
        assert not passed

    def test_ad_buy_budget_sum_valid(self):
        from src.tools.base import FieldValue
        inv = [i for i in AdBuySkill.invariants if i.name == "local_markets_sum_to_total_budget"][0]
        extraction = {
            "local_markets": FieldValue(name="local_markets", value=[
                {"market": "NYC", "spend": 50000, "impressions": 1000000},
                {"market": "LA", "spend": 30000, "impressions": 800000},
            ]),
            "total_budget": FieldValue(name="total_budget", value=80000),
        }
        passed, _ = inv.fn(extraction)
        assert passed

    def test_ad_buy_budget_sum_invalid(self):
        from src.tools.base import FieldValue
        inv = [i for i in AdBuySkill.invariants if i.name == "local_markets_sum_to_total_budget"][0]
        extraction = {
            "local_markets": FieldValue(name="local_markets", value=[
                {"market": "NYC", "spend": 50000, "impressions": 1000000},
                {"market": "LA", "spend": 30000, "impressions": 800000},
            ]),
            "total_budget": FieldValue(name="total_budget", value=100000),
        }
        passed, _ = inv.fn(extraction)
        assert not passed

    def test_compliance_audit_retention_valid(self):
        from src.tools.base import FieldValue
        inv = ComplianceAuditSkill.invariants[0]
        extraction = {"audit_log_retention": FieldValue(name="audit_log_retention", value=365)}
        passed, _ = inv.fn(extraction)
        assert passed

    def test_compliance_audit_retention_invalid(self):
        from src.tools.base import FieldValue
        inv = ComplianceAuditSkill.invariants[0]
        extraction = {"audit_log_retention": FieldValue(name="audit_log_retention", value=90)}
        passed, _ = inv.fn(extraction)
        assert not passed
