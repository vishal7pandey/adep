"""Budget-aware planning for the new engine (ADE-35).

Treats tokens, tool calls, and latency as first-class quantities the agent reasons about
rather than afterthoughts. The agent calls budget_status to see what it can still afford and
adapts its strategy: on a dense drawing with 22 entities and 10 turns left, it should batch
crops rather than reading one entity per turn. This module only reports status — it never
refuses a record or stops the agent; the agent decides what to do with the numbers.

Ported from ade2's src/ade2/budget.py (read in full as part of ADE-30).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Budget:
    """Resource limits for a single extraction run."""

    max_turns: int = 30
    max_cost_usd: float = 2.0
    max_seconds: float = 600.0


@dataclass
class Spend:
    """Accumulated resource consumption."""

    turns: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0

    def remaining(self, budget: Budget) -> "Spend":
        """How much of each resource is left (never negative)."""
        return Spend(
            turns=max(0, budget.max_turns - self.turns),
            cost_usd=max(0.0, budget.max_cost_usd - self.cost_usd),
            seconds=max(0.0, budget.max_seconds - self.seconds),
        )

    def fraction_used(self, budget: Budget) -> dict[str, float]:
        """Fraction of each budget consumed (0.0 to 1.0+); guards against a zero budget."""
        return {
            "turns": self.turns / budget.max_turns if budget.max_turns else 0.0,
            "cost": self.cost_usd / budget.max_cost_usd if budget.max_cost_usd else 0.0,
            "time": self.seconds / budget.max_seconds if budget.max_seconds else 0.0,
        }


# Estimated cost per tool type. Local tools (validate_extraction, to_dexpi_xml,
# to_spice_netlist, update_plan, list_document_pages) cost 0 turns because they don't
# require a model response. Perception tools (survey, crop, OCR) each consume one model turn.
TOOL_TURNS: dict[str, int] = {
    "survey_layout_tool": 1,
    "survey_region_tool": 1,
    "crop_and_read_tool": 1,
    "ocr_page_tool": 1,
    "validate_extraction": 0,
    "to_dexpi_xml": 0,
    "to_spice_netlist": 0,
    "update_plan": 0,
    "list_document_pages": 0,
    "budget_status": 0,
    "final_result": 0,
}

# Estimated dollar cost per LLM tool call (starting point from ade2's observed eval data;
# ADE-31's head-to-head evaluation is where real cost data will show if these need adjusting).
TOOL_COST_USD: dict[str, float] = {
    "survey_layout_tool": 0.03,
    "survey_region_tool": 0.03,
    "crop_and_read_tool": 0.04,
    "ocr_page_tool": 0.02,
}


@dataclass
class BudgetTracker:
    """Tracks spend against a budget during an extraction run."""

    budget: Budget = field(default_factory=Budget)
    spend: Spend = field(default_factory=Spend)
    start_time: float = field(default_factory=time.time)
    tool_history: list[str] = field(default_factory=list)

    def record_tool(self, tool_name: str) -> None:
        """Record a tool call's estimated cost. An unlisted tool defaults to 1 turn, $0."""
        self.tool_history.append(tool_name)
        self.spend.turns += TOOL_TURNS.get(tool_name, 1)
        self.spend.cost_usd += TOOL_COST_USD.get(tool_name, 0.0)
        self.spend.seconds = time.time() - self.start_time

    def status(self) -> dict[str, Any]:
        """Remaining resources, fraction used, and strategic recommendations."""
        remaining = self.spend.remaining(self.budget)
        fractions = self.spend.fraction_used(self.budget)

        perception_calls = sum(1 for t in self.tool_history if TOOL_TURNS.get(t, 1) > 0)
        local_calls = sum(1 for t in self.tool_history if TOOL_TURNS.get(t, 1) == 0)

        recommendations: list[str] = []
        if remaining.turns <= 3:
            recommendations.append(
                f"Only {remaining.turns} turns left. Prioritize: serialize what you have, "
                "validate, and return. Do NOT start new survey_region calls."
            )
        elif remaining.turns <= 8:
            recommendations.append(
                f"{remaining.turns} turns left. If you have many unread elements from "
                "survey_region, batch them: crop a wider region covering multiple elements "
                "in one call rather than cropping each individually."
            )

        if fractions["turns"] > 0.7 and perception_calls > 0:
            recommendations.append(
                f"You've used {perception_calls} perception calls. Estimate how many "
                "entities you still haven't read. If more than your remaining turns, "
                "you MUST batch — crop wider regions covering multiple symbols."
            )

        if remaining.cost_usd < 0.20:
            recommendations.append(
                f"Only ${remaining.cost_usd:.2f} budget left. Avoid unnecessary crops. "
                "Use validate_extraction (free) to check completeness before spending more."
            )

        return {
            "remaining_turns": remaining.turns,
            "remaining_cost_usd": round(remaining.cost_usd, 4),
            "remaining_seconds": round(remaining.seconds, 1),
            "fraction_used": {k: round(v, 3) for k, v in fractions.items()},
            "perception_calls": perception_calls,
            "local_calls": local_calls,
            "tool_history": self.tool_history,
            "recommendations": recommendations,
        }


def estimate_budget_for_complexity(zone_count: int, image_pixels: int) -> Budget:
    """Scale a starting Budget to a document's apparent complexity.

    Dense drawings (many zones, high resolution) need more turns to crop every region.
    The zone-count contribution is capped so a pathological zone count can't produce an
    unbounded budget.
    """
    base_turns = 15
    zone_turns = min(zone_count * 2, 20)
    resolution_turns = 5 if image_pixels > 4_000_000 else 0

    max_turns = base_turns + zone_turns + resolution_turns
    max_cost = max(1.0, max_turns * 0.05)
    max_seconds = max_turns * 25.0

    budget = Budget(max_turns=max_turns, max_cost_usd=max_cost, max_seconds=max_seconds)
    logger.info(
        "Budget estimated: zones=%d pixels=%d -> turns=%d cost=$%.2f time=%.0fs",
        zone_count,
        image_pixels,
        budget.max_turns,
        budget.max_cost_usd,
        budget.max_seconds,
    )
    return budget
