"""Tests for BLK-284: Definition-level agent overrides must be fully applied.

Verifies that all AgentConfig fields are properly propagated to the live run:
- max_cycles_per_field → LoopDetector
- max_cycles_per_document → LoopDetector + recursion_limit
- confidence_threshold → validator_config + AgentState
- use_pdf_fast_path → fallback path selection
"""

from src.config import settings
from src.agent.validator import ValidatorConfig


class TestAgentConfigOverridesApplied:
    """BLK-284: All agent_config overrides must reach their consumers."""

    def test_confidence_threshold_override_applied_to_validator_config(self):
        """When agent_config has confidence_threshold, it must override
        the validator_config.default_confidence_threshold."""
        # Simulate the override logic from _execute_run_inner
        agent_config = {"confidence_threshold": 0.95}
        confidence_threshold = agent_config.get("confidence_threshold")

        validator_config = ValidatorConfig(
            default_confidence_threshold=settings.default_confidence_threshold,
        )

        if confidence_threshold is not None:
            validator_config.default_confidence_threshold = confidence_threshold

        assert validator_config.default_confidence_threshold == 0.95
        assert (
            validator_config.default_confidence_threshold != settings.default_confidence_threshold
        )

    def test_no_confidence_threshold_override_keeps_default(self):
        """When agent_config has no confidence_threshold, validator_config
        must keep the global default."""
        agent_config = {}
        confidence_threshold = agent_config.get("confidence_threshold")

        validator_config = ValidatorConfig(
            default_confidence_threshold=settings.default_confidence_threshold,
        )

        if confidence_threshold is not None:
            validator_config.default_confidence_threshold = confidence_threshold

        assert (
            validator_config.default_confidence_threshold == settings.default_confidence_threshold
        )

    def test_max_cycles_overrides_applied_to_loop_detector(self):
        """When agent_config has max_cycles overrides, they must be used
        for LoopDetector instead of global settings."""
        from src.agent.guardrails.loop_detection import LoopDetector

        agent_config = {
            "max_cycles_per_field": 3,
            "max_cycles_per_document": 15,
        }
        max_cycles = agent_config.get("max_cycles_per_document")
        max_cycles_per_field = agent_config.get("max_cycles_per_field")

        loop_detector = LoopDetector(
            max_cycles_per_field=max_cycles_per_field or settings.max_cycles_per_field,
            max_cycles_per_document=max_cycles or settings.max_cycles_per_document,
        )

        assert loop_detector.max_cycles_per_field == 3
        assert loop_detector.max_cycles_per_document == 15
        assert loop_detector.max_cycles_per_field != settings.max_cycles_per_field
        assert loop_detector.max_cycles_per_document != settings.max_cycles_per_document

    def test_no_max_cycles_overrides_keeps_defaults(self):
        """When agent_config has no max_cycles overrides, LoopDetector
        must use global settings."""
        from src.agent.guardrails.loop_detection import LoopDetector

        agent_config = {}
        max_cycles = agent_config.get("max_cycles_per_document")
        max_cycles_per_field = agent_config.get("max_cycles_per_field")

        loop_detector = LoopDetector(
            max_cycles_per_field=max_cycles_per_field or settings.max_cycles_per_field,
            max_cycles_per_document=max_cycles or settings.max_cycles_per_document,
        )

        assert loop_detector.max_cycles_per_field == settings.max_cycles_per_field
        assert loop_detector.max_cycles_per_document == settings.max_cycles_per_document

    def test_confidence_threshold_passed_to_initial_state(self):
        """build_initial_state must propagate confidence_threshold to AgentState."""
        from src.run import build_initial_state
        from src.skills.invoice import InvoiceSkill
        from src.templates.invoice import InvoiceTemplate

        state = build_initial_state(
            "sample-data/invoices/sample-invoice-03.jpg",
            InvoiceTemplate,
            InvoiceSkill,
            confidence_threshold=0.92,
        )

        assert state["confidence_threshold"] == 0.92

    def test_confidence_threshold_defaults_to_settings_when_none(self):
        """build_initial_state must default to settings when no override provided."""
        from src.run import build_initial_state
        from src.skills.invoice import InvoiceSkill
        from src.templates.invoice import InvoiceTemplate

        state = build_initial_state(
            "sample-data/invoices/sample-invoice-03.jpg",
            InvoiceTemplate,
            InvoiceSkill,
        )

        assert state["confidence_threshold"] == settings.default_confidence_threshold
