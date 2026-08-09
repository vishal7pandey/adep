"""Tests for Industry Skill Library [BLK-042, §14, TS].

Tests cover:
- Each skill has: name, system_prompt, tool_preferences, probe_order, invariants, failure_actions
- TradeFinanceScrutinySkill: date arithmetic invariants
- BillOfQuantitiesSkill: qty×rate=total and subtotal+vat=grand_total invariants
- UtilityBillSkill: read_chart tool preference, usage non-negative invariant
- Each template has the expected fields
- VLM fallback actions integrated in each skill
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.agent.validator import GapType
from src.skills.base import Skill
from src.skills.bill_of_quantities import BillOfQuantitiesSkill
from src.skills.trade_finance import TradeFinanceScrutinySkill
from src.skills.utility_bill import UtilityBillSkill
from src.templates.base import Template
from src.templates.bill_of_quantities import BillOfQuantitiesTemplate
from src.templates.trade_finance import TradeFinanceTemplate
from src.templates.utility_bill import UtilityBillTemplate
from src.tools.base import FieldValue, Grounding


def _fv(value: any, name: str = "") -> FieldValue:
    """Build a FieldValue with grounding for testing."""
    return FieldValue(
        name=name or "test",
        value=value,
        grounding=Grounding(bbox=(0, 0, 100, 50), source_tool="ocr", confidence=0.9),
        confidence=0.9,
    )


class TestSkillStructure:
    """Verify all 3 skills have required attributes."""

    @pytest.mark.parametrize("skill,expected_name", [
        (TradeFinanceScrutinySkill, "trade_finance_scrutiny"),
        (BillOfQuantitiesSkill, "bill_of_quantities"),
        (UtilityBillSkill, "utility_bill"),
    ])
    def test_skill_name(self, skill: Skill, expected_name: str):
        assert skill.name == expected_name

    @pytest.mark.parametrize("skill", [
        TradeFinanceScrutinySkill,
        BillOfQuantitiesSkill,
        UtilityBillSkill,
    ])
    def test_has_system_prompt(self, skill: Skill):
        assert len(skill.system_prompt) > 100
        assert "extract" in skill.system_prompt.lower()

    @pytest.mark.parametrize("skill", [
        TradeFinanceScrutinySkill,
        BillOfQuantitiesSkill,
        UtilityBillSkill,
    ])
    def test_has_tool_preferences(self, skill: Skill):
        assert len(skill.tool_preferences) > 0
        assert "text" in skill.tool_preferences

    @pytest.mark.parametrize("skill", [
        TradeFinanceScrutinySkill,
        BillOfQuantitiesSkill,
        UtilityBillSkill,
    ])
    def test_has_probe_order(self, skill: Skill):
        assert len(skill.probe_order) > 0
        assert all(isinstance(t, tuple) and len(t) == 2 for t in skill.probe_order)

    @pytest.mark.parametrize("skill", [
        TradeFinanceScrutinySkill,
        BillOfQuantitiesSkill,
        UtilityBillSkill,
    ])
    def test_has_invariants(self, skill: Skill):
        assert len(skill.invariants) > 0

    @pytest.mark.parametrize("skill", [
        TradeFinanceScrutinySkill,
        BillOfQuantitiesSkill,
        UtilityBillSkill,
    ])
    def test_has_failure_actions(self, skill: Skill):
        assert len(skill.failure_actions) > 0
        assert GapType.MISSING in skill.failure_actions

    @pytest.mark.parametrize("skill", [
        TradeFinanceScrutinySkill,
        BillOfQuantitiesSkill,
        UtilityBillSkill,
    ])
    def test_has_known_failures(self, skill: Skill):
        assert len(skill.known_failures) > 0

    @pytest.mark.parametrize("skill", [
        TradeFinanceScrutinySkill,
        BillOfQuantitiesSkill,
        UtilityBillSkill,
    ])
    def test_has_confidence_overrides(self, skill: Skill):
        assert len(skill.confidence_overrides) > 0


class TestTradeFinanceSkill:
    """TradeFinanceScrutinySkill specific tests."""

    def test_expiry_after_issue_passes(self):
        """Expiry date after issue date — invariant passes."""
        extraction = {
            "issue_date": _fv("2026-01-15", "issue_date"),
            "expiry_date": _fv("2026-06-15", "expiry_date"),
        }
        inv = TradeFinanceScrutinySkill.invariants[0]
        result, msg = inv.fn(extraction)
        assert result is True

    def test_expiry_after_issue_fails(self):
        """Expiry date before issue date — invariant fails."""
        extraction = {
            "issue_date": _fv("2026-06-15", "issue_date"),
            "expiry_date": _fv("2026-01-15", "expiry_date"),
        }
        inv = TradeFinanceScrutinySkill.invariants[0]
        result, msg = inv.fn(extraction)
        assert result is False

    def test_shipment_before_expiry_passes(self):
        """Shipment date before expiry — invariant passes."""
        extraction = {
            "latest_shipment_date": _fv("2026-05-01", "latest_shipment_date"),
            "expiry_date": _fv("2026-06-15", "expiry_date"),
        }
        inv = TradeFinanceScrutinySkill.invariants[1]
        result, msg = inv.fn(extraction)
        assert result is True

    def test_shipment_before_expiry_fails(self):
        """Shipment date after expiry — invariant fails."""
        extraction = {
            "latest_shipment_date": _fv("2026-07-01", "latest_shipment_date"),
            "expiry_date": _fv("2026-06-15", "expiry_date"),
        }
        inv = TradeFinanceScrutinySkill.invariants[1]
        result, msg = inv.fn(extraction)
        assert result is False

    def test_system_prompt_mentions_mt700(self):
        assert "MT700" in TradeFinanceScrutinySkill.system_prompt

    def test_failure_actions_have_vlm_fallback(self):
        action = TradeFinanceScrutinySkill.failure_actions[GapType.LOW_CONFIDENCE]
        assert "vlm" in action.lower()


class TestBillOfQuantitiesSkill:
    """BillOfQuantitiesSkill specific tests."""

    def test_qty_rate_total_passes(self):
        """qty × rate = total for all items — invariant passes."""
        extraction = {
            "line_items": _fv([
                {"item_no": 1, "description": "Excavation", "unit": "m³", "quantity": 100, "rate": 50, "total": 5000},
                {"item_no": 2, "description": "Concrete", "unit": "m³", "quantity": 200, "rate": 150, "total": 30000},
            ], "line_items"),
        }
        inv = BillOfQuantitiesSkill.invariants[0]
        result, msg = inv.fn(extraction)
        assert result is True

    def test_qty_rate_total_fails(self):
        """qty × rate ≠ total — invariant fails."""
        extraction = {
            "line_items": _fv([
                {"item_no": 1, "description": "Excavation", "unit": "m³", "quantity": 100, "rate": 50, "total": 6000},
            ], "line_items"),
        }
        inv = BillOfQuantitiesSkill.invariants[0]
        result, msg = inv.fn(extraction)
        assert result is False
        assert "100" in msg and "50" in msg

    def test_subtotal_vat_grand_total_passes(self):
        """subtotal + vat = grand_total — invariant passes."""
        extraction = {
            "subtotal": _fv(35000.0, "subtotal"),
            "vat_amount": _fv(5250.0, "vat_amount"),
            "grand_total": _fv(40250.0, "grand_total"),
        }
        inv = BillOfQuantitiesSkill.invariants[1]
        result, msg = inv.fn(extraction)
        assert result is True

    def test_subtotal_vat_grand_total_fails(self):
        """subtotal + vat ≠ grand_total — invariant fails."""
        extraction = {
            "subtotal": _fv(35000.0, "subtotal"),
            "vat_amount": _fv(5250.0, "vat_amount"),
            "grand_total": _fv(50000.0, "grand_total"),
        }
        inv = BillOfQuantitiesSkill.invariants[1]
        result, msg = inv.fn(extraction)
        assert result is False

    def test_tool_preferences_table_is_read_table(self):
        assert BillOfQuantitiesSkill.tool_preferences.get("table") == "read_table"


class TestUtilityBillSkill:
    """UtilityBillSkill specific tests."""

    def test_chart_tool_preference_is_read_chart(self):
        assert UtilityBillSkill.tool_preferences.get("chart") == "read_chart"

    def test_figure_tool_preference_is_read_chart(self):
        assert UtilityBillSkill.tool_preferences.get("figure") == "read_chart"

    def test_usage_non_negative_passes(self):
        extraction = {
            "current_usage": _fv(350.0, "current_usage"),
            "previous_usage": _fv(400.0, "previous_usage"),
        }
        inv = UtilityBillSkill.invariants[0]
        result, msg = inv.fn(extraction)
        assert result is True

    def test_usage_negative_fails(self):
        extraction = {
            "current_usage": _fv(-50.0, "current_usage"),
            "previous_usage": _fv(400.0, "previous_usage"),
        }
        inv = UtilityBillSkill.invariants[0]
        result, msg = inv.fn(extraction)
        assert result is False

    def test_probe_order_includes_chart(self):
        types = [t for t, _ in UtilityBillSkill.probe_order]
        assert "chart" in types

    def test_system_prompt_mentions_read_chart(self):
        assert "read_chart" in UtilityBillSkill.system_prompt


class TestTemplates:
    """Verify each template has the expected fields."""

    def test_trade_finance_template_fields(self):
        fields = TradeFinanceTemplate.model_fields
        assert "lc_number" in fields
        assert "lc_amount" in fields
        assert "currency" in fields
        assert "issue_date" in fields
        assert "expiry_date" in fields
        assert "applicant" in fields
        assert "beneficiary" in fields

    def test_boq_template_fields(self):
        fields = BillOfQuantitiesTemplate.model_fields
        assert "project_name" in fields
        assert "line_items" in fields
        assert "subtotal" in fields
        assert "vat_amount" in fields
        assert "grand_total" in fields

    def test_utility_bill_template_fields(self):
        fields = UtilityBillTemplate.model_fields
        assert "account_number" in fields
        assert "current_usage" in fields
        assert "amount_due" in fields
        assert "consumption_history" in fields
        assert "utility_type" in fields

    def test_all_templates_extend_base(self):
        assert issubclass(TradeFinanceTemplate, Template)
        assert issubclass(BillOfQuantitiesTemplate, Template)
        assert issubclass(UtilityBillTemplate, Template)
