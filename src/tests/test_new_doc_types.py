"""Structure and invariant tests for new document types [BLK-106].

Tests cover:
- Template field structure for all 6 new types
- Skill configuration (prompt, probe order, invariants)
- Invariant logic (balance continuity, totals, tax rates, premium sum)
- Registry resolution (skill + template lookups in run_engine)
"""

from __future__ import annotations

import pytest

from src.skills.bank_statement import BankStatementSkill, _check_balance_continuity
from src.skills.purchase_order import PurchaseOrderSkill, _check_po_totals, _check_line_items_sum
from src.skills.packing_list import PackingListSkill, _check_total_weight
from src.skills.w2_tax_form import W2TaxFormSkill, _check_ss_tax, _check_medicare_tax
from src.skills.pay_stub import PayStubSkill, _check_net_pay
from src.skills.insurance_policy import InsurancePolicySkill, _check_premium_sum

from src.templates.bank_statement import BankStatementTemplate, Transaction
from src.templates.purchase_order import PurchaseOrderTemplate, POLineItem
from src.templates.packing_list import PackingListTemplate, PackingItem
from src.templates.w2_tax_form import W2TaxFormTemplate
from src.templates.pay_stub import PayStubTemplate, Deduction
from src.templates.insurance_policy import InsurancePolicyTemplate, CoverageLine

from src.agent.validator import GapType


# ---------------------------------------------------------------------------
# Helper: mock FieldValue
# ---------------------------------------------------------------------------


class MockFieldValue:
    """Mock FieldValue for invariant testing."""

    def __init__(self, value):
        self.value = value


def mock_state(**kwargs):
    """Build a mock extraction state dict for invariant testing."""
    return {k: MockFieldValue(v) for k, v in kwargs.items()}


# ---------------------------------------------------------------------------
# Template structure tests
# ---------------------------------------------------------------------------


class TestBankStatementTemplate:
    """Verify BankStatementTemplate structure."""

    def test_has_required_fields(self):
        fields = BankStatementTemplate.model_fields
        assert "bank_name" in fields
        assert "account_number" in fields
        assert "account_holder" in fields
        assert "statement_period_start" in fields
        assert "statement_period_end" in fields
        assert "opening_balance" in fields
        assert "closing_balance" in fields
        assert "total_credits" in fields
        assert "total_debits" in fields
        assert "transactions" in fields

    def test_transaction_subtemplate(self):
        fields = Transaction.model_fields
        assert "date" in fields
        assert "description" in fields
        assert "amount" in fields
        assert "balance" in fields


class TestPurchaseOrderTemplate:
    """Verify PurchaseOrderTemplate structure."""

    def test_has_required_fields(self):
        fields = PurchaseOrderTemplate.model_fields
        assert "po_number" in fields
        assert "po_date" in fields
        assert "expected_delivery_date" in fields
        assert "buyer" in fields
        assert "vendor" in fields
        assert "ship_to_address" in fields
        assert "line_items" in fields
        assert "subtotal" in fields
        assert "tax" in fields
        assert "shipping" in fields
        assert "total" in fields

    def test_line_item_subtemplate(self):
        fields = POLineItem.model_fields
        assert "description" in fields
        assert "quantity" in fields
        assert "unit_price" in fields
        assert "amount" in fields


class TestPackingListTemplate:
    """Verify PackingListTemplate structure."""

    def test_has_required_fields(self):
        fields = PackingListTemplate.model_fields
        assert "pl_number" in fields
        assert "pl_date" in fields
        assert "shipper" in fields
        assert "consignee" in fields
        assert "origin" in fields
        assert "destination" in fields
        assert "container_number" in fields
        assert "total_packages" in fields
        assert "total_weight" in fields
        assert "items" in fields


class TestW2TaxFormTemplate:
    """Verify W2TaxFormTemplate structure."""

    def test_has_required_fields(self):
        fields = W2TaxFormTemplate.model_fields
        assert "employee_ssn" in fields
        assert "employer_ein" in fields
        assert "employee_name" in fields
        assert "employer_name" in fields
        assert "wages" in fields
        assert "federal_tax_withheld" in fields
        assert "social_security_wages" in fields
        assert "social_security_tax_withheld" in fields
        assert "medicare_wages" in fields
        assert "medicare_tax_withheld" in fields
        assert "tax_year" in fields


class TestPayStubTemplate:
    """Verify PayStubTemplate structure."""

    def test_has_required_fields(self):
        fields = PayStubTemplate.model_fields
        assert "employee_name" in fields
        assert "employer_name" in fields
        assert "pay_period_start" in fields
        assert "pay_period_end" in fields
        assert "pay_date" in fields
        assert "gross_pay" in fields
        assert "net_pay" in fields
        assert "ytd_gross" in fields
        assert "ytd_net" in fields
        assert "federal_tax" in fields
        assert "deductions" in fields


class TestInsurancePolicyTemplate:
    """Verify InsurancePolicyTemplate structure."""

    def test_has_required_fields(self):
        fields = InsurancePolicyTemplate.model_fields
        assert "policy_number" in fields
        assert "policy_period_start" in fields
        assert "policy_period_end" in fields
        assert "insurance_company" in fields
        assert "insured_name" in fields
        assert "total_premium" in fields
        assert "deductible" in fields
        assert "coverages" in fields
        assert "policy_type" in fields


# ---------------------------------------------------------------------------
# Skill configuration tests
# ---------------------------------------------------------------------------


class TestSkillConfigurations:
    """Verify skill configurations for new document types."""

    def test_bank_statement_skill(self):
        assert BankStatementSkill.name == "bank_statement"
        assert len(BankStatementSkill.system_prompt) > 50
        assert len(BankStatementSkill.probe_order) >= 3
        assert len(BankStatementSkill.invariants) >= 1
        assert GapType.MISSING in BankStatementSkill.failure_actions

    def test_purchase_order_skill(self):
        assert PurchaseOrderSkill.name == "purchase_order"
        assert len(PurchaseOrderSkill.probe_order) >= 3
        assert len(PurchaseOrderSkill.invariants) >= 2

    def test_packing_list_skill(self):
        assert PackingListSkill.name == "packing_list"
        assert len(PackingListSkill.probe_order) >= 3
        assert len(PackingListSkill.invariants) >= 1

    def test_w2_tax_form_skill(self):
        assert W2TaxFormSkill.name == "w2_tax_form"
        assert len(W2TaxFormSkill.probe_order) >= 3
        assert len(W2TaxFormSkill.invariants) >= 2

    def test_pay_stub_skill(self):
        assert PayStubSkill.name == "pay_stub"
        assert len(PayStubSkill.probe_order) >= 3
        assert len(PayStubSkill.invariants) >= 1

    def test_insurance_policy_skill(self):
        assert InsurancePolicySkill.name == "insurance_policy"
        assert len(InsurancePolicySkill.probe_order) >= 3
        assert len(InsurancePolicySkill.invariants) >= 1


# ---------------------------------------------------------------------------
# Invariant tests
# ---------------------------------------------------------------------------


class TestBankStatementInvariants:
    """Verify bank statement balance continuity invariant."""

    def test_valid_balance(self):
        state = mock_state(
            opening_balance=1000.0,
            total_credits=500.0,
            total_debits=300.0,
            closing_balance=1200.0,
        )
        ok, msg = _check_balance_continuity(state)
        assert ok is True

    def test_invalid_balance(self):
        state = mock_state(
            opening_balance=1000.0,
            total_credits=500.0,
            total_debits=300.0,
            closing_balance=1100.0,
        )
        ok, msg = _check_balance_continuity(state)
        assert ok is False
        assert "1200" in msg

    def test_missing_fields_passes(self):
        state = mock_state(opening_balance=1000.0)
        ok, msg = _check_balance_continuity(state)
        assert ok is True


class TestPurchaseOrderInvariants:
    """Verify PO totals and line items sum invariants."""

    def test_valid_totals(self):
        state = mock_state(
            subtotal=100.0,
            tax=10.0,
            shipping=5.0,
            total=115.0,
        )
        ok, msg = _check_po_totals(state)
        assert ok is True

    def test_invalid_totals(self):
        state = mock_state(
            subtotal=100.0,
            tax=10.0,
            shipping=5.0,
            total=120.0,
        )
        ok, msg = _check_po_totals(state)
        assert ok is False

    def test_valid_line_items_sum(self):
        items = MockFieldValue(
            [
                {"amount": 50.0},
                {"amount": 30.0},
                {"amount": 20.0},
            ]
        )
        state = {"line_items": items, "subtotal": MockFieldValue(100.0)}
        ok, msg = _check_line_items_sum(state)
        assert ok is True

    def test_invalid_line_items_sum(self):
        items = MockFieldValue(
            [
                {"amount": 50.0},
                {"amount": 30.0},
                {"amount": 25.0},
            ]
        )
        state = {"line_items": items, "subtotal": MockFieldValue(100.0)}
        ok, msg = _check_line_items_sum(state)
        assert ok is False


class TestPackingListInvariants:
    """Verify packing list weight sum invariant."""

    def test_valid_weight(self):
        items = MockFieldValue(
            [
                {"weight": 10.0},
                {"weight": 20.0},
                {"weight": 5.0},
            ]
        )
        state = {"items": items, "total_weight": MockFieldValue(35.0)}
        ok, msg = _check_total_weight(state)
        assert ok is True

    def test_invalid_weight(self):
        items = MockFieldValue(
            [
                {"weight": 10.0},
                {"weight": 20.0},
            ]
        )
        state = {"items": items, "total_weight": MockFieldValue(35.0)}
        ok, msg = _check_total_weight(state)
        assert ok is False


class TestW2TaxFormInvariants:
    """Verify W-2 tax rate invariants."""

    def test_valid_ss_tax(self):
        state = mock_state(
            social_security_wages=100000.0,
            social_security_tax_withheld=6200.0,
        )
        ok, msg = _check_ss_tax(state)
        assert ok is True

    def test_invalid_ss_tax(self):
        state = mock_state(
            social_security_wages=100000.0,
            social_security_tax_withheld=5000.0,
        )
        ok, msg = _check_ss_tax(state)
        assert ok is False

    def test_valid_medicare_tax(self):
        state = mock_state(
            medicare_wages=100000.0,
            medicare_tax_withheld=1450.0,
        )
        ok, msg = _check_medicare_tax(state)
        assert ok is True

    def test_invalid_medicare_tax(self):
        state = mock_state(
            medicare_wages=100000.0,
            medicare_tax_withheld=1000.0,
        )
        ok, msg = _check_medicare_tax(state)
        assert ok is False


class TestPayStubInvariants:
    """Verify pay stub net pay invariant."""

    def test_valid_net_pay(self):
        deductions = MockFieldValue(
            [
                {"amount": 100.0},
                {"amount": 50.0},
            ]
        )
        state = mock_state(
            gross_pay=2000.0,
            net_pay=1397.0,
            federal_tax=200.0,
            state_tax=100.0,
            social_security=124.0,
            medicare=29.0,
        )
        state["deductions"] = deductions
        ok, msg = _check_net_pay(state)
        assert ok is True

    def test_invalid_net_pay(self):
        state = mock_state(
            gross_pay=2000.0,
            net_pay=1900.0,
            federal_tax=200.0,
        )
        ok, msg = _check_net_pay(state)
        assert ok is False


class TestInsurancePolicyInvariants:
    """Verify insurance premium sum invariant."""

    def test_valid_premium_sum(self):
        coverages = MockFieldValue(
            [
                {"premium": 500.0},
                {"premium": 300.0},
                {"premium": 200.0},
            ]
        )
        state = {"coverages": coverages, "total_premium": MockFieldValue(1000.0)}
        ok, msg = _check_premium_sum(state)
        assert ok is True

    def test_invalid_premium_sum(self):
        coverages = MockFieldValue(
            [
                {"premium": 500.0},
                {"premium": 300.0},
            ]
        )
        state = {"coverages": coverages, "total_premium": MockFieldValue(1000.0)}
        ok, msg = _check_premium_sum(state)
        assert ok is False


# ---------------------------------------------------------------------------
# Registry resolution tests
# ---------------------------------------------------------------------------


class TestRegistryResolution:
    """Verify new skills and templates are registered in run_engine."""

    def test_all_new_skills_resolvable(self):
        from src.api.run_engine import resolve_skill

        for skill_id in [
            "bank_statement",
            "purchase_order",
            "packing_list",
            "w2_tax_form",
            "pay_stub",
            "insurance_policy",
        ]:
            skill = resolve_skill(skill_id)
            assert skill is not None
            assert skill.name == skill_id

    def test_all_new_templates_resolvable(self):
        from src.api.run_engine import resolve_template

        for template_id in [
            "bank_statement",
            "purchase_order",
            "packing_list",
            "w2_tax_form",
            "pay_stub",
            "insurance_policy",
        ]:
            template_cls = resolve_template(template_id)
            assert template_cls is not None


# ---------------------------------------------------------------------------
# Prebuilt definition tests
# ---------------------------------------------------------------------------


class TestPrebuiltDefinitions:
    """Verify new prebuilt definitions are registered."""

    def test_no_duplicate_definition_ids(self):
        """BLK-172: Ensure no duplicate definition IDs in prebuilt definitions."""
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS

        def_ids = [d["id"] for d in PREBUILT_DEFINITIONS]
        assert len(def_ids) == len(set(def_ids)), (
            f"Duplicate definition IDs: {set(def_ids) - set(def_ids)}"
        )

    def test_all_new_definitions_present(self):
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS

        def_ids = {d["id"] for d in PREBUILT_DEFINITIONS}
        for def_id in [
            "def-bank-statement",
            "def-purchase-order",
            "def-packing-list",
            "def-w2-tax-form",
            "def-pay-stub",
            "def-insurance-policy",
        ]:
            assert def_id in def_ids

    def test_definition_count(self):
        from src.definitions.prebuilt import PREBUILT_DEFINITIONS

        assert len(PREBUILT_DEFINITIONS) == 21

    def test_new_skills_in_prebuilt_skills(self):
        from src.definitions.prebuilt import PREBUILT_SKILLS

        skill_ids = {s["id"] for s in PREBUILT_SKILLS}
        for skill_id in [
            "bank_statement",
            "purchase_order",
            "packing_list",
            "w2_tax_form",
            "pay_stub",
            "insurance_policy",
        ]:
            assert skill_id in skill_ids

    def test_new_templates_in_prebuilt_templates(self):
        from src.definitions.prebuilt import PREBUILT_TEMPLATES

        template_ids = {t["id"] for t in PREBUILT_TEMPLATES}
        for template_id in [
            "bank_statement",
            "purchase_order",
            "packing_list",
            "w2_tax_form",
            "pay_stub",
            "insurance_policy",
        ]:
            assert template_id in template_ids
