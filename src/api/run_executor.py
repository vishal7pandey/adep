"""Async run executor — bounded worker pool, live SSE, cooperative control [BLK-129].

Replaces synchronous run execution with an async task pool. Runs execute
in background asyncio tasks, emit live SSE events, and support cooperative
pause/resume/cancel at ReAct cycle boundaries.

v1: in-process asyncio only. No Celery/Redis. Multi-process scaling is
a documented follow-up.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from src.api.sse import SSEEventEmitter
from src.config import settings
from src.definitions.store import get_store

logger = logging.getLogger(__name__)


class RunControl:
    """Cooperative control flags for a running agent [BLK-129].

    Checked at ReAct cycle boundaries (should_continue / should_act).
    Cancellation is cooperative — never a hard task kill.

    Attributes:
        cancel_requested: If True, agent terminates at next cycle boundary.
        pause_requested: If True, agent pauses at next cycle boundary.
        resume_event: Thread-safe event — set when resume is called; the agent
            blocks on this when paused [BLK-270].
        gate_approval_event: Thread-safe event set by /approve or /reject to
            unblock a HITL gate in observe_node [BLK-047].
        gate_decision: The user's gate decision ("accept" or "reject") [BLK-047].
        gate_field: The field name currently awaiting gate approval [BLK-047].
    """

    def __init__(self) -> None:
        self.cancel_requested: bool = False
        self.pause_requested: bool = False
        self.resume_event: threading.Event = threading.Event()
        self.gate_approval_event: threading.Event = threading.Event()
        self.gate_decision: str = ""
        self.gate_field: str = ""
        self.compact_requested: bool = False
        self.rollback_requested: bool = False
        self.rollback_to_cycle: int = -1

    def request_pause(self) -> None:
        """Request the agent to pause at the next cycle boundary [BLK-270].

        Clears the resume_event so the graph will block when it reaches
        the next cycle boundary.
        """
        self.pause_requested = True
        self.resume_event.clear()

    def request_resume(self) -> None:
        """Clear pause and signal the agent to continue [BLK-270]."""
        self.pause_requested = False
        self.resume_event.set()

    def wait_for_resume(self, timeout: float | None = None) -> bool:
        """Block until resume is signaled or timeout expires [BLK-270].

        Called from the graph thread (runs via asyncio.to_thread).
        Returns True if the event was set, False on timeout.
        """
        return self.resume_event.wait(timeout)

    def reset_gate(self) -> None:
        """Reset gate state for the next HITL gate [BLK-047]."""
        self.gate_approval_event.clear()
        self.gate_decision = ""
        self.gate_field = ""

    def signal_gate_decision(self, decision: str, field: str = "") -> None:
        """Signal a HITL gate decision from the API layer [BLK-047].

        Args:
            decision: "accept" or "reject".
            field: The field name being approved/rejected.
        """
        self.gate_decision = decision
        self.gate_field = field
        self.gate_approval_event.set()

    def request_cancel(self) -> None:
        """Request the agent to cancel at the next cycle boundary.

        Also unblocks any thread waiting in a HITL gate or pause so the
        worker doesn't leak forever [SCRUM-483].
        """
        self.cancel_requested = True
        self.gate_approval_event.set()
        self.resume_event.set()

    def request_compact(self) -> None:
        """Request manual trace compaction at the next cycle boundary [BLK-244].

        Sets ``compact_requested`` so ``should_continue`` routes through
        the compact node on the next reflect→plan transition.
        """
        self.compact_requested = True

    def request_rollback(self, to_cycle: int) -> None:
        """Request a rollback to a previous cycle [BLK-244].

        Args:
            to_cycle: The cycle number to rollback to.
        """
        self.rollback_requested = True
        self.rollback_to_cycle = to_cycle

    def check_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self.cancel_requested


class RunContext:
    """Per-run context holding state, SSE emitter, and control flags [BLK-129].

    Attributes:
        run_id: Unique run identifier.
        definition_id: Agent definition ID.
        document_path: Path to the document.
        status: Current run status (queued, running, paused, completed, max_iterations_reached, failed, cancelled).
        emitter: SSE event emitter for this run.
        control: Cooperative control flags.
        event_buffer: Buffered events for late SSE subscribers.
        result: Final serialized result (None until run completes).
        created_at: ISO timestamp when the run was enqueued.
        started_at: ISO timestamp when the worker picked up the run.
        completed_at: ISO timestamp when the run finished.
        error: Error message if the run failed.
    """

    def __init__(
        self,
        run_id: str,
        definition_id: str,
        document_path: str,
    ) -> None:
        self.run_id = run_id
        self.definition_id = definition_id
        self.document_path = document_path
        self.status: str = "queued"
        self.emitter: SSEEventEmitter = SSEEventEmitter()
        self.control: RunControl = RunControl()
        self.event_buffer: list[dict[str, Any]] = []
        self.result: dict[str, Any] | None = None
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.started_at: str | None = None
        self.completed_at: str | None = None
        self.error: str | None = None

    def buffer_event(self, event: dict[str, Any]) -> None:
        """Buffer an SSE event for late subscribers."""
        self.event_buffer.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Serialize run context for API responses."""
        return {
            "id": self.run_id,
            "definition_id": self.definition_id,
            "document_url": self.document_path,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


class RunExecutor:
    """Bounded async worker pool for run execution [BLK-129].

    Manages a queue of pending runs and a pool of worker tasks. Each worker
    pulls a run from the queue and executes it in a background thread (the
    LangGraph invoke is synchronous). SSE events are emitted live via the
    per-run emitter.

    Attributes:
        _max_workers: Maximum concurrent runs (default 3).
        _queue: Pending run requests.
        _runs: Active and recently completed run contexts.
        _workers: Set of active worker asyncio tasks.
        _shutdown: Whether graceful shutdown has been initiated.
    """

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers: int = max_workers or 3
        self._queue: asyncio.Queue[RunContext] = asyncio.Queue()
        self._runs: dict[str, RunContext] = {}
        self._workers: set[asyncio.Task] = set()
        self._shutdown: bool = False
        self._started: bool = False

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def active_count(self) -> int:
        """Number of currently running workers."""
        return sum(
            1 for ctx in self._runs.values()
            if ctx.status in ("running", "paused")
        )

    @property
    def queue_depth(self) -> int:
        """Number of pending runs in the queue."""
        return self._queue.qsize()

    def start(self) -> None:
        """Start the worker pool. Called on app startup."""
        if self._started:
            return
        self._started = True
        self._shutdown = False
        for _ in range(self._max_workers):
            task = asyncio.create_task(self._worker_loop())
            self._workers.add(task)
        logger.info(
            "RunExecutor started with %d workers [BLK-129]",
            self._max_workers,
        )

    async def stop(self) -> None:
        """Graceful shutdown — stop accepting new runs, drain in-flight [BLK-129].

        Lets in-flight runs finish or checkpoint, then exits.
        """
        self._shutdown = True

        # Signal queue-empty by putting None sentinels
        for _ in self._workers:
            await self._queue.put(None)  # type: ignore[arg-type]

        # Wait for workers to finish
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._started = False
        logger.info("RunExecutor stopped — all workers drained [BLK-129]")

    def enqueue(
        self,
        definition_id: str,
        document_path: str,
        run_id: str | None = None,
    ) -> RunContext:
        """Enqueue a new run for background execution [BLK-129].

        Args:
            definition_id: Agent definition ID to use.
            document_path: Path to the document.
            run_id: Optional run ID (auto-generated if not provided).

        Returns:
            RunContext for the queued run.

        Raises:
            RuntimeError: If executor is shutting down.
        """
        if self._shutdown:
            raise RuntimeError("RunExecutor is shutting down — not accepting new runs")

        if run_id is None:
            run_id = f"run-{uuid.uuid4().hex[:8]}"

        ctx = RunContext(run_id, definition_id, document_path)
        self._runs[run_id] = ctx
        self._queue.put_nowait(ctx)

        # Persist initial state
        store = get_store()
        store.save_run(run_id, {
            "id": run_id,
            "definition_id": definition_id,
            "document_url": document_path,
            "status": "queued",
            "current_cycle": 0,
            "total_fields": 0,
            "extracted_fields_count": 0,
            "fields": [],
            "created_at": ctx.created_at,
        })

        logger.info("Run %s enqueued (definition=%s) [BLK-129]", run_id, definition_id)
        return ctx

    def get_run(self, run_id: str) -> RunContext | None:
        """Get a run context by ID."""
        return self._runs.get(run_id)

    def pause_run(self, run_id: str) -> bool:
        """Request a running run to pause at the next cycle boundary [BLK-129, BLK-270].

        Updates ctx.status to "paused" and persists to store so the API
        layer doesn't need to update the store separately.

        Returns:
            True if pause was requested, False if run not found or not running.
        """
        ctx = self._runs.get(run_id)
        if ctx is None or ctx.status not in ("running",):
            return False
        ctx.control.request_pause()
        ctx.status = "paused"
        self._persist_run(ctx)
        return True

    def resume_run(self, run_id: str) -> bool:
        """Resume a paused run [BLK-129, BLK-270].

        Signals the graph thread to unblock via resume_event and updates
        ctx.status back to "running". Persists to store.

        Returns:
            True if resume was signaled, False if run not found or not paused.
        """
        ctx = self._runs.get(run_id)
        if ctx is None or ctx.status != "paused":
            return False
        ctx.control.request_resume()
        ctx.status = "running"
        self._persist_run(ctx)
        return True

    def cancel_run(self, run_id: str) -> bool:
        """Request a running run to cancel at the next cycle boundary [BLK-129].

        Returns:
            True if cancel was requested, False if run not found or not active.
        """
        ctx = self._runs.get(run_id)
        if ctx is None or ctx.status not in ("running", "paused", "queued"):
            return False
        ctx.control.request_cancel()
        # If paused, also resume so the worker can see the cancel flag
        if ctx.status == "paused":
            ctx.control.request_resume()
        return True

    def signal_gate(self, run_id: str, decision: str, field: str = "") -> bool:
        """Signal a HITL gate decision to a blocked agent [BLK-047].

        Args:
            run_id: The run ID.
            decision: "accept" or "reject".
            field: The field name being approved/rejected.

        Returns:
            True if the signal was delivered, False if run not found.
        """
        ctx = self._runs.get(run_id)
        if ctx is None:
            return False
        ctx.control.signal_gate_decision(decision, field)
        return True

    def compact_run(self, run_id: str) -> bool:
        """Request manual compaction for a running run [BLK-244].

        Args:
            run_id: The run ID.

        Returns:
            True if compaction was requested, False if run not found or not running.
        """
        ctx = self._runs.get(run_id)
        if ctx is None or ctx.status not in ("running", "paused"):
            return False
        ctx.control.request_compact()
        return True

    def rollback_run(self, run_id: str, to_cycle: int) -> bool:
        """Request rollback for a running run [BLK-244].

        Args:
            run_id: The run ID.
            to_cycle: The cycle to rollback to.

        Returns:
            True if rollback was requested, False if run not found or not running.
        """
        ctx = self._runs.get(run_id)
        if ctx is None or ctx.status not in ("running", "paused"):
            return False
        ctx.control.request_rollback(to_cycle)
        return True

    def get_queue_status(self) -> dict[str, Any]:
        """Get queue depth and worker utilisation for admin endpoint [BLK-129]."""
        active_runs = [
            ctx.to_dict()
            for ctx in self._runs.values()
            if ctx.status in ("running", "paused")
        ]
        queued_runs = [
            ctx.to_dict()
            for ctx in self._runs.values()
            if ctx.status == "queued"
        ]
        return {
            "queue_depth": self.queue_depth,
            "active_workers": self.active_count,
            "max_workers": self._max_workers,
            "runs": active_runs + queued_runs,
        }

    def recover_orphans(self) -> int:
        """Mark interrupted runs as failed on boot [BLK-129].

        Runs left in 'running' or 'paused' state from a previous process
        are marked 'failed' with a clear reason.

        Returns:
            Number of orphaned runs recovered.
        """
        store = get_store()
        runs = store.list_runs()
        count = 0
        for run in runs:
            status = run.get("status", "")
            if status in ("running", "paused", "queued"):
                run["status"] = "failed"
                run["error"] = "Worker process restarted — run was interrupted"
                store.update_run(run["id"], run)
                count += 1
                logger.warning(
                    "Orphaned run %s marked failed (was %s) [BLK-129]",
                    run["id"], status,
                )
        if count:
            logger.info("Recovered %d orphaned runs [BLK-129]", count)
        return count

    async def _worker_loop(self) -> None:
        """Worker loop — pulls runs from queue and executes them."""
        while True:
            ctx = await self._queue.get()
            if ctx is None:
                # Shutdown sentinel
                break
            try:
                await self._execute_run(ctx)
            except Exception as e:
                logger.error(
                    "Run %s failed in worker: %s [BLK-129]",
                    ctx.run_id, e,
                )
                ctx.status = "failed"
                ctx.error = str(e)
                ctx.completed_at = datetime.now(timezone.utc).isoformat()
                self._persist_run(ctx)
        logger.debug("Worker loop exiting [BLK-129]")

    async def _execute_run(self, ctx: RunContext) -> None:
        """Execute a single run [BLK-129].

        Delegates to execute_run_async which runs the synchronous LangGraph
        invoke in a thread via asyncio.to_thread() [BLK-240]. SSE events
        are emitted live via the emitter wired into the graph nodes.
        """
        ctx.status = "running"
        ctx.started_at = datetime.now(timezone.utc).isoformat()
        self._persist_run(ctx)

        # Import here to avoid circular imports
        from src.api.run_engine import execute_run_async

        try:
            result = await execute_run_async(
                run_id=ctx.run_id,
                definition_id=ctx.definition_id,
                document_path=ctx.document_path,
                emitter=ctx.emitter,
                control=ctx.control,
                event_buffer=ctx.event_buffer,
            )
            ctx.result = result
            ctx.status = result.get("status", "completed")
            ctx.completed_at = datetime.now(timezone.utc).isoformat()
            self._persist_run(ctx)

        except asyncio.CancelledError:
            ctx.status = "cancelled"
            ctx.completed_at = datetime.now(timezone.utc).isoformat()
            ctx.error = "Task was cancelled"
            self._persist_run(ctx)
            raise

        except Exception as e:
            ctx.status = "failed"
            ctx.error = str(e)
            ctx.completed_at = datetime.now(timezone.utc).isoformat()
            self._persist_run(ctx)
            logger.error("Run %s failed: %s [BLK-129]", ctx.run_id, e)

    def _persist_run(self, ctx: RunContext) -> None:
        """Persist run state to the store on every transition [BLK-129]."""
        store = get_store()
        try:
            existing = store.get_run(ctx.run_id)
        except FileNotFoundError:
            existing = {
                "id": ctx.run_id,
                "definition_id": ctx.definition_id,
                "document_url": ctx.document_path,
                "fields": [],
            }
        existing["status"] = ctx.status
        existing["started_at"] = ctx.started_at
        existing["completed_at"] = ctx.completed_at
        if ctx.error:
            existing["error"] = ctx.error
        if ctx.result:
            existing.update(ctx.result)
        store.update_run(ctx.run_id, existing)


# Singleton executor instance
_executor: RunExecutor | None = None


def get_executor() -> RunExecutor:
    """Get the singleton RunExecutor instance [BLK-129]."""
    global _executor
    if _executor is None:
        _executor = RunExecutor(
            max_workers=getattr(settings, "max_concurrent_runs", 3),
        )
    return _executor


def reset_executor() -> None:
    """Reset the singleton executor (for testing)."""
    global _executor
    _executor = None
