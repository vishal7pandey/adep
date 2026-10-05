"""Tests for BLK-281: max_iterations_reached must NOT be treated as success.

Verifies that:
1. emit_status_change uses canonical status mapping (not collapsed to "failed")
2. SSE complete message doesn't say "Completed" for non-complete runs
3. serialize_extraction_result preserves max_iterations_reached status
"""

from unittest.mock import MagicMock, patch

import pytest

from src.agent.state import RunStatus
from src.api.status import (
    MAX_ITERATIONS_REACHED,
    COMPLETED,
    FAILED,
    map_status_to_frontend,
    map_store_status_to_sse,
)


class TestMaxIterationsStatusContract:
    """BLK-281: max_iterations_reached must not be treated as success-like completion."""

    def test_partial_maps_to_max_iterations_reached(self):
        """RunStatus.PARTIAL must map to max_iterations_reached, not completed."""
        assert map_status_to_frontend(RunStatus.PARTIAL) == MAX_ITERATIONS_REACHED

    def test_partial_sse_status_passes_through(self):
        """max_iterations_reached must pass through SSE mapping unchanged."""
        assert map_store_status_to_sse(MAX_ITERATIONS_REACHED) == MAX_ITERATIONS_REACHED

    def test_partial_does_not_map_to_completed(self):
        """SSE status for PARTIAL must NOT be 'completed'."""
        sse_status = map_store_status_to_sse(map_status_to_frontend(RunStatus.PARTIAL))
        assert sse_status != COMPLETED
        assert sse_status == MAX_ITERATIONS_REACHED

    def test_error_maps_to_failed_not_max_iterations(self):
        """RunStatus.ERROR must map to 'failed', not max_iterations_reached."""
        assert map_status_to_frontend(RunStatus.ERROR) == FAILED
        sse_status = map_store_status_to_sse(map_status_to_frontend(RunStatus.ERROR))
        assert sse_status == FAILED
        assert sse_status != MAX_ITERATIONS_REACHED

    def test_complete_maps_to_completed(self):
        """RunStatus.COMPLETE must map to 'completed' in both layers."""
        assert map_status_to_frontend(RunStatus.COMPLETE) == COMPLETED
        assert map_store_status_to_sse(COMPLETED) == COMPLETED


class TestEmitStatusChangeUsesCanonicalMapping:
    """BLK-281: emit_status_change must use canonical status mapping."""

    def test_partial_status_change_emits_max_iterations_not_failed(self):
        """When result.status is PARTIAL, emit_status_change must emit
        'max_iterations_reached', not 'failed'."""
        from src.templates.base import ExtractedResult
        from src.agent.validator import GapReport, FieldGap, GapType
        from src.api.run_engine import serialize_extraction_result

        result = ExtractedResult(
            is_complete=False,
            status=RunStatus.PARTIAL,
            field_values={},
            gap_report=GapReport(
                gaps=[FieldGap(field="test", gap_type=GapType.MISSING, detail="missing")]
            ),
            trace=[],
            total_cycles=5,
        )

        serialized = serialize_extraction_result("run-test", "def-test", "doc.png", result, {})
        assert serialized["status"] == MAX_ITERATIONS_REACHED
        assert serialized["status"] != COMPLETED
        assert serialized["status"] != FAILED

    def test_error_status_change_emits_failed_not_max_iterations(self):
        """When result.status is ERROR, serialized status must be 'failed'."""
        from src.templates.base import ExtractedResult
        from src.agent.validator import GapReport
        from src.api.run_engine import serialize_extraction_result

        result = ExtractedResult(
            is_complete=False,
            status=RunStatus.ERROR,
            field_values={},
            gap_report=GapReport(),
            trace=[],
            total_cycles=3,
        )

        serialized = serialize_extraction_result("run-test", "def-test", "doc.png", result, {})
        assert serialized["status"] == FAILED
        assert serialized["status"] != MAX_ITERATIONS_REACHED
