"""Tests for the deterministic Outcome Validator [§4.1, TS, MLC, NFT].

The validator is pure code with no external calls — these tests verify the
deterministic gap-report logic directly.
"""

from __future__ import annotations

import pytest
from pydantic import Field

from src.agent.validator import (
    FieldGap,
    GapType,
    Invariant,
    ValidatorConfig,
    validate_extraction,
)
from src.templates.base import Template
from src.tools.base import FieldValue, Grounding


class DummyTemplate(Template):
    """Minimal schema for validator tests."""

    name: str = Field(description="A name")
    amount: float = Field(description="A monetary amount")
    date: str = Field(description="ISO date")


def _make_fv(
    value: object,
    confidence: float = 0.9,
    grounded: bool = True,
) -> FieldValue:
    """Helper: build a FieldValue with sensible defaults."""
    return FieldValue(
        name="test",
        value=value,
        grounding=Grounding(bbox=(0, 0, 100, 100)) if grounded else None,
        confidence=confidence,
    )


class TestValidatorPresence:
    """Check 1: required-field presence."""

    def test_missing_field_reported_as_missing(self):
        extraction = {
            "name": _make_fv("Alice"),
            "amount": _make_fv(42.0),
            # date missing
        }
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=ValidatorConfig(),
        )
        assert not report.is_complete
        missing = report.missing_fields()
        assert "date" in missing
        assert "name" not in missing
        assert "amount" not in missing

    def test_all_fields_present_is_complete(self):
        extraction = {
            "name": _make_fv("Alice"),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=ValidatorConfig(),
        )
        assert report.is_complete
        assert len(report.gaps) == 0


class TestValidatorGrounding:
    """Check 4: grounding presence [§2.5]."""

    def test_ungrounded_value_reported(self):
        extraction = {
            "name": _make_fv("Alice", grounded=False),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=ValidatorConfig(),
        )
        ungrounded = report.fields_by_type(GapType.UNGROUNDED)
        assert len(ungrounded) == 1
        assert ungrounded[0].field == "name"


class TestValidatorConfidence:
    """Check 5: confidence >= threshold."""

    def test_low_confidence_reported(self):
        extraction = {
            "name": _make_fv("Alice", confidence=0.5),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=ValidatorConfig(default_confidence_threshold=0.8),
        )
        low = report.fields_by_type(GapType.LOW_CONFIDENCE)
        assert len(low) == 1
        assert low[0].field == "name"

    def test_per_field_threshold_override(self):
        extraction = {
            "name": _make_fv("Alice", confidence=0.6),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=ValidatorConfig(
                default_confidence_threshold=0.8,
                per_field_thresholds={"name": 0.5},
            ),
        )
        assert report.is_complete


class TestValidatorInvariants:
    """Check 3: math invariants."""

    def test_invariant_passes(self):
        extraction = {
            "name": _make_fv("Alice"),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        inv = Invariant(
            name="positive_amount",
            fields=["amount"],
            fn=lambda e: (e["amount"].value > 0, "amount must be positive"),
        )
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[inv],
            config=ValidatorConfig(),
        )
        assert report.is_complete

    def test_invariant_fails(self):
        extraction = {
            "name": _make_fv("Alice"),
            "amount": _make_fv(-5.0),
            "date": _make_fv("2024-01-15"),
        }
        inv = Invariant(
            name="positive_amount",
            fields=["amount"],
            fn=lambda e: (e["amount"].value > 0, "amount must be positive"),
        )
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[inv],
            config=ValidatorConfig(),
        )
        failed = report.fields_by_type(GapType.INVARIANT_FAILED)
        assert len(failed) == 1
        assert failed[0].field == "positive_amount"

    def test_invariant_skipped_if_field_missing(self):
        extraction = {
            "name": _make_fv("Alice"),
            # amount missing
            "date": _make_fv("2024-01-15"),
        }
        inv = Invariant(
            name="positive_amount",
            fields=["amount"],
            fn=lambda e: (e["amount"].value > 0, "amount must be positive"),
        )
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[inv],
            config=ValidatorConfig(),
        )
        # The missing field is reported, but the invariant is not run.
        assert "amount" in report.missing_fields()
        assert len(report.fields_by_type(GapType.INVARIANT_FAILED)) == 0


class TestValidatorFailureActions:
    """Verify failure_actions from the Skill are injected into gaps."""

    def test_suggested_action_injected(self):
        extraction = {
            "name": _make_fv("Alice", grounded=False),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        actions = {
            GapType.UNGROUNDED: "Call the ground tool to trace this value.",
        }
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=ValidatorConfig(),
            failure_actions=actions,
        )
        ungrounded = report.fields_by_type(GapType.UNGROUNDED)
        assert ungrounded[0].suggested_action == "Call the ground tool to trace this value."


class TestValidatorSemanticChecks:
    """Check 6: optional semantic checks (LLM-assisted, off by default) [§4.1]."""

    def test_semantic_check_off_by_default(self):
        extraction = {
            "name": _make_fv("Alice"),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=ValidatorConfig(),
        )
        assert report.is_complete
        assert len(report.fields_by_type(GapType.SEMANTIC_FAIL)) == 0

    def test_semantic_check_fails(self):
        def reject_alice(field: str, value: object, evidence: str) -> tuple[bool, str]:
            if value == "Alice":
                return False, "Alice is not a valid vendor name"
            return True, ""

        extraction = {
            "name": _make_fv("Alice"),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        config = ValidatorConfig(
            semantic_checkers={"name": reject_alice},
        )
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=config,
        )
        assert not report.is_complete
        semantic = report.fields_by_type(GapType.SEMANTIC_FAIL)
        assert len(semantic) == 1
        assert semantic[0].field == "name"
        assert "not a valid vendor" in semantic[0].detail

    def test_semantic_check_passes(self):
        def accept_all(field: str, value: object, evidence: str) -> tuple[bool, str]:
            return True, ""

        extraction = {
            "name": _make_fv("Bob"),
            "amount": _make_fv(42.0),
            "date": _make_fv("2024-01-15"),
        }
        config = ValidatorConfig(
            semantic_checkers={"name": accept_all},
        )
        report = validate_extraction(
            schema=DummyTemplate,
            extraction=extraction,
            invariants=[],
            config=config,
        )
        assert report.is_complete


class TestFieldGapRetryLoopPrevention:
    """Verify last_error and last_tool fields on FieldGap [§12.3]."""

    def test_field_gap_has_last_error_and_last_tool_defaults(self):
        gap = FieldGap(
            field="total",
            gap_type=GapType.MISSING,
            detail="not extracted",
        )
        assert gap.last_error == ""
        assert gap.last_tool == ""

    def test_field_gap_can_carry_last_error(self):
        gap = FieldGap(
            field="total",
            gap_type=GapType.MISSING,
            detail="not extracted",
            last_error="ocr: timeout",
            last_tool="ocr",
        )
        assert gap.last_error == "ocr: timeout"
        assert gap.last_tool == "ocr"
