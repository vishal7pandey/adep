"""Risk tier classification for HITL gate pattern [BLK-047, §13].

Classifies extraction actions by risk level to determine gating:
- Low: auto-execute (OCR, VLM, geometry — no gate)
- Medium: flag for review, non-blocking, auto-accept after timeout
- High: blocking gate — user must approve or reject
- Critical: explicit sign-off for partial termination
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskTier(str, Enum):
    """Risk tier for agent actions [BLK-047]."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GateDecision:
    """Result of risk tier evaluation for a field [BLK-047].

    Attributes:
        tier: Risk tier assigned.
        requires_gate: Whether a blocking gate is triggered.
        auto_timeout_seconds: Seconds before auto-action (0 = no timeout).
        auto_action_on_timeout: What happens on timeout ("accept" or "reject").
        reason: Why this tier was assigned.
    """

    tier: RiskTier
    requires_gate: bool
    auto_timeout_seconds: int
    auto_action_on_timeout: str
    reason: str


# Timeout settings per tier [BLK-047]
_MEDIUM_TIMEOUT_SECONDS = 60
_HIGH_TIMEOUT_SECONDS = 0  # No auto-timeout for high (deny by default on manual timeout)


def classify_extraction_risk(
    confidence: float,
    semantic_failed: bool = False,
    is_partial_termination: bool = False,
) -> GateDecision:
    """Classify the risk of an extraction action [BLK-047].

    Args:
        confidence: Confidence score of the extracted value (0.0 to 1.0).
        semantic_failed: Whether the semantic check failed for this field.
        is_partial_termination: Whether the agent wants to terminate with
            a partial result (give up on remaining fields).

    Returns:
        GateDecision with tier, gating requirement, and timeout behavior.
    """
    if is_partial_termination:
        return GateDecision(
            tier=RiskTier.CRITICAL,
            requires_gate=True,
            auto_timeout_seconds=0,
            auto_action_on_timeout="reject",
            reason="Agent wants to terminate with partial result — explicit sign-off required",
        )

    if semantic_failed or confidence < 0.5:
        return GateDecision(
            tier=RiskTier.HIGH,
            requires_gate=True,
            auto_timeout_seconds=_HIGH_TIMEOUT_SECONDS,
            auto_action_on_timeout="reject",
            reason=f"Confidence {confidence:.2f} < 0.5 or semantic check failed — pre-execution review required",
        )

    if confidence < 0.8:
        return GateDecision(
            tier=RiskTier.MEDIUM,
            requires_gate=False,  # Non-blocking — flagged but doesn't pause
            auto_timeout_seconds=_MEDIUM_TIMEOUT_SECONDS,
            auto_action_on_timeout="accept",
            reason=f"Confidence {confidence:.2f} in [0.5, 0.8) — flagged for review, auto-accept after {_MEDIUM_TIMEOUT_SECONDS}s",
        )

    return GateDecision(
        tier=RiskTier.LOW,
        requires_gate=False,
        auto_timeout_seconds=0,
        auto_action_on_timeout="accept",
        reason=f"Confidence {confidence:.2f} >= 0.8 — auto-execute, no gate",
    )
