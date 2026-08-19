"""REST endpoints for batch processing queue [BLK-118].

Batch upload and processing queue for enterprise users who need to process
hundreds of documents. Each batch creates multiple runs (one per document)
that share a common definition_id (or "auto" for auto-routing).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel

from src.api.run_executor import get_executor
from src.definitions.store import get_store
from src.documents.store import get_document_store, MAX_FILE_SIZE_BYTES, SUPPORTED_FORMATS
from src.documents.validation import validate_magic_bytes, MAGIC_BYTE_READ_SIZE

logger = logging.getLogger(__name__)

router = APIRouter(tags=["batches"])


# ---------------------------------------------------------------------------
# Batch store — file-based persistence in .adep/batches/
# ---------------------------------------------------------------------------

def _batches_dir() -> Path:
    """Return the batches directory, creating it if needed."""
    d = Path.cwd() / ".adep" / "batches"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _batch_path(batch_id: str) -> Path:
    return _batches_dir() / f"{batch_id}.json"


def save_batch(batch_id: str, data: dict[str, Any]) -> None:
    """Persist batch metadata to disk."""
    path = _batch_path(batch_id)
    path.write_text(json.dumps(data, indent=2, default=str))


def load_batch(batch_id: str) -> dict[str, Any]:
    """Load batch metadata from disk."""
    path = _batch_path(batch_id)
    if not path.exists():
        raise FileNotFoundError(f"Batch '{batch_id}' not found")
    return json.loads(path.read_text())


def list_batches() -> list[dict[str, Any]]:
    """List all batches from disk, newest first."""
    d = _batches_dir()
    batches = []
    for f in sorted(d.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            batches.append(json.loads(f.read_text()))
        except Exception:
            logger.warning("Failed to read batch file %s", f)
    return batches


def update_batch(batch_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Update batch metadata on disk."""
    batch = load_batch(batch_id)
    batch.update(updates)
    save_batch(batch_id, batch)
    return batch


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

BatchRunStatus = Literal[
    "queued", "running", "paused", "completed", "failed",
    "cancelled", "max_iterations_reached",
]


class BatchRunItem(BaseModel):
    """A single run within a batch."""
    run_id: str
    document_id: str
    original_filename: str
    status: BatchRunStatus = "queued"
    error: str | None = None


BatchStatus = Literal[
    "queued", "running", "paused", "completed", "cancelled",
    "failed", "max_iterations_reached",
]


class BatchResponse(BaseModel):
    """Response model for batch creation and status."""
    id: str
    name: str
    definition_id: str
    status: BatchStatus = "queued"
    total_runs: int
    completed_runs: int = 0
    failed_runs: int = 0
    running_runs: int = 0
    queued_runs: int = 0
    cancelled_runs: int = 0
    paused_runs: int = 0
    max_iterations_runs: int = 0
    created_at: str
    runs: list[BatchRunItem] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/batches", response_model=BatchResponse, status_code=status.HTTP_201_CREATED)
async def create_batch(
    definition_id: str = Form(..., description="Agent Definition ID or 'auto' for auto-routing"),
    files: list[UploadFile] = File(...),
    name: str | None = Form(None),
) -> dict[str, Any]:
    """Create a batch — upload multiple documents and enqueue runs [BLK-118].

    Accepts multiple files (PDF, PNG, JPG, TIFF, BMP) and a definition_id.
    Each file is uploaded to the document store and a run is enqueued.

    Returns the batch metadata with individual run IDs.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    store = get_store()
    executor = get_executor()
    doc_store = get_document_store()

    # Validate definition exists (unless auto-routing)
    if definition_id != "auto":
        try:
            store.get_definition(definition_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Definition '{definition_id}' not found",
            )

    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    batch_name = name or f"Batch {batch_id[-8:]}"
    created_at = datetime.now(timezone.utc).isoformat()

    run_items: list[dict[str, Any]] = []
    failed_uploads: list[dict[str, str]] = []

    for file in files:
        filename = file.filename or "unknown"
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_FORMATS:
            failed_uploads.append({
                "filename": filename,
                "error": f"Unsupported format '{ext}'",
            })
            continue

        tmp_path: Path | None = None
        try:
            # Stream to temp file with size cap
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                tmp_path = Path(tmp.name)
                total = 0
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_FILE_SIZE_BYTES:
                        tmp.close()
                        tmp_path.unlink(missing_ok=True)
                        tmp_path = None
                        raise ValueError(
                            f"File size exceeds {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB limit"
                        )
                    tmp.write(chunk)

            # Validate magic bytes
            with open(tmp_path, "rb") as f:
                header = f.read(MAGIC_BYTE_READ_SIZE)
            if not validate_magic_bytes(header, ext):
                raise ValueError(
                    f"File content does not match extension '{ext}'. Possible content-type spoofing."
                )

            # Import via document store
            meta = doc_store.import_document(tmp_path, original_filename=filename)
            document_id = meta.doc_id

            # Enqueue run
            ctx = executor.enqueue(
                definition_id=definition_id,
                document_path=document_id,
            )

            run_items.append({
                "run_id": ctx.run_id,
                "document_id": document_id,
                "original_filename": filename,
                "status": ctx.status,
            })
        except Exception as e:
            logger.error("Failed to process file %s in batch: %s", filename, e)
            failed_uploads.append({
                "filename": filename,
                "error": str(e),
            })
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    if not run_items:
        raise HTTPException(
            status_code=400,
            detail=f"No files were successfully processed. Failures: {failed_uploads}",
        )

    batch_data = {
        "id": batch_id,
        "name": batch_name,
        "definition_id": definition_id,
        "status": "queued",
        "total_runs": len(run_items),
        "completed_runs": 0,
        "failed_runs": 0,
        "running_runs": 0,
        "queued_runs": len(run_items),
        "cancelled_runs": 0,
        "paused_runs": 0,
        "max_iterations_runs": 0,
        "created_at": created_at,
        "runs": run_items,
        "failed_uploads": failed_uploads,
    }

    save_batch(batch_id, batch_data)

    logger.info(
        "Batch %s created with %d runs (definition=%s) [BLK-118]",
        batch_id, len(run_items), definition_id,
    )

    return batch_data


@router.get("/batches")
async def list_all_batches() -> list[dict[str, Any]]:
    """List all batches [BLK-118]."""
    batches = list_batches()
    # Refresh status for each batch
    refreshed = []
    for batch in batches:
        refreshed.append(_refresh_batch_status(batch))
    return refreshed


@router.get("/batches/{batch_id}")
async def get_batch(batch_id: str) -> dict[str, Any]:
    """Get batch status — aggregates run statuses [BLK-118]."""
    try:
        batch = load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    return _refresh_batch_status(batch)


@router.post("/batches/{batch_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_batch(batch_id: str) -> dict[str, Any]:
    """Cancel all pending and running runs in a batch [BLK-118]."""
    try:
        batch = load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    executor = get_executor()
    cancelled_count = 0
    for run_item in batch.get("runs", []):
        run_id = run_item["run_id"]
        if executor.cancel_run(run_id):
            cancelled_count += 1
            run_item["status"] = "cancelled"

    batch["status"] = "cancelled"
    save_batch(batch_id, batch)

    logger.info("Batch %s cancelled (%d runs) [BLK-118]", batch_id, cancelled_count)

    return {
        "id": batch_id,
        "cancelled_runs": cancelled_count,
        "message": f"Cancelled {cancelled_count} runs",
    }


@router.delete("/batches/{batch_id}", status_code=status.HTTP_200_OK)
async def delete_batch(batch_id: str) -> dict[str, Any]:
    """Delete a batch and its metadata file [BLK-118].

    Does NOT delete individual runs — those remain in the run store.
    """
    try:
        load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    path = _batch_path(batch_id)
    path.unlink()

    return {"deleted": True, "id": batch_id}


@router.get("/batches/{batch_id}/export/json")
async def export_batch_json(batch_id: str) -> StreamingResponse:
    """Export all completed runs in a batch as a JSON array [BLK-118]."""
    try:
        batch = load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    store = get_store()
    results = []
    for run_item in batch.get("runs", []):
        run_id = run_item["run_id"]
        try:
            run_data = store.get_run(run_id)
            results.append({
                "run_id": run_id,
                "filename": run_item.get("original_filename", ""),
                "status": run_data.get("status", "unknown"),
                "fields": run_data.get("fields", []),
                "total_cost_usd": run_data.get("total_cost_usd", 0),
                "total_tokens": run_data.get("total_tokens", 0),
            })
        except FileNotFoundError:
            results.append({
                "run_id": run_id,
                "filename": run_item.get("original_filename", ""),
                "status": "not_found",
                "fields": [],
            })

    content = json.dumps(results, indent=2, default=str)
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={batch_id}_export.json"},
    )


@router.get("/batches/{batch_id}/export/csv")
async def export_batch_csv(batch_id: str) -> PlainTextResponse:
    """Export all completed runs in a batch as CSV [BLK-118].

    Each row is one field from one run, with columns:
    run_id, filename, field_name, value, confidence, status.
    """
    try:
        batch = load_batch(batch_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    store = get_store()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["run_id", "filename", "field_name", "value", "confidence", "status"])

    for run_item in batch.get("runs", []):
        run_id = run_item["run_id"]
        filename = run_item.get("original_filename", "")
        try:
            run_data = store.get_run(run_id)
            for field in run_data.get("fields", []):
                writer.writerow([
                    run_id,
                    filename,
                    field.get("name", ""),
                    field.get("value", ""),
                    field.get("confidence", 0),
                    field.get("status", ""),
                ])
        except FileNotFoundError:
            writer.writerow([run_id, filename, "", "", "", "not_found"])

    return PlainTextResponse(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={batch_id}_export.csv"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _refresh_batch_status(batch: dict[str, Any]) -> dict[str, Any]:
    """Refresh run statuses in a batch from the executor/store."""
    executor = get_executor()
    store = get_store()

    completed = 0
    failed = 0
    running = 0
    queued = 0
    cancelled = 0
    paused = 0
    max_iter = 0

    for run_item in batch.get("runs", []):
        run_id = run_item["run_id"]
        ctx = executor.get_run(run_id)
        if ctx:
            run_item["status"] = ctx.status
        else:
            # Check store for completed runs
            try:
                run_data = store.get_run(run_id)
                run_item["status"] = run_data.get("status", "completed")
            except FileNotFoundError:
                run_item["status"] = "unknown"

        s = run_item["status"]
        if s == "completed":
            completed += 1
        elif s == "failed":
            failed += 1
        elif s == "running":
            running += 1
        elif s == "paused":
            paused += 1
        elif s == "queued":
            queued += 1
        elif s == "cancelled":
            cancelled += 1
        elif s == "max_iterations_reached":
            max_iter += 1

    batch["completed_runs"] = completed
    batch["failed_runs"] = failed
    batch["running_runs"] = running
    batch["queued_runs"] = queued
    batch["cancelled_runs"] = cancelled
    batch["paused_runs"] = paused
    batch["max_iterations_runs"] = max_iter

    # Determine overall batch status
    total = batch.get("total_runs", len(batch.get("runs", [])))
    terminal = completed + failed + cancelled + max_iter
    if paused > 0 and running == 0:
        batch["status"] = "paused"
    elif cancelled > 0 and terminal >= total:
        batch["status"] = "completed" if completed > 0 else "cancelled"
    elif terminal >= total:
        batch["status"] = "completed"
    elif running > 0:
        batch["status"] = "running"
    else:
        batch["status"] = "queued"

    return batch
