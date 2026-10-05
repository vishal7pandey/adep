"""Circular reasoning & loop detection [BLK-082].

Detect when the agent is stuck in a loop — repeating the same tool calls,
visiting the same fields, or producing the same thoughts across cycles.
Terminate the run gracefully when a loop is detected.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# Default thresholds
TOOL_REPETITION_THRESHOLD = 3
OSCILLATION_THRESHOLD = 4
THOUGHT_SIMILARITY_THRESHOLD = 0.95
THOUGHT_SIMILARITY_CONSECUTIVE = 3


class LoopType(str, Enum):
    """Type of detected loop [BLK-082]."""

    TOOL_REPETITION = "tool_repetition"
    FIELD_RE_EXTRACTION = "field_re_extraction"
    THOUGHT_SIMILARITY = "thought_similarity"
    OSCILLATION = "oscillation"
    NO_PROGRESS = "no_progress"
    NONE = "none"


@dataclass
class LoopReport:
    """Report generated when a loop is detected [BLK-082].

    Attributes:
        loop_type: Type of loop detected.
        detected: Whether a loop was detected.
        cycle_range: (start_cycle, end_cycle) of the repeated pattern.
        summary: Human-readable description of the repeated pattern.
    """

    loop_type: LoopType
    detected: bool
    cycle_range: tuple[int, int] = (0, 0)
    summary: str = ""


class LoopDetector:
    """Detects circular reasoning and repetitive loops [BLK-082].

    Tracks tool calls, field attempts, and thought patterns across cycles
    to detect various forms of loops.

    Attributes:
        tool_call_history: List of (tool_name, args_hash) per cycle.
        field_attempt_history: List of field names attempted per cycle.
        thought_history: List of thought texts per cycle.
        extracted_counts: List of extracted_fields_count per cycle.
    """

    def __init__(
        self,
        max_cycles_per_field: int = 5,
        max_cycles_per_document: int = 30,
    ) -> None:
        self.max_cycles_per_field = max_cycles_per_field
        self.max_cycles_per_document = max_cycles_per_document
        self.tool_call_history: list[tuple[str, str]] = []
        self.field_attempt_history: list[str] = []
        self.thought_history: list[str] = []
        self.extracted_counts: list[int] = []
        self._cycle: int = 0

    def record_cycle(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        field: str | None,
        thought: str,
        extracted_count: int,
    ) -> None:
        """Record a cycle's activity for loop detection [BLK-082]."""
        args_hash = str(sorted(tool_args.items()))
        self.tool_call_history.append((tool_name, args_hash))
        self.field_attempt_history.append(field or "")
        self.thought_history.append(thought)
        self.extracted_counts.append(extracted_count)
        self._cycle += 1

    def check_tool_repetition(self) -> LoopReport:
        """Check if the same tool+args have been called for N consecutive cycles [BLK-082]."""
        if len(self.tool_call_history) < TOOL_REPETITION_THRESHOLD:
            return LoopReport(loop_type=LoopType.TOOL_REPETITION, detected=False)

        recent = self.tool_call_history[-TOOL_REPETITION_THRESHOLD:]
        if all(call == recent[0] for call in recent):
            start = self._cycle - TOOL_REPETITION_THRESHOLD
            return LoopReport(
                loop_type=LoopType.TOOL_REPETITION,
                detected=True,
                cycle_range=(start, self._cycle),
                summary=f"Tool '{recent[0][0]}' called with same args for {TOOL_REPETITION_THRESHOLD} consecutive cycles",
            )
        return LoopReport(loop_type=LoopType.TOOL_REPETITION, detected=False)

    def check_field_re_extraction(self) -> LoopReport:
        """Check if a field has been re-extracted too many times [BLK-082]."""
        from collections import Counter

        field_counts = Counter(self.field_attempt_history)
        for field, count in field_counts.items():
            if field and count > self.max_cycles_per_field:
                return LoopReport(
                    loop_type=LoopType.FIELD_RE_EXTRACTION,
                    detected=True,
                    cycle_range=(0, self._cycle),
                    summary=f"Field '{field}' re-extracted {count} times (max: {self.max_cycles_per_field})",
                )
        return LoopReport(loop_type=LoopType.FIELD_RE_EXTRACTION, detected=False)

    def check_thought_similarity(self) -> LoopReport:
        """Check for circular reasoning via thought similarity [BLK-082].

        Uses simple Jaccard similarity on word sets as a lightweight
        proxy for embedding similarity. For production, replace with
        actual embedding cosine similarity.
        """
        if len(self.thought_history) < THOUGHT_SIMILARITY_CONSECUTIVE:
            return LoopReport(loop_type=LoopType.THOUGHT_SIMILARITY, detected=False)

        recent = self.thought_history[-THOUGHT_SIMILARITY_CONSECUTIVE:]

        # Compute pairwise Jaccard similarity
        for i in range(len(recent) - 1):
            words_a = set(recent[i].lower().split())
            words_b = set(recent[i + 1].lower().split())
            if not words_a and not words_b:
                similarity = 1.0
            elif not words_a or not words_b:
                similarity = 0.0
            else:
                similarity = len(words_a & words_b) / len(words_a | words_b)

            if similarity < THOUGHT_SIMILARITY_THRESHOLD:
                return LoopReport(loop_type=LoopType.THOUGHT_SIMILARITY, detected=False)

        start = self._cycle - THOUGHT_SIMILARITY_CONSECUTIVE
        return LoopReport(
            loop_type=LoopType.THOUGHT_SIMILARITY,
            detected=True,
            cycle_range=(start, self._cycle),
            summary=f"Thought similarity > {THOUGHT_SIMILARITY_THRESHOLD} for {THOUGHT_SIMILARITY_CONSECUTIVE} consecutive cycles",
        )

    def check_oscillation(self) -> LoopReport:
        """Check if the agent is oscillating between two states [BLK-082]."""
        if len(self.field_attempt_history) < OSCILLATION_THRESHOLD:
            return LoopReport(loop_type=LoopType.OSCILLATION, detected=False)

        recent = self.field_attempt_history[-OSCILLATION_THRESHOLD:]
        unique_fields = set(recent)

        if len(unique_fields) == 2:
            # Check if it's alternating
            if recent[0] == recent[2] and recent[1] == recent[3]:
                start = self._cycle - OSCILLATION_THRESHOLD
                return LoopReport(
                    loop_type=LoopType.OSCILLATION,
                    detected=True,
                    cycle_range=(start, self._cycle),
                    summary=f"Oscillating between fields '{recent[0]}' and '{recent[1]}' for {OSCILLATION_THRESHOLD} cycles",
                )
        return LoopReport(loop_type=LoopType.OSCILLATION, detected=False)

    def check_no_progress(self) -> LoopReport:
        """Check if extracted_fields_count has not increased [BLK-082]."""
        no_progress_threshold = max(1, self.max_cycles_per_document // 3)

        if len(self.extracted_counts) < no_progress_threshold:
            return LoopReport(loop_type=LoopType.NO_PROGRESS, detected=False)

        recent = self.extracted_counts[-no_progress_threshold:]
        if all(count == recent[0] for count in recent):
            start = self._cycle - no_progress_threshold
            return LoopReport(
                loop_type=LoopType.NO_PROGRESS,
                detected=True,
                cycle_range=(start, self._cycle),
                summary=f"No progress in extracted fields for {no_progress_threshold} cycles",
            )
        return LoopReport(loop_type=LoopType.NO_PROGRESS, detected=False)

    def check_all(self) -> LoopReport:
        """Run all loop detection checks and return the first match [BLK-082]."""
        for check in [
            self.check_tool_repetition,
            self.check_oscillation,
            self.check_no_progress,
            self.check_thought_similarity,
            self.check_field_re_extraction,
        ]:
            report = check()
            if report.detected:
                logger.warning(
                    "Loop detected: %s — %s [BLK-082]", report.loop_type.value, report.summary
                )
                return report

        return LoopReport(loop_type=LoopType.NONE, detected=False)
