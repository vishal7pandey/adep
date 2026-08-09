"""Tests for VLM fallback patterns [BLK-044, TS].

Tests cover:
- VLM_FALLBACK_ACTIONS contains all gap types
- GEOMETRY_FIRST_PROBE_ORDER structure
- Handwriting bypass: should_bypass_ocr for various region types
- Escalation steps for low-confidence OCR
- Escalation steps for high-confidence (no escalation)
- Fallback actions reference geometry tools (deskew, denoise, threshold)
- Fallback actions reference VLM as final escalation
"""

from __future__ import annotations

import pytest

from src.agent.validator import GapType
from src.skills.vlm_fallback import (
    GEOMETRY_FIRST_PROBE_ORDER,
    HANDWRITING_BYPASS_REGION_TYPES,
    HANDWRITING_TOOL_PREFERENCE,
    VLM_FALLBACK_ACTIONS,
    get_escalation_steps,
    should_bypass_ocr,
)


class TestVLMFallbackActions:
    """Verify VLM_FALLBACK_ACTIONS covers all gap types."""

    def test_covers_low_confidence(self):
        assert GapType.LOW_CONFIDENCE in VLM_FALLBACK_ACTIONS
        action = VLM_FALLBACK_ACTIONS[GapType.LOW_CONFIDENCE]
        assert "deskew" in action.lower()
        assert "denoise" in action.lower()
        assert "vlm" in action.lower()

    def test_covers_missing(self):
        assert GapType.MISSING in VLM_FALLBACK_ACTIONS
        action = VLM_FALLBACK_ACTIONS[GapType.MISSING]
        assert "detect_layout" in action
        assert "vlm" in action.lower()

    def test_covers_type_error(self):
        assert GapType.TYPE_ERROR in VLM_FALLBACK_ACTIONS
        action = VLM_FALLBACK_ACTIONS[GapType.TYPE_ERROR]
        assert "vlm" in action.lower()

    def test_covers_format_error(self):
        assert GapType.FORMAT_ERROR in VLM_FALLBACK_ACTIONS
        action = VLM_FALLBACK_ACTIONS[GapType.FORMAT_ERROR]
        assert "deskew" in action.lower() or "vlm" in action.lower()

    def test_covers_ungrounded(self):
        assert GapType.UNGROUNDED in VLM_FALLBACK_ACTIONS

    def test_covers_invariant_failed(self):
        assert GapType.INVARIANT_FAILED in VLM_FALLBACK_ACTIONS
        action = VLM_FALLBACK_ACTIONS[GapType.INVARIANT_FAILED]
        assert "deskew" in action.lower()
        assert "vlm" in action.lower()

    def test_covers_semantic_fail(self):
        assert GapType.SEMANTIC_FAIL in VLM_FALLBACK_ACTIONS
        action = VLM_FALLBACK_ACTIONS[GapType.SEMANTIC_FAIL]
        assert "vlm" in action.lower()

    def test_all_actions_mention_vlm_as_escalation(self):
        """Every action (except UNGROUNDED which is about bbox tracing) should mention vlm."""
        for gap_type, action in VLM_FALLBACK_ACTIONS.items():
            if gap_type == GapType.UNGROUNDED:
                continue  # Grounding is about bbox tracing, not OCR escalation
            assert "vlm" in action.lower(), (
                f"Action for {gap_type} does not mention VLM escalation"
            )


class TestGeometryFirstProbeOrder:
    """Verify GEOMETRY_FIRST_PROBE_ORDER structure."""

    def test_has_header_first(self):
        assert GEOMETRY_FIRST_PROBE_ORDER[0][0] == "header"
        assert "deskew" in GEOMETRY_FIRST_PROBE_ORDER[0][1].lower()

    def test_has_handwriting_entry(self):
        types = [t for t, _ in GEOMETRY_FIRST_PROBE_ORDER]
        assert "handwriting" in types

    def test_handwriting_bypasses_ocr(self):
        handwriting_entry = next(
            (t, r) for t, r in GEOMETRY_FIRST_PROBE_ORDER if t == "handwriting"
        )
        assert "bypass" in handwriting_entry[1].lower() or "vlm" in handwriting_entry[1].lower()

    def test_has_figure_entry(self):
        types = [t for t, _ in GEOMETRY_FIRST_PROBE_ORDER]
        assert "figure" in types

    def test_figure_routes_to_read_chart(self):
        figure_entry = next(
            (t, r) for t, r in GEOMETRY_FIRST_PROBE_ORDER if t == "figure"
        )
        assert "read_chart" in figure_entry[1].lower() or "vlm" in figure_entry[1].lower()


class TestShouldBypassOCR:
    """Verify should_bypass_ocr for various region types."""

    def test_handwriting_bypasses(self):
        assert should_bypass_ocr("handwriting") is True

    def test_stamp_bypasses(self):
        assert should_bypass_ocr("stamp") is True

    def test_logo_bypasses(self):
        assert should_bypass_ocr("logo") is True

    def test_text_does_not_bypass(self):
        assert should_bypass_ocr("text") is False

    def test_table_does_not_bypass(self):
        assert should_bypass_ocr("table") is False

    def test_case_insensitive(self):
        assert should_bypass_ocr("HANDWRITING") is True
        assert should_bypass_ocr("Handwriting") is True

    def test_unknown_type_does_not_bypass(self):
        assert should_bypass_ocr("unknown") is False

    def test_bypass_types_constant(self):
        assert "handwriting" in HANDWRITING_BYPASS_REGION_TYPES
        assert "stamp" in HANDWRITING_BYPASS_REGION_TYPES
        assert "logo" in HANDWRITING_BYPASS_REGION_TYPES
        assert "text" not in HANDWRITING_BYPASS_REGION_TYPES

    def test_handwriting_tool_preference_is_vlm(self):
        assert HANDWRITING_TOOL_PREFERENCE == "vlm"


class TestGetEscalationSteps:
    """Verify escalation step generation for failed OCR."""

    def test_low_confidence_ocr_escalation(self):
        steps = get_escalation_steps("ocr", confidence=0.3, threshold=0.5)
        assert len(steps) > 0
        assert "crop" in steps
        assert "deskew" in steps
        assert "denoise" in steps
        assert "threshold" in steps
        assert "ocr" in steps  # retry OCR after geometry corrections
        assert "vlm" in steps  # final escalation to VLM
        assert steps[-1] == "vlm"  # VLM is the last resort

    def test_high_confidence_no_escalation(self):
        steps = get_escalation_steps("ocr", confidence=0.9, threshold=0.5)
        assert steps == []

    def test_confidence_at_threshold_no_escalation(self):
        steps = get_escalation_steps("ocr", confidence=0.5, threshold=0.5)
        assert steps == []

    def test_non_ocr_failure_escalates_to_vlm(self):
        steps = get_escalation_steps("vlm", confidence=0.2, threshold=0.5)
        assert steps == ["vlm"]

    def test_escalation_order_is_correct(self):
        """Verify the escalation follows: crop → deskew → denoise → threshold → ocr → vlm."""
        steps = get_escalation_steps("ocr", confidence=0.1, threshold=0.5)
        expected = ["crop", "deskew", "denoise", "threshold", "ocr", "vlm"]
        assert steps == expected

    def test_custom_threshold(self):
        """Higher threshold triggers escalation more aggressively."""
        steps = get_escalation_steps("ocr", confidence=0.7, threshold=0.8)
        assert len(steps) > 0  # 0.7 < 0.8, so escalate

        steps = get_escalation_steps("ocr", confidence=0.85, threshold=0.8)
        assert steps == []  # 0.85 >= 0.8, no escalation
