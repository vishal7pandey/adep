"""Canonical run-status vocabulary and mapping [BLK-280].

All layers (backend, SSE, persisted store, frontend) must use these
constants and mappings to avoid status-contract drift.

Canonical frontend-facing status values:
  queued                 — run enqueued, not yet started
  running                — active execution (planning/acting/observing/reflecting)
  paused                 — auto-pause or manual pause
  completed              — fully complete, all fields/nodes/edges resolved
  max_iterations_reached — give-up: partial results (budget/cycle cap)
  failed                 — error during execution
  cancelled              — user-requested cancellation
"""

from __future__ import annotations

from src.agent.state import RunStatus

# ---------------------------------------------------------------------------
# Canonical frontend-facing status constants
# ---------------------------------------------------------------------------

QUEUED = "queued"
RUNNING = "running"
PAUSED = "paused"
COMPLETED = "completed"
MAX_ITERATIONS_REACHED = "max_iterations_reached"
FAILED = "failed"
CANCELLED = "cancelled"

ALL_STATUSES = frozenset(
    {
        QUEUED,
        RUNNING,
        PAUSED,
        COMPLETED,
        MAX_ITERATIONS_REACHED,
        FAILED,
        CANCELLED,
    }
)

# ---------------------------------------------------------------------------
# Internal → frontend mapping
# ---------------------------------------------------------------------------

_INTERNAL_TO_FRONTEND: dict[str, str] = {
    RunStatus.PLANNING: RUNNING,
    RunStatus.ACTING: RUNNING,
    RunStatus.OBSERVING: RUNNING,
    RunStatus.REFLECTING: RUNNING,
    RunStatus.COMPLETE: COMPLETED,
    RunStatus.PARTIAL: MAX_ITERATIONS_REACHED,
    RunStatus.PAUSED: PAUSED,
    RunStatus.CANCELLED: CANCELLED,
    RunStatus.ERROR: FAILED,
}


def map_status_to_frontend(status: str) -> str:
    """Map internal RunStatus to canonical frontend status [BLK-280].

    Unknown statuses default to ``failed``.
    """
    return _INTERNAL_TO_FRONTEND.get(status, FAILED)


# ---------------------------------------------------------------------------
# Frontend/store status → SSE complete status
# ---------------------------------------------------------------------------

_STORE_TO_SSE: dict[str, str] = {
    COMPLETED: COMPLETED,
    MAX_ITERATIONS_REACHED: MAX_ITERATIONS_REACHED,
    CANCELLED: CANCELLED,
    PAUSED: PAUSED,
    FAILED: FAILED,
}


def map_store_status_to_sse(status: str) -> str:
    """Map persisted store status to SSE complete event status [BLK-280].

    Unknown statuses default to ``failed``.
    """
    return _STORE_TO_SSE.get(status, FAILED)
