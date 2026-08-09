"""Skill base class — reusable playbook per document archetype [§3.2].

A Skill bundles everything the agent needs to know about a document type:
  - system prompt
  - tool preferences
  - probe order
  - verification rules (invariants)
  - failure actions (GapType -> suggested action)
  - known failure modes

A Skill is NOT a fixed pipeline — it is advice the agent may follow or
override based on what it observes. Skills compose with any Template.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.agent.validator import GapType, Invariant


@dataclass
class Skill:
    """Reusable extraction playbook for a document archetype.

    Attributes:
        name: Unique skill identifier (e.g. "invoice", "utility_bill").
        system_prompt: Frames the agent for this document type. Stored as
            a constant, not inline [PE].
        tool_preferences: Maps field path or region type -> preferred tool
            (e.g. {"chart": "vlm", "tabular_charges": "ocr"}). The agent
            uses these as defaults but may override.
        probe_order: Ordered list of (region_type, rationale) tuples telling
            the agent which regions to examine first. E.g.
            [("header", "invoice number and date are usually top-right"),
             ("table", "line items are in the main table")].
        invariants: Math/logic verification rules [§4.1]. E.g.
            subtotal + tax == total.
        failure_actions: Maps GapType -> suggested action hint. Injected into
            each FieldGap by the validator. Document-type-specific, lives in
            the Skill, never in the engine [§3.2].
        known_failures: Free-text hints about common failure modes and
            recovery strategies for this document type.
        confidence_overrides: Per-field confidence thresholds that override
            the validator's default.
    """

    name: str
    system_prompt: str
    tool_preferences: dict[str, str] = field(default_factory=dict)
    probe_order: list[tuple[str, str]] = field(default_factory=list)
    invariants: list[Invariant] = field(default_factory=list)
    failure_actions: dict[GapType, str] = field(default_factory=dict)
    known_failures: str = ""
    confidence_overrides: dict[str, float] = field(default_factory=dict)
