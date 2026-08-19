"""Tests for canonical run-status contract [BLK-280].

Verifies that all layers (backend RunStatus, SSE, persisted store, frontend)
use a single aligned status vocabulary with no drift.
"""

from __future__ import annotations

from src.agent.state import RunStatus
from src.api.status import (
    ALL_STATUSES,
    CANCELLED,
    COMPLETED,
    FAILED,
    MAX_ITERATIONS_REACHED,
    PAUSED,
    QUEUED,
    RUNNING,
    map_status_to_frontend,
    map_store_status_to_sse,
)


class TestStatusVocabulary:
    """Verify the canonical status vocabulary is complete and consistent [BLK-280]."""

    def test_all_statuses_defined(self):
        """All 7 canonical statuses must be present."""
        assert ALL_STATUSES == frozenset({
            QUEUED, RUNNING, PAUSED, COMPLETED,
            MAX_ITERATIONS_REACHED, FAILED, CANCELLED,
        })

    def test_no_extra_internal_statuses(self):
        """Every RunStatus constant must have a mapping."""
        internal_statuses = [
            RunStatus.PLANNING, RunStatus.ACTING, RunStatus.OBSERVING,
            RunStatus.REFLECTING, RunStatus.COMPLETE, RunStatus.PARTIAL,
            RunStatus.PAUSED, RunStatus.ERROR, RunStatus.CANCELLED,
        ]
        for s in internal_statuses:
            mapped = map_status_to_frontend(s)
            assert mapped in ALL_STATUSES, (
                f"RunStatus.{s} maps to '{mapped}' which is not in canonical vocabulary [BLK-280]"
            )


class TestMapStatusToFrontend:
    """Verify internal → frontend status mapping [BLK-280]."""

    def test_planning_maps_to_running(self):
        assert map_status_to_frontend(RunStatus.PLANNING) == RUNNING

    def test_acting_maps_to_running(self):
        assert map_status_to_frontend(RunStatus.ACTING) == RUNNING

    def test_observing_maps_to_running(self):
        assert map_status_to_frontend(RunStatus.OBSERVING) == RUNNING

    def test_reflecting_maps_to_running(self):
        assert map_status_to_frontend(RunStatus.REFLECTING) == RUNNING

    def test_complete_maps_to_completed(self):
        assert map_status_to_frontend(RunStatus.COMPLETE) == COMPLETED

    def test_partial_maps_to_max_iterations_reached(self):
        """PARTIAL must NOT map to 'completed' — it means give-up [BLK-280]."""
        assert map_status_to_frontend(RunStatus.PARTIAL) == MAX_ITERATIONS_REACHED

    def test_paused_maps_to_paused(self):
        assert map_status_to_frontend(RunStatus.PAUSED) == PAUSED

    def test_cancelled_maps_to_cancelled(self):
        """CANCELLED must NOT fall through to 'failed' [BLK-280]."""
        assert map_status_to_frontend(RunStatus.CANCELLED) == CANCELLED

    def test_error_maps_to_failed(self):
        assert map_status_to_frontend(RunStatus.ERROR) == FAILED

    def test_unknown_maps_to_failed(self):
        assert map_status_to_frontend("unknown_status") == FAILED


class TestMapStoreStatusToSSE:
    """Verify persisted store → SSE complete status mapping [BLK-280]."""

    def test_completed_maps_to_completed(self):
        assert map_store_status_to_sse(COMPLETED) == COMPLETED

    def test_max_iterations_reached_passes_through(self):
        assert map_store_status_to_sse(MAX_ITERATIONS_REACHED) == MAX_ITERATIONS_REACHED

    def test_cancelled_passes_through(self):
        assert map_store_status_to_sse(CANCELLED) == CANCELLED

    def test_paused_passes_through(self):
        assert map_store_status_to_sse(PAUSED) == PAUSED

    def test_failed_passes_through(self):
        assert map_store_status_to_sse(FAILED) == FAILED

    def test_queued_maps_to_failed(self):
        """Queued runs should never reach SSE complete — default to failed."""
        assert map_store_status_to_sse(QUEUED) == FAILED

    def test_running_maps_to_failed(self):
        """Running runs should never reach SSE complete — default to failed."""
        assert map_store_status_to_sse(RUNNING) == FAILED

    def test_unknown_maps_to_failed(self):
        assert map_store_status_to_sse("unknown") == FAILED


class TestRunEngineDelegatesToCanonical:
    """Verify run_engine.map_status_to_frontend delegates to canonical module [BLK-280]."""

    def test_run_engine_mapping_matches_canonical(self):
        from src.api.run_engine import map_status_to_frontend as engine_map
        for status in [
            RunStatus.PLANNING, RunStatus.ACTING, RunStatus.OBSERVING,
            RunStatus.REFLECTING, RunStatus.COMPLETE, RunStatus.PARTIAL,
            RunStatus.PAUSED, RunStatus.ERROR, RunStatus.CANCELLED,
        ]:
            assert engine_map(status) == map_status_to_frontend(status), (
                f"run_engine mapping diverges from canonical for {status} [BLK-280]"
            )


class TestComposedPipelineDoesNotCollapseFailures:
    """Verify the full internal -> frontend -> SSE pipeline never miscategorizes
    error/partial outcomes into success-like states [BLK-221, SCRUM-36].

    Regression: run_engine.py used to compute SSE ``complete_status`` via an
    ad-hoc ternary (``"success" if result.is_complete else
    "max_iterations_reached"``) that never checked for RunStatus.ERROR,
    silently collapsing failed runs into "max_iterations_reached" over SSE
    while the persisted store correctly recorded "failed" — a status-contract
    drift between SSE and the store.
    """

    def _composed(self, internal_status: str) -> str:
        return map_store_status_to_sse(map_status_to_frontend(internal_status))

    def test_error_surfaces_as_failed_not_max_iterations(self):
        assert self._composed(RunStatus.ERROR) == FAILED

    def test_partial_surfaces_as_max_iterations_reached(self):
        assert self._composed(RunStatus.PARTIAL) == MAX_ITERATIONS_REACHED

    def test_complete_surfaces_as_completed(self):
        assert self._composed(RunStatus.COMPLETE) == COMPLETED

    def test_cancelled_surfaces_as_cancelled(self):
        assert self._composed(RunStatus.CANCELLED) == CANCELLED

    def test_paused_surfaces_as_paused(self):
        assert self._composed(RunStatus.PAUSED) == PAUSED

    def test_no_internal_status_collapses_to_completed_except_complete(self):
        """Only RunStatus.COMPLETE may ever surface as the SSE 'completed' status."""
        non_complete_statuses = [
            RunStatus.PLANNING, RunStatus.ACTING, RunStatus.OBSERVING,
            RunStatus.REFLECTING, RunStatus.PARTIAL, RunStatus.PAUSED,
            RunStatus.ERROR, RunStatus.CANCELLED,
        ]
        for s in non_complete_statuses:
            assert self._composed(s) != COMPLETED, (
                f"RunStatus.{s} must not surface as SSE '{COMPLETED}' [BLK-221]"
            )
