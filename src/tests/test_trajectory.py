"""Tests for Trajectory Integrity [BLK-049, §13, TS].

Tests cover:
- SSE trajectory_warning event after 3 non-improving cycles
- SSE trajectory_critical event after 5 non-improving cycles
- consecutive_non_improving counter in AgentState
- reflect_node tracks gap count changes
- Auto-pause on trajectory critical
- Counter resets when gaps improve
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.agent.graph import reflect_node
from src.agent.state import AgentState, RunStatus
from src.agent.validator import (
    FieldGap,
    GapReport,
    GapType,
    ValidatorConfig,
)
from src.api.sse import SSEEventEmitter
from src.skills.invoice import InvoiceSkill
from src.templates.invoice import InvoiceTemplate


def _make_gap_report(gap_count: int, is_complete: bool = False) -> GapReport:
    """Build a GapReport with the given number of gaps."""
    gaps = [
        FieldGap(field=f"f{i}", gap_type=GapType.MISSING, detail="missing")
        for i in range(gap_count)
    ]
    return GapReport(gaps=gaps, satisfied=[], is_complete=is_complete, total_fields=7)


def _make_state(
    prev_gap_count: int = 5,
    consecutive: int = 0,
    status: str = RunStatus.PLANNING,
    total_cycles: int = 0,
    prev_gap_report: GapReport | None | str = "default",
) -> AgentState:
    """Build a minimal AgentState for reflect_node testing.

    Pass prev_gap_report=None explicitly to simulate no previous gap_report.
    Pass prev_gap_report="default" (or omit) to use a GapReport with prev_gap_count gaps.
    """
    if prev_gap_report == "default":
        prev_gap_report = _make_gap_report(prev_gap_count)
    return {
        "document": None,
        "template_schema": InvoiceTemplate,
        "skill_name": "invoice",
        "regions": {},
        "extraction": {},
        "gap_report": prev_gap_report,
        "trace": [],
        "step": 0,
        "field_attempts": {},
        "total_cycles": total_cycles,
        "status": status,
        "attempted": {},
        "provider_errors": [],
        "compaction_summary": "",
        "_planned_action": None,
        "_tool_result": None,
        "_compact_requested": False,
        "consecutive_non_improving": consecutive,
    }


def _run_reflect(
    state: AgentState, new_gap_count: int, is_complete: bool = False
) -> dict[str, Any]:
    """Run reflect_node with a mocked validator returning controlled gap count."""
    with patch(
        "src.agent.graph.validate_extraction",
        return_value=_make_gap_report(new_gap_count, is_complete),
    ):
        return reflect_node(state, skill=InvoiceSkill, validator_config=ValidatorConfig())


class TestSSETrajectoryEvents:
    """Verify SSE trajectory event emitters [BLK-049]."""

    def _collect_events(self, emitter: SSEEventEmitter) -> list[dict[str, Any]]:
        emitter.close()
        loop = asyncio.new_event_loop()
        events = []
        try:

            async def collect():
                async for e in emitter.async_iter():
                    events.append(e)

            loop.run_until_complete(collect())
        finally:
            loop.close()
        return [json.loads(e.replace("data: ", "").strip()) for e in events]

    def test_emit_trajectory_warning(self):
        emitter = SSEEventEmitter()
        emitter.emit_trajectory_warning(cycle=5, consecutive_non_improving=3)
        events = self._collect_events(emitter)
        assert events[0]["type"] == "trajectory_warning"
        assert events[0]["cycle"] == 5
        assert events[0]["consecutive_non_improving"] == 3

    def test_emit_trajectory_critical(self):
        emitter = SSEEventEmitter()
        emitter.emit_trajectory_critical(cycle=8, consecutive_non_improving=5)
        events = self._collect_events(emitter)
        assert events[0]["type"] == "trajectory_critical"
        assert events[0]["cycle"] == 8
        assert events[0]["consecutive_non_improving"] == 5


class TestReflectNodeCascadeDetection:
    """Verify reflect_node tracks non-improving cycles [BLK-049]."""

    def test_first_cycle_no_previous_gap(self):
        """First cycle has no previous gap_report — counter starts at 0."""
        state = _make_state(prev_gap_report=None)
        result = _run_reflect(state, new_gap_count=5)
        assert result["consecutive_non_improving"] == 0

    def test_gap_count_same_increments_counter(self):
        """Same gap count as previous → counter increments."""
        state = _make_state(prev_gap_count=5, consecutive=2)
        result = _run_reflect(state, new_gap_count=5)
        assert result["consecutive_non_improving"] == 3

    def test_gap_count_decreased_resets_counter(self):
        """Fewer gaps than previous → counter resets to 0."""
        state = _make_state(prev_gap_count=5, consecutive=2)
        result = _run_reflect(state, new_gap_count=3)
        assert result["consecutive_non_improving"] == 0

    def test_gap_count_increased_increments_counter(self):
        """More gaps than previous → counter increments."""
        state = _make_state(prev_gap_count=5, consecutive=1)
        result = _run_reflect(state, new_gap_count=7)
        assert result["consecutive_non_improving"] == 2

    def test_three_non_improving_still_planning(self):
        """3 non-improving cycles → still planning (warning is advisory)."""
        state = _make_state(prev_gap_count=5, consecutive=2)
        result = _run_reflect(state, new_gap_count=5)
        assert result["consecutive_non_improving"] == 3
        assert result["status"] == RunStatus.PLANNING

    def test_five_non_improving_auto_pauses(self):
        """5 non-improving cycles → auto-pause [BLK-049]."""
        state = _make_state(prev_gap_count=5, consecutive=4)
        result = _run_reflect(state, new_gap_count=5)
        assert result["consecutive_non_improving"] == 5
        assert result["status"] == "paused"

    def test_complete_resets_counter(self):
        """When gap_report is complete, counter resets to 0."""
        state = _make_state(prev_gap_count=5, consecutive=4)
        result = _run_reflect(state, new_gap_count=0, is_complete=True)
        assert result["consecutive_non_improving"] == 0
        assert result["status"] == RunStatus.COMPLETE

    def test_six_non_improving_also_pauses(self):
        """6 non-improving cycles → still paused (>= 5)."""
        state = _make_state(prev_gap_count=5, consecutive=5)
        result = _run_reflect(state, new_gap_count=5)
        assert result["consecutive_non_improving"] == 6
        assert result["status"] == "paused"

    def test_counter_in_return_dict(self):
        """reflect_node should return consecutive_non_improving in result."""
        state = _make_state(prev_gap_count=5, consecutive=0)
        result = _run_reflect(state, new_gap_count=5)
        assert "consecutive_non_improving" in result

    def test_improvement_after_warning_resets(self):
        """Gaps improve after a warning → counter resets."""
        state = _make_state(prev_gap_count=5, consecutive=3)
        result = _run_reflect(state, new_gap_count=2)
        assert result["consecutive_non_improving"] == 0
        assert result["status"] == RunStatus.PLANNING


class TestAgentStateHasCounter:
    """Verify AgentState includes consecutive_non_improving."""

    def test_state_accepts_counter(self):
        state: AgentState = {
            "consecutive_non_improving": 3,
        }
        assert state["consecutive_non_improving"] == 3
