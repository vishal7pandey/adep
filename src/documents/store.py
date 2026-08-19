"""Document import & pre-processing pipeline [BLK-059].

Handles multi-format document uploads (PDF, PNG, JPG, TIFF, BMP) and
pre-processes them into standard per-page PNG images at 150 DPI.

Supports:
- PDF rasterization via PyMuPDF (fitz)
- Image format conversion via PIL
- Thumbnail generation (300px wide)
- Metadata extraction (page count, dimensions, DPI)
- Persistence to .adep/documents/{doc_id}/
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB
SUPPORTED_FORMATS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
TARGET_DPI = 150
THUMBNAIL_WIDTH = 300

# BLK-256: Decompression-bomb guard — reject images that expand to more than
# 100 million pixels (~400MB uncompressed RGB). PIL raises DecompressionBombError
# when this limit is exceeded, preventing memory exhaustion from malicious uploads.
_MAX_IMAGE_PIXELS = 100_000_000

_DOC_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


def _atomic_write(path: Path, content: str) -> None:
    """Write content to a file atomically [BLK-155].

    Writes to a temp file in the same directory, then os.replace() into place.
    """
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=path.stem + ".",
        suffix=".tmp",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


@dataclass
class DocumentMeta:
    """Metadata for an imported document [BLK-059].

    Attributes:
        doc_id: Unique document identifier.
        original_filename: Original uploaded filename.
        format: Source format (pdf, png, jpg, tiff, bmp).
        total_pages: Number of pages after rasterization.
        page_dimensions: List of (width, height) tuples per page.
        page_paths: List of paths to page PNG files.
        thumbnail_path: Path to thumbnail JPEG.
        created_at: ISO 8601 timestamp.
    """

    doc_id: str
    original_filename: str
    format: str
    total_pages: int
    page_dimensions: list[tuple[int, int]] = field(default_factory=list)
    page_paths: list[str] = field(default_factory=list)
    thumbnail_path: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence and API responses."""
        return {
            "document_id": self.doc_id,
            "original_filename": self.original_filename,
            "format": self.format,
            "total_pages": self.total_pages,
            "page_dimensions": [
                {"width": w, "height": h} for w, h in self.page_dimensions
            ],
            "page_paths": self.page_paths,
            "thumbnail": self.thumbnail_path,
            "created_at": self.created_at,
        }


class DocumentStore:
    """File-based document store [BLK-059].

    Documents are stored under ``.adep/documents/{doc_id}/`` with:
    - ``page_001.png``, ``page_002.png``, ...
    - ``thumbnail.jpg``
    - ``meta.json``
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path(".adep")
        self.docs_dir = self.base_dir / "documents"
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def get_doc_dir(self, doc_id: str) -> Path:
        """Get the directory for a document.

        Raises:
            ValueError: If doc_id contains path traversal characters.
        """
        if not _DOC_ID_PATTERN.match(doc_id):
            raise ValueError(
                f"Invalid document ID '{doc_id}': must match {_DOC_ID_PATTERN.pattern}"
            )
        return self.docs_dir / doc_id

    def import_document(self, file_path: Path, original_filename: str | None = None) -> DocumentMeta:
        """Import and pre-process a document [BLK-059].

        Args:
            file_path: Path to the uploaded file.
            original_filename: Original filename (defaults to file_path.name).

        Returns:
            DocumentMeta with page info and paths.

        Raises:
            ValueError: If file format is unsupported, file is too large,
                or PDF is password-protected.
        """
        original_filename = original_filename or file_path.name
        ext = file_path.suffix.lower()

        if ext not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format '{ext}'. Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
            )

        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"File size {file_size // 1024 // 1024}MB exceeds 20MB limit"
            )

        doc_id = uuid.uuid4().hex[:12]
        doc_dir = self.get_doc_dir(doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)

        if ext == ".pdf":
            meta = self._process_pdf(file_path, doc_dir, doc_id, original_filename)
        else:
            meta = self._process_image(file_path, doc_dir, doc_id, original_filename, ext)

        # Save metadata
        meta_path = doc_dir / "meta.json"
        _atomic_write(meta_path, json.dumps(meta.to_dict(), indent=2))

        logger.info(
            "Imported document %s: %d pages, format=%s [BLK-059]",
            doc_id, meta.total_pages, meta.format,
        )
        return meta

    def _process_pdf(
        self,
        file_path: Path,
        doc_dir: Path,
        doc_id: str,
        original_filename: str,
    ) -> DocumentMeta:
        """Rasterize PDF pages to PNG at 150 DPI."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise RuntimeError(
                "PyMuPDF (fitz) not installed. Install with: uv add pymupdf"
            )

        doc = fitz.open(str(file_path))

        # Check for password protection
        if doc.needs_pass:
            doc.close()
            raise ValueError("Password-protected PDFs are not supported")

        page_paths: list[str] = []
        page_dimensions: list[tuple[int, int]] = []

        # 150 DPI = 2.0833x default 72 DPI
        zoom = TARGET_DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix)
            page_file = doc_dir / f"page_{i + 1:03d}.png"
            pix.save(str(page_file))
            page_paths.append(str(page_file))
            page_dimensions.append((pix.width, pix.height))

        # Generate thumbnail from first page
        thumbnail_path = ""
        if page_paths:
            thumbnail_path = self._generate_thumbnail(
                Path(page_paths[0]), doc_dir
            )

        doc.close()

        return DocumentMeta(
            doc_id=doc_id,
            original_filename=original_filename,
            format="pdf",
            total_pages=len(page_paths),
            page_dimensions=page_dimensions,
            page_paths=page_paths,
            thumbnail_path=thumbnail_path,
        )

    def _process_image(
        self,
        file_path: Path,
        doc_dir: Path,
        doc_id: str,
        original_filename: str,
        ext: str,
    ) -> DocumentMeta:
        """Convert single image to PNG."""
        from PIL import Image

        # BLK-256: Decompression-bomb guard
        Image.MAX_IMAGE_PIXELS = _MAX_IMAGE_PIXELS

        img = Image.open(file_path)

        # Convert to RGB if necessary (e.g., RGBA, P mode)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Handle multi-page TIFF
        page_paths: list[str] = []
        page_dimensions: list[tuple[int, int]] = []

        if ext in (".tiff", ".tif") and getattr(img, "n_frames", 1) > 1:
            for i in range(img.n_frames):
                img.seek(i)
                page_img = img.copy()
                if page_img.mode not in ("RGB", "L"):
                    page_img = page_img.convert("RGB")
                page_file = doc_dir / f"page_{i + 1:03d}.png"
                page_img.save(str(page_file), "PNG")
                page_paths.append(str(page_file))
                page_dimensions.append((page_img.width, page_img.height))
        else:
            page_file = doc_dir / "page_001.png"
            img.save(str(page_file), "PNG")
            page_paths.append(str(page_file))
            page_dimensions.append((img.width, img.height))

        # Generate thumbnail
        thumbnail_path = self._generate_thumbnail(Path(page_paths[0]), doc_dir)

        format_name = "tiff" if ext in (".tiff", ".tif") else ext.lstrip(".")
        return DocumentMeta(
            doc_id=doc_id,
            original_filename=original_filename,
            format=format_name,
            total_pages=len(page_paths),
            page_dimensions=page_dimensions,
            page_paths=page_paths,
            thumbnail_path=thumbnail_path,
        )

    def _generate_thumbnail(self, source_path: Path, doc_dir: Path) -> str:
        """Generate a 300px-wide thumbnail JPEG."""
        from PIL import Image

        # BLK-256: Decompression-bomb guard
        Image.MAX_IMAGE_PIXELS = _MAX_IMAGE_PIXELS

        img = Image.open(source_path)
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        ratio = THUMBNAIL_WIDTH / img.width
        new_height = int(img.height * ratio)
        thumb = img.resize((THUMBNAIL_WIDTH, new_height), Image.Resampling.LANCZOS)

        thumb_path = doc_dir / "thumbnail.jpg"
        thumb.save(str(thumb_path), "JPEG", quality=85)
        return str(thumb_path)

    def get_document(self, doc_id: str) -> dict[str, Any]:
        """Get document metadata by ID."""
        meta_path = self.get_doc_dir(doc_id) / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Document '{doc_id}' not found")
        return json.loads(meta_path.read_text(encoding="utf-8"))

    def get_page_path(self, doc_id: str, page_number: int) -> Path:
        """Get the path to a specific page image (1-indexed)."""
        doc_dir = self.get_doc_dir(doc_id)
        page_file = doc_dir / f"page_{page_number:03d}.png"
        if not page_file.exists():
            raise FileNotFoundError(
                f"Page {page_number} not found for document '{doc_id}'"
            )
        return page_file

    def get_thumbnail_path(self, doc_id: str) -> Path:
        """Get the path to a document's thumbnail."""
        thumb_path = self.get_doc_dir(doc_id) / "thumbnail.jpg"
        if not thumb_path.exists():
            raise FileNotFoundError(
                f"Thumbnail not found for document '{doc_id}'"
            )
        return thumb_path

    def list_documents(self) -> list[dict[str, Any]]:
        """List all imported documents."""
        docs = []
        if not self.docs_dir.exists():
            return docs
        for doc_dir in sorted(self.docs_dir.iterdir()):
            if doc_dir.is_dir():
                meta_path = doc_dir / "meta.json"
                if meta_path.exists():
                    docs.append(json.loads(meta_path.read_text(encoding="utf-8")))
        return docs


# Singleton
_store: DocumentStore | None = None


def get_document_store() -> DocumentStore:
    """Get the singleton DocumentStore instance."""
    global _store
    if _store is None:
        _store = DocumentStore()
    return _store
