"""REST endpoints for document import [BLK-059]."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse

from src.documents.store import get_document_store, MAX_FILE_SIZE_BYTES, SUPPORTED_FORMATS
from src.documents.validation import validate_magic_bytes, MAGIC_BYTE_READ_SIZE

logger = logging.getLogger(__name__)

router = APIRouter(tags=["documents"])


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload and pre-process a document [BLK-059].

    Accepts PDF, PNG, JPG, TIFF, BMP. Rasterizes to 150 DPI PNG per page.
    Generates thumbnails. Max file size: 20MB.

    Returns document metadata including page count and paths.
    """
    # Validate filename extension
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}",
        )

    # BLK-256: Stream to temp file with size cap to prevent disk exhaustion
    # before the file is fully written. Read in chunks and abort early if
    # the streamed size exceeds MAX_FILE_SIZE_BYTES.
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp_path = Path(tmp.name)
            total = 0
            while True:
                chunk = file.file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_SIZE_BYTES:
                    tmp.close()
                    tmp_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File size exceeds {MAX_FILE_SIZE_BYTES // 1024 // 1024}MB limit",
                    )
                tmp.write(chunk)
    except HTTPException:
        raise
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise

    # BLK-256: Validate magic bytes to prevent content-type spoofing
    with open(tmp_path, "rb") as f:
        header = f.read(MAGIC_BYTE_READ_SIZE)
    if not validate_magic_bytes(header, ext):
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=415,
            detail=f"File content does not match extension '{ext}'. Possible content-type spoofing.",
        )

    # Import and pre-process
    try:
        store = get_document_store()
        meta = store.import_document(tmp_path, original_filename=filename)
        return meta.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get("/documents")
async def list_documents() -> list[dict[str, Any]]:
    """List all imported documents [BLK-059]."""
    return get_document_store().list_documents()


@router.get("/documents/{document_id}")
async def get_document(document_id: str) -> dict[str, Any]:
    """Get document metadata by ID [BLK-059]."""
    try:
        return get_document_store().get_document(document_id)
    except (FileNotFoundError, ValueError):
        # ValueError: the document id is not a valid id (never a document).
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")


@router.get("/documents/{document_id}/page/{page_number}")
async def get_page(document_id: str, page_number: int) -> FileResponse:
    """Get a specific page image [BLK-059].

    Args:
        document_id: Document ID.
        page_number: Page number (1-indexed).
    """
    not_found = HTTPException(
        status_code=404,
        detail=f"Page {page_number} not found for document '{document_id}'",
    )
    store = get_document_store()
    try:
        page_path = store.get_page_path(document_id, page_number)
    except (FileNotFoundError, ValueError):
        # ValueError: the document id is not a valid id (never a document).
        raise not_found
    # The path derives from the request: resolve it and require it to stay inside the document
    # store before it is served (CodeQL py/path-injection).
    docs_root = os.path.realpath(store.docs_dir)
    page_file = os.path.realpath(page_path)
    if page_file.startswith(docs_root + os.sep):
        return FileResponse(page_file, media_type="image/png")
    raise not_found


@router.get("/documents/{document_id}/thumbnail")
async def get_thumbnail(document_id: str) -> FileResponse:
    """Get document thumbnail [BLK-059]."""
    not_found = HTTPException(
        status_code=404,
        detail=f"Thumbnail not found for document '{document_id}'",
    )
    store = get_document_store()
    try:
        thumb_path = store.get_thumbnail_path(document_id)
    except (FileNotFoundError, ValueError):
        # ValueError: the document id is not a valid id (never a document).
        raise not_found
    # The path derives from the request: resolve it and serve it only inside the true branch of
    # the containment guard (CodeQL py/path-injection).
    docs_root = os.path.realpath(store.docs_dir)
    thumb_file = os.path.realpath(thumb_path)
    if thumb_file.startswith(docs_root + os.sep):
        return FileResponse(thumb_file, media_type="image/jpeg")
    raise not_found


@router.post("/documents/{document_id}/suggest-agent")
async def suggest_agent(document_id: str) -> dict[str, Any]:
    """Classify a document and suggest the best agent definition [BLK-127].

    Uses VLM analysis to classify the document pages and returns ranked
    predictions with suggested agent definition IDs.

    Returns:
        Dict with predictions, page_count, is_multi_type, and for each
        prediction: document_type, confidence, reasoning, suggested_definition_id.
    """
    store = get_document_store()
    try:
        meta = store.get_document(document_id)
    except (FileNotFoundError, ValueError):
        raise HTTPException(
            status_code=404,
            detail=f"Document '{document_id}' not found",
        )

    page_paths = meta.get("page_paths", [])
    if not page_paths:
        raise HTTPException(
            status_code=400,
            detail=f"Document '{document_id}' has no page images",
        )

    from src.tools.classify import classify_document

    result = classify_document(
        image_path=page_paths[0],
        page_paths=page_paths,
    )

    if not result.ok:
        raise HTTPException(
            status_code=500,
            detail=result.error,
        )

    return result.data
