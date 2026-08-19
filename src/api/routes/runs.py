"""REST endpoints for Runs + SSE streaming [BLK-022, BLK-023]."""

from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel, Field

from src.api.run_engine import execute_run
from src.api.run_executor import get_executor
from src.api.sse import SSEEventEmitter
from src.api.rate_limit import get_limiter
from src.agent.budget import check_pre_run_budget, get_budget_status
from src.config import settings
from src.definitions.store import get_store

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


def _get_run_or_404(run_id: str) -> dict[str, Any]:
    """Fetch a run by ID or raise 404."""
    try:
        return get_store().get_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


class StartRunRequest(BaseModel):
    """Request body for starting a run."""
    definition_id: str = Field(description="Agent definition ID to use")
    document_path: str = Field(description="Path to the document to extract", alias="document_url")

    model_config = {"populate_by_name": True}


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def start_run(req: StartRunRequest, response: Response) -> dict[str, Any]:
    """Start a new extraction run [BLK-129].

    Enqueues the run for background execution and returns 202 immediately
    with the run ID and `queued` status. Stream progress via
    GET /runs/{id}/stream.

    Supports definition_id='auto' for auto-routing: classifies the document
    first and selects the best agent definition above the confidence threshold
    (default 0.75) [BLK-127].

    Returns 429 with Retry-After header when the worker pool is full.
    """
    store = get_store()
    executor = get_executor()

    # Check if worker pool is full [BLK-129, frontend addition]
    if executor.active_count + executor.queue_depth >= executor.max_workers:
        response.headers["Retry-After"] = "5"
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Worker pool full — too many concurrent runs",
                "active_workers": executor.active_count,
                "queue_depth": executor.queue_depth,
                "max_workers": executor.max_workers,
            },
        )

    # Auto-routing: classify document and select definition [BLK-127]
    if req.definition_id == "auto":
        from src.tools.classify import auto_route

        # Get document page paths from the document store
        from src.documents.store import get_document_store
        doc_store = get_document_store()
        # Extract document_id from document_path (may be a path or an ID)
        doc_path = req.document_path
        # Try to find the document by ID first, then by path
        page_paths = None
        try:
            # document_path may be a document_id
            doc_meta = doc_store.get_document(doc_path)
            page_paths = doc_meta.get("page_paths")
            first_page = page_paths[0] if page_paths else doc_path
        except FileNotFoundError:
            # Treat as a file path
            first_page = doc_path

        try:
            route_result = auto_route(
                image_path=first_page,
                page_paths=page_paths,
            )
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=str(e),
            )

        definition_id = route_result["definition_id"]
    else:
        definition_id = req.definition_id

    # Validate definition exists
    try:
        store.get_definition(definition_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Definition '{definition_id}' not found",
        )

    # BLK-241: Validate document_path against allowed document roots
    doc_path_resolved = Path(req.document_path).resolve()
    allowed_roots = [r.resolve() for r in [Path.cwd() / ".adep", Path.cwd() / "sample-data"]]
    if not any(doc_path_resolved.is_relative_to(root) for root in allowed_roots):
        logger.warning("Run creation denied — document_path outside allowed roots: %s", req.document_path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="document_url must point to a file within the document store (.adep/) or sample-data/.",
        )

    # Pre-run budget check [BLK-051]
    def_status, global_status = check_pre_run_budget()
    if def_status.is_exceeded:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Definition daily budget exceeded",
                "level": "definition_daily",
                "consumed_tokens": def_status.consumed_tokens,
                "limit_tokens": def_status.limit_tokens,
                "consumed_cost_usd": def_status.consumed_cost_usd,
                "limit_cost_usd": def_status.limit_cost_usd,
            },
        )
    if global_status.is_exceeded:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Global daily budget exceeded",
                "level": "global_daily",
                "consumed_tokens": global_status.consumed_tokens,
                "limit_tokens": global_status.limit_tokens,
                "consumed_cost_usd": global_status.consumed_cost_usd,
                "limit_cost_usd": global_status.limit_cost_usd,
            },
        )

    # Enqueue for background execution [BLK-129]
    ctx = executor.enqueue(
        definition_id=definition_id,
        document_path=req.document_path,
    )
    return {
        "id": ctx.run_id,
        "status": ctx.status,
        "definition_id": definition_id,
        "document_url": req.document_path,
        "created_at": ctx.created_at,
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict[str, Any]:
    """Get run status and result by ID.

    Returns `extracted_fields_count`, `total_fields`, `status`, and `fields`.
    """
    return _get_run_or_404(run_id)


@router.get("/runs/{run_id}/preview/{page_number}")
async def preview_run_document(run_id: str, page_number: int = 1) -> Response:
    """Render a preview image for the run's source document.

    Supports image paths directly and rasterizes PDFs to PNG on demand.
    This enables UI preview when older run records store filesystem paths.

    BLK-241: Path is confined to allowed document roots (.adep/ and sample-data/)
    to prevent arbitrary file read via attacker-controlled document_url.
    """
    run_data = _get_run_or_404(run_id)
    document_path = run_data.get("document_url") or run_data.get("document_path")
    if not document_path:
        raise HTTPException(status_code=404, detail="Run has no source document path")

    path = Path(document_path).resolve()

    # BLK-241: Confine to allowed document roots only
    allowed_roots = [
        Path.cwd() / ".adep",
        Path.cwd() / "sample-data",
    ]
    allowed_roots = [r.resolve() for r in allowed_roots]
    if not any(path.is_relative_to(root) for root in allowed_roots):
        logger.warning("Preview denied — path outside allowed roots: %s", document_path)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document path is outside the allowed document store.",
        )

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Document not found")

    ext = path.suffix.lower()
    image_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }

    if ext in image_types:
        return FileResponse(str(path), media_type=image_types[ext])

    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF preview unavailable: {exc}")

        with fitz.open(str(path)) as doc:
            if doc.page_count == 0:
                raise HTTPException(status_code=404, detail="PDF has no pages")
            page_index = max(0, min(page_number - 1, doc.page_count - 1))
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            return Response(content=pix.tobytes("png"), media_type="image/png")

    raise HTTPException(status_code=415, detail=f"Unsupported preview format: {ext}")


@router.delete("/runs/{run_id}", status_code=status.HTTP_200_OK)
async def delete_run(run_id: str) -> dict[str, Any]:
    """Delete a run and its associated data [BLK-077]."""
    try:
        get_store().delete_run(run_id)
        return {"deleted": True}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


class PatchRunRequest(BaseModel):
    """Request body for patching a run [BLK-077]."""
    name: str | None = None


@router.post("/runs/{run_id}/verify")
async def verify_run(run_id: str) -> dict[str, Any]:
    """Run surrogate verification against a persisted run.

    This keeps the refine loop inside the HTTP API: callers can execute a run,
    then request a verifier diagnosis without direct access to internal graph
    objects.
    """
    run_data = _get_run_or_404(run_id)
    verifier_payload = run_data.get("verifier_payload")
    if not verifier_payload:
        raise HTTPException(
            status_code=409,
            detail=(
                "Run does not contain verifier payload data. Re-run the document "
                "after upgrading the backend to enable API-based verification."
            ),
        )

    definition_id = run_data.get("definition_id")
    if not definition_id:
        raise HTTPException(status_code=409, detail="Run is missing definition_id")

    try:
        definition = get_store().get_definition(definition_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Definition '{definition_id}' not found")

    skill_id = definition.get("skill_id", definition.get("skill_ref"))
    if not skill_id:
        raise HTTPException(status_code=409, detail="Definition is missing skill_id")

    try:
        skill = get_store().get_skill(skill_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")

    from src.ai.surrogate_verifier import verify_skill as _verify

    result = _verify(
        skill=skill,
        trace=verifier_payload.get("trace", []),
        gap_report=verifier_payload.get("gap_report", {}),
        extraction=verifier_payload.get("extraction", {}),
    )
    if result.get("error"):
        raise HTTPException(status_code=503, detail=result["error"])
    return result


@router.patch("/runs/{run_id}")
async def patch_run(run_id: str, req: PatchRunRequest) -> dict[str, Any]:
    """Update run metadata (e.g. rename) [BLK-077]."""
    run_data = _get_run_or_404(run_id)
    if req.name is not None:
        run_data["name"] = req.name
    get_store().update_run(run_id, run_data)
    return {"id": run_id, "name": run_data.get("name")}


@router.post("/runs/{run_id}/duplicate", status_code=status.HTTP_201_CREATED)
async def duplicate_run(run_id: str) -> dict[str, Any]:
    """Create a new run with the same definition and document [BLK-077].

    The new run starts in `queued` status with no extracted fields.
    """
    source = _get_run_or_404(run_id)

    import uuid as _uuid
    new_id = f"run-{_uuid.uuid4().hex[:8]}"
    new_run = {
        "id": new_id,
        "definition_id": source.get("definition_id"),
        "document_url": source.get("document_url") or source.get("document_path"),
        "status": "queued",
        "current_cycle": 0,
        "total_fields": source.get("total_fields", 0),
        "extracted_fields_count": 0,
        "fields": [],
        "name": f"Copy of {source.get('name', run_id)}",
        "source_run_id": run_id,
    }
    get_store().save_run(new_id, new_run)
    return new_run


@router.get("/runs")
async def list_runs(
    page: int = 1,
    limit: int = 20,
    q: str | None = None,
    status: str | None = None,
    definition_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """List all runs with pagination, search, and filters [BLK-061].

    Args:
        page: Page number (1-indexed).
        limit: Maximum number of items per page.
        q: Search query — case-insensitive substring match on run ID and document name.
        status: Filter by run status (e.g. "completed", "failed", "paused").
        definition_id: Filter by definition ID.
        date_from: Filter runs from this date (ISO format, inclusive).
        date_to: Filter runs up to this date (ISO format, inclusive).
    """
    runs = get_store().list_runs()

    if q:
        q_lower = q.lower()
        runs = [
            r for r in runs
            if q_lower in r.get("id", "").lower()
            or q_lower in (r.get("document_url") or r.get("document_path") or "").lower()
        ]

    if status:
        runs = [r for r in runs if r.get("status") == status]

    if definition_id:
        runs = [r for r in runs if r.get("definition_id") == definition_id]

    if date_from:
        runs = [r for r in runs if r.get("created_at", "") >= date_from]

    if date_to:
        runs = [r for r in runs if r.get("created_at", "") <= date_to]

    start = (page - 1) * limit
    end = start + limit
    return {
        "items": runs[start:end],
        "total": len(runs),
        "page": page,
        "limit": limit,
    }


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str, request: Request) -> StreamingResponse:
    """SSE endpoint — streams run progress events [BLK-129].

    Returns a ``text/event-stream`` response. Events match the frontend's
    ``lib/sse.ts`` types: thought, tool_call, tool_result, progress,
    field_update, complete.

    Live mode: if the run is active (queued/running/paused), subscribes to
    the per-run emitter for live events. Late subscribers receive buffered
    event history, then live events.

    Replay mode: if the run is already completed/failed/cancelled, replays
    stored events from the run data.

    Heartbeat comment every 15 seconds keeps proxies from closing the connection.

    Concurrent SSE cap: max 5 concurrent streams per key/IP [BLK-123].
    """
    # Get the run result
    try:
        run_data = get_store().get_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    # SSE concurrency cap [BLK-123]
    limiter = get_limiter()
    if settings.rate_limit_enabled:
        acquired = await limiter.acquire_sse_slot(request)
        if not acquired:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many concurrent SSE streams",
                    "retry_after": 5,
                },
                headers={"Retry-After": "5"},
            )

    executor = get_executor()
    ctx = executor.get_run(run_id)

    # If run is active, subscribe to live emitter [BLK-129]
    if ctx is not None and ctx.status in ("running", "paused", "queued"):
        async def live_stream():
            """Stream live events from the run's emitter."""
            try:
                # Replay buffered events for late subscribers [BLK-129]
                for event in ctx.event_buffer:
                    yield f"data: {json.dumps(event)}\n\n"

                # Stream live events from the emitter
                async for event in ctx.emitter.async_iter():
                    yield event

                # If emitter is closed but run hasn't finished, emit from stored data
                if ctx.status in ("completed", "failed", "cancelled", "max_iterations_reached"):
                    return
            finally:
                # Release SSE slot on disconnect [BLK-123]
                if settings.rate_limit_enabled:
                    await limiter.release_sse_slot(request)

        return StreamingResponse(
            live_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Replay mode: run is already finished — replay stored events [BLK-129]
    emitter = SSEEventEmitter()

    async def event_stream():
        """Generate SSE events from the stored run."""
        try:
            # Emit field updates
            for field in run_data.get("fields", []):
                emitter.emit_field_update(
                    field_id=field.get("id", field.get("name", "")),
                    name=field.get("name", ""),
                    value=field.get("value"),
                    confidence=field.get("confidence", 0.0),
                    bbox=field.get("bbox"),
                    page=field.get("page", 0),
                    status=field.get("status", "extracted"),
                )

            # Emit progress
            emitter.emit_progress(
                completed_fields=run_data.get("extracted_fields_count", 0),
                total_fields=run_data.get("total_fields", 0),
                failing_fields=run_data.get("total_fields", 0) - run_data.get("extracted_fields_count", 0),
            )

            # Emit compaction event if compaction occurred [§12.4, BLK-039]
            if run_data.get("compaction_summary"):
                emitter.emit_compaction(
                    entries_compacted=run_data.get("entries_compacted", 0),
                    summary_length=len(run_data.get("compaction_summary", "")),
                )

            # Emit complete with run_id [BLK-129]
            # Map persisted store status → SSE complete status [BLK-280]
            from src.api.status import map_store_status_to_sse
            status_str = run_data.get("status", "failed")
            complete_status = map_store_status_to_sse(status_str)
            emitter.emit_complete(complete_status, run_id=run_id)

            # Yield all events
            async for event in emitter.async_iter():
                yield event
        finally:
            # Release SSE slot on disconnect [BLK-123]
            if settings.rate_limit_enabled:
                await limiter.release_sse_slot(request)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/runs/{run_id}/compact")
async def compact_run(run_id: str) -> dict[str, Any]:
    """Trigger manual context compaction for a run [§12.4, BLK-039, BLK-244].

    For running/paused runs, signals the graph via RunControl so the next
    reflect→plan transition routes through the compact node.

    For completed runs, returns a message indicating compaction is only
    meaningful during live execution. Auto-compaction at threshold still
    works during execution.
    """
    try:
        run_data = get_store().get_run(run_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    run_status = run_data.get("status", "unknown")
    if run_status in ("completed", "failed", "max_iterations_reached", "cancelled"):
        return {
            "run_id": run_id,
            "compaction_triggered": False,
            "message": (
                "Run has already completed. Manual compaction is only "
                "meaningful during live execution. Auto-compaction at "
                "threshold runs automatically during the run."
            ),
        }

    # Signal the running graph to compact on next cycle [BLK-244]
    executor = get_executor()
    triggered = executor.compact_run(run_id)

    return {
        "run_id": run_id,
        "compaction_triggered": triggered,
        "message": (
            "Compaction requested — will trigger on next cycle."
            if triggered
            else "Run is not active in the executor — compaction not triggered."
        ),
    }


# ---------------------------------------------------------------------------
# Agent control endpoints [BLK-046]
# ---------------------------------------------------------------------------

class RollbackRequest(BaseModel):
    """Request body for rollback endpoint."""
    to_cycle: int = Field(description="Cycle number to rollback to")


def _update_run_status(run_id: str, new_status: str) -> dict[str, Any]:
    """Update a run's status in the store and return the updated run."""
    run_data = _get_run_or_404(run_id)
    run_data["status"] = new_status
    get_store().update_run(run_id, run_data)
    return run_data


@router.post("/runs/{run_id}/pause")
async def pause_run(run_id: str, response: Response) -> dict[str, Any]:
    """Pause agent execution after the current cycle [BLK-046, BLK-129].

    Graceful halt — the agent finishes the current ReAct cycle, then
    waits for a resume signal. The SSE stream stays open.

    Returns 202 when pause is requested, 200 when no action is taken.
    """
    run_data = _get_run_or_404(run_id)
    current_status = run_data.get("status", "unknown")

    if current_status in ("completed", "failed", "cancelled", "max_iterations_reached"):
        response.status_code = status.HTTP_200_OK
        return {
            "run_id": run_id,
            "paused": False,
            "message": f"Cannot pause — run status is '{current_status}'.",
        }

    if current_status == "paused":
        response.status_code = status.HTTP_200_OK
        return {
            "run_id": run_id,
            "paused": False,
            "message": "Run is already paused.",
        }

    # Request cooperative pause via executor [BLK-129, BLK-270]
    response.status_code = status.HTTP_202_ACCEPTED
    executor = get_executor()
    if not executor.pause_run(run_id):
        # Run not in executor (e.g. sync run) — update store directly [BLK-244]
        _update_run_status(run_id, "paused")
    return {
        "run_id": run_id,
        "paused": True,
        "cycle": run_data.get("current_cycle", 0),
        "message": "Pause requested — agent will halt after current cycle.",
    }


@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: str) -> dict[str, Any]:
    """Resume agent execution from a paused state [BLK-046, BLK-129]."""
    run_data = _get_run_or_404(run_id)
    current_status = run_data.get("status", "unknown")

    if current_status != "paused":
        return {
            "run_id": run_id,
            "resumed": False,
            "message": f"Cannot resume — run status is '{current_status}', not 'paused'.",
        }

    # Signal cooperative resume via executor [BLK-129, BLK-270]
    executor = get_executor()
    if not executor.resume_run(run_id):
        # Run not in executor (e.g. sync run) — update store directly [BLK-244]
        _update_run_status(run_id, "running")
    return {
        "run_id": run_id,
        "resumed": True,
        "cycle": run_data.get("current_cycle", 0),
        "message": "Resumed — agent continuing from paused state.",
    }


@router.post("/runs/{run_id}/stop")
async def stop_run(run_id: str, response: Response) -> dict[str, Any]:
    """Emergency stop — halt immediately, preserve partial results [BLK-046, BLK-129].

    Returns 202 when cancellation is requested, 200 when no action is taken.
    Status becomes 'cancelled'.
    """
    run_data = _get_run_or_404(run_id)
    current_status = run_data.get("status", "unknown")

    if current_status in ("completed", "failed", "cancelled", "max_iterations_reached"):
        response.status_code = status.HTTP_200_OK
        return {
            "run_id": run_id,
            "cancelled": False,
            "message": f"Cannot stop — run already '{current_status}'.",
        }

    # Request cooperative cancellation via executor [BLK-129]
    response.status_code = status.HTTP_202_ACCEPTED
    executor = get_executor()
    executor.cancel_run(run_id)
    _update_run_status(run_id, "cancelled")
    return {
        "run_id": run_id,
        "cancelled": True,
        "cycle": run_data.get("current_cycle", 0),
        "partial_result": run_data.get("fields", []),
        "message": "Cancellation requested — partial results preserved.",
    }


@router.post("/runs/{run_id}/rollback")
async def rollback_run(run_id: str, body: RollbackRequest) -> dict[str, Any]:
    """Rollback run state to a previous cycle [BLK-046, BLK-244].

    For running/paused runs, signals the graph via RunControl to rollback
    at the next cycle boundary. The ``attempted`` set is preserved across
    rollback — retry-loop prevention is non-negotiable [§12.3].

    For completed runs, records the rollback request metadata in the store.
    Full checkpoint restoration requires async runs with checkpointing (v2).
    """
    run_data = _get_run_or_404(run_id)
    current_cycle = run_data.get("current_cycle", 0)
    target_cycle = body.to_cycle

    if target_cycle < 0:
        raise HTTPException(status_code=400, detail="to_cycle must be >= 0")

    if target_cycle >= current_cycle:
        return {
            "run_id": run_id,
            "rolled_back": False,
            "message": f"Cannot rollback to cycle {target_cycle} — current cycle is {current_cycle}.",
        }

    # Try to signal a running graph via the executor [BLK-244]
    executor = get_executor()
    live_rollback = executor.rollback_run(run_id, target_cycle)

    # Record rollback metadata in the store
    run_data["rolled_back_from"] = current_cycle
    run_data["rolled_back_to"] = target_cycle
    run_data["status"] = "paused"
    get_store().update_run(run_id, run_data)

    return {
        "run_id": run_id,
        "rolled_back": True,
        "from_cycle": current_cycle,
        "to_cycle": target_cycle,
        "attempted_preserved": True,
        "live_rollback": live_rollback,
        "message": (
            f"Rolled back from cycle {current_cycle} to {target_cycle}. "
            "attempted set preserved [§12.3]."
            + (" Live graph signaled." if live_rollback else " Run not active in executor — metadata recorded.")
        ),
    }


# ---------------------------------------------------------------------------
# HITL gate approval [BLK-047]
# ---------------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    """Request body for HITL gate approval [BLK-047]."""
    field: str = Field(default="", description="Field path being approved or rejected")
    action: str = Field(default="accept", description="Approval action: 'accept' or 'reject'")


@router.post("/runs/{run_id}/approve")
def approve_field(run_id: str, body: ApprovalRequest | None = None) -> dict[str, Any]:
    """Approve a gated field value [BLK-047].

    Accept: value is locked, agent continues.
    The agent thread, blocked in observe_node on gate_approval_event,
    is unblocked via RunControl.signal_gate_decision.
    """
    field = body.field if body else ""
    run_data = _get_run_or_404(run_id)

    # Record the approval decision
    approvals = run_data.get("gate_approvals", {})
    approvals[field or "_global"] = "accept"
    run_data["gate_approvals"] = approvals

    # Signal the blocked agent thread via RunControl [BLK-047]
    executor = get_executor()
    delivered = executor.signal_gate(run_id, "accept", field)

    # If agent was paused for gate, resume
    if run_data.get("status") == "paused":
        run_data["status"] = "running"

    get_store().update_run(run_id, run_data)

    return {
        "run_id": run_id,
        "field": field,
        "action": "accept",
        "delivered": delivered,
        "message": f"Field '{field or '_global'}' accepted by user [BLK-047].",
    }


@router.post("/runs/{run_id}/reject")
def reject_field(run_id: str, body: ApprovalRequest | None = None) -> dict[str, Any]:
    """Reject a gated field value [BLK-047].

    Reject: agent retries with a different tool/approach.
    The agent thread, blocked in observe_node on gate_approval_event,
    is unblocked via RunControl.signal_gate_decision.
    """
    field = body.field if body else ""
    run_data = _get_run_or_404(run_id)

    # Record the rejection decision
    approvals = run_data.get("gate_approvals", {})
    approvals[field or "_global"] = "reject"
    run_data["gate_approvals"] = approvals

    # Signal the blocked agent thread via RunControl [BLK-047]
    executor = get_executor()
    delivered = executor.signal_gate(run_id, "reject", field)

    # If agent was paused for gate, resume so it can process the rejection
    if run_data.get("status") == "paused":
        run_data["status"] = "running"

    get_store().update_run(run_id, run_data)

    return {
        "run_id": run_id,
        "field": field,
        "action": "reject",
        "delivered": delivered,
        "message": f"Field '{field or '_global'}' rejected by user [BLK-047].",
    }


# ---------------------------------------------------------------------------
# Trace export & audit report [BLK-060]
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/export/json")
async def export_run_json(run_id: str) -> dict[str, Any]:
    """Export full run data as JSON [BLK-060].

    Returns all run metadata, extraction results, trace, token usage,
    and gap report in a single JSON object.
    """
    run_data = _get_run_or_404(run_id)

    export: dict[str, Any] = {
        "run_id": run_id,
        "definition_id": run_data.get("definition_id"),
        "document_url": run_data.get("document_url") or run_data.get("document_path"),
        "status": run_data.get("status"),
        "created_at": run_data.get("created_at"),
        "fields": run_data.get("fields", []),
        "extracted_fields_count": run_data.get("extracted_fields_count", 0),
        "total_fields": run_data.get("total_fields", 0),
        "compaction_summary": run_data.get("compaction_summary"),
        "token_usage": run_data.get("token_usage_summary", {}),
        "gate_approvals": run_data.get("gate_approvals", {}),
    }

    return export


@router.get("/runs/{run_id}/export/csv")
async def export_run_csv(run_id: str) -> PlainTextResponse:
    """Export extracted fields as CSV [BLK-060].

    One row per field with columns:
    field_name, value, confidence, status, page, bbox_x, bbox_y, bbox_w, bbox_h
    """
    run_data = _get_run_or_404(run_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "field_name", "value", "confidence", "status",
        "page", "bbox_x", "bbox_y", "bbox_w", "bbox_h",
    ])

    for field in run_data.get("fields", []):
        bbox = field.get("bbox") or {}
        writer.writerow([
            field.get("name", field.get("id", "")),
            field.get("value", ""),
            field.get("confidence", 0.0),
            field.get("status", ""),
            field.get("page", 0),
            bbox.get("x", ""),
            bbox.get("y", ""),
            bbox.get("width", ""),
            bbox.get("height", ""),
        ])

    return PlainTextResponse(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=run_{run_id}_export.csv",
        },
    )


# ---------------------------------------------------------------------------
# Budget status endpoint [BLK-051]
# ---------------------------------------------------------------------------

@router.get("/budget")
async def get_budget() -> dict[str, Any]:
    """Get current budget consumption at all levels [BLK-051, §15].

    Returns run, definition_daily, and global_daily budget statuses
    with consumed/remaining tokens and cost.
    """
    return get_budget_status()
