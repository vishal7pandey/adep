"""Table detection tool — identify and extract table structures [BLK-125].

Detects tables in document images using a multi-strategy approach:
1. Ruled tables (visible borders) — OpenCV line detection
2. Unruled tables (whitespace-aligned) — projection profiles
3. Complex/merged cells — VLM fallback

Returns cell-level geometry with bboxes in source-image coordinates.
Text is not filled — use `ocr` per cell or `read_table` helper.

Also provides `read_table` composition helper that runs `detect_tables`
then `ocr` per cell and returns header-keyed row dicts.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.base import BBox, ToolResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# detect_tables
# ---------------------------------------------------------------------------


def detect_tables(
    image_path: str,
    region: BBox | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Detect table structures in a document page image.

    Tries ruled-table detection (OpenCV line detection) first, then
    unruled-table detection (projection profiles), then VLM fallback
    for complex/merged cells. The strategy used is recorded in the result.

    Args:
        image_path: Path to the page image.
        region: Optional bounding box to restrict detection to a sub-region.

    Returns:
        ToolResult with data = {"tables": [...], "strategy": str}.
        Each table has: bbox, confidence, n_rows, n_cols, header_row_index,
        cells (list of {row, col, row_span, col_span, bbox, text, confidence}).
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return ToolResult(
            ok=False,
            error="OpenCV (cv2) and numpy are required for detect_tables. Install with: uv add opencv-python numpy",
            tool="detect_tables",
        )

    img = cv2.imread(image_path)
    if img is None:
        return ToolResult(
            ok=False,
            error=f"Could not load image: {image_path}",
            tool="detect_tables",
        )

    if region is not None:
        x1, y1, x2, y2 = region
        img = img[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1
    else:
        offset_x, offset_y = 0, 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Strategy 1: Ruled table detection (visible borders)
    tables, strategy = _detect_ruled_tables(gray, offset_x, offset_y)

    if tables:
        logger.info("detect_tables: ruled-table strategy found %d tables", len(tables))
        return ToolResult(
            ok=True,
            data={"tables": tables, "strategy": strategy},
            tool="detect_tables",
        )

    # Strategy 2: Unruled table detection (projection profiles)
    tables, strategy = _detect_unruled_tables(gray, offset_x, offset_y)

    if tables:
        logger.info("detect_tables: unruled-table strategy found %d tables", len(tables))
        return ToolResult(
            ok=True,
            data={"tables": tables, "strategy": strategy},
            tool="detect_tables",
        )

    # Strategy 3: VLM fallback
    tables, strategy = _detect_tables_vml(image_path, region)

    if tables:
        logger.info("detect_tables: VLM strategy found %d tables", len(tables))
        return ToolResult(
            ok=True,
            data={"tables": tables, "strategy": strategy},
            tool="detect_tables",
        )

    # No tables found
    return ToolResult(
        ok=True,
        data={"tables": [], "strategy": "none"},
        tool="detect_tables",
    )


def _detect_ruled_tables(
    gray: "np.ndarray",
    offset_x: int,
    offset_y: int,
) -> tuple[list[dict[str, Any]], str]:
    """Detect tables with visible border lines using OpenCV.

    Uses morphological operations to isolate horizontal and vertical lines,
    finds intersections, and derives the cell grid.
    """
    import cv2
    import numpy as np

    # Threshold to binary
    try:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    except Exception:
        return [], ""

    # Detect horizontal lines
    h_kernel_size = max(20, int(gray.shape[1] * 0.05))
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_kernel_size, 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

    # Detect vertical lines
    v_kernel_size = max(20, int(gray.shape[0] * 0.05))
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_kernel_size))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

    # Find intersections
    intersections = cv2.bitwise_and(horizontal, vertical)
    if cv2.countNonZero(intersections) < 4:
        return [], ""

    # Find table bounding box from intersection points
    points = cv2.findNonZero(intersections)
    if points is None:
        return [], ""

    x, y, w, h = cv2.boundingRect(points)
    if w < 50 or h < 50:
        return [], ""

    table_bbox = (
        int(x + offset_x),
        int(y + offset_y),
        int(x + w + offset_x),
        int(y + h + offset_y),
    )

    # Find column boundaries from vertical lines within the table
    col_positions = _find_line_positions(vertical, axis=0, min_count=2)
    row_positions = _find_line_positions(horizontal, axis=1, min_count=2)

    if len(col_positions) < 2 or len(row_positions) < 2:
        return [], ""

    # Build cell grid
    cells = []
    for row_idx in range(len(row_positions) - 1):
        for col_idx in range(len(col_positions) - 1):
            cell_bbox = (
                int(col_positions[col_idx] + offset_x),
                int(row_positions[row_idx] + offset_y),
                int(col_positions[col_idx + 1] + offset_x),
                int(row_positions[row_idx + 1] + offset_y),
            )
            cells.append(
                {
                    "row": row_idx,
                    "col": col_idx,
                    "row_span": 1,
                    "col_span": 1,
                    "bbox": cell_bbox,
                    "text": None,
                    "confidence": 0.95,
                }
            )

    # Detect header row (first row with darker background or distinct from data)
    header_row_index = 0 if len(row_positions) > 2 else None

    n_rows = len(row_positions) - 1
    n_cols = len(col_positions) - 1

    tables = [
        {
            "bbox": table_bbox,
            "confidence": 0.92,
            "n_rows": n_rows,
            "n_cols": n_cols,
            "header_row_index": header_row_index,
            "cells": cells,
        }
    ]

    return tables, "ruled"


def _detect_unruled_tables(
    gray: "np.ndarray",
    offset_x: int,
    offset_y: int,
) -> tuple[list[dict[str, Any]], str]:
    """Detect tables without visible borders using projection profiles.

    Uses vertical whitespace projection to find column boundaries and
    horizontal projection to find row boundaries.
    """
    import cv2
    import numpy as np

    # Invert and threshold
    try:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    except Exception:
        return [], ""

    # Horizontal projection (row density profile)
    row_projection = np.sum(binary == 0, axis=1)  # count dark pixels per row

    # Find row gaps (whitespace bands)
    row_gaps = _find_gaps(row_projection, min_gap_height=5)
    if len(row_gaps) < 2:
        return [], ""

    # Derive row boundaries from gaps
    row_boundaries = [0]
    for gap_start, gap_end in row_gaps:
        row_boundaries.append((gap_start + gap_end) // 2)
    row_boundaries.append(len(row_projection) - 1)

    # Vertical projection (column density profile)
    col_projection = np.sum(binary == 0, axis=0)

    # Find column gaps
    col_gaps = _find_gaps(col_projection, min_gap_height=5)
    if len(col_gaps) < 2:
        return [], ""

    col_boundaries = [0]
    for gap_start, gap_end in col_gaps:
        col_boundaries.append((gap_start + gap_end) // 2)
    col_boundaries.append(len(col_projection) - 1)

    # Check that we have a reasonable grid
    n_rows = len(row_boundaries) - 1
    n_cols = len(col_boundaries) - 1

    if n_rows < 2 or n_cols < 2:
        return [], []

    # Build cells
    cells = []
    for row_idx in range(n_rows):
        for col_idx in range(n_cols):
            cell_bbox = (
                int(col_boundaries[col_idx] + offset_x),
                int(row_boundaries[row_idx] + offset_y),
                int(col_boundaries[col_idx + 1] + offset_x),
                int(row_boundaries[row_idx + 1] + offset_y),
            )
            cells.append(
                {
                    "row": row_idx,
                    "col": col_idx,
                    "row_span": 1,
                    "col_span": 1,
                    "bbox": cell_bbox,
                    "text": None,
                    "confidence": 0.75,
                }
            )

    table_bbox = (
        int(col_boundaries[0] + offset_x),
        int(row_boundaries[0] + offset_y),
        int(col_boundaries[-1] + offset_x),
        int(row_boundaries[-1] + offset_y),
    )

    header_row_index = 0 if n_rows > 2 else None

    tables = [
        {
            "bbox": table_bbox,
            "confidence": 0.70,
            "n_rows": n_rows,
            "n_cols": n_cols,
            "header_row_index": header_row_index,
            "cells": cells,
        }
    ]

    return tables, "unruled"


def _detect_tables_vml(
    image_path: str,
    region: BBox | None,
) -> tuple[list[dict[str, Any]], str]:
    """Detect tables using VLM fallback for complex/merged cells."""
    try:
        from src.providers.vlm_azure import vlm
    except ImportError:
        return [], ""

    prompt = (
        "You are analyzing a document page for table structures. "
        "Identify all tables in the image. For each table, return a JSON object with: "
        '"bbox": [x1, y1, x2, y2], "n_rows": int, "n_cols": int, '
        '"header_row_index": int or null, "confidence": 0.0-1.0, '
        '"cells": [{"row": int, "col": int, "row_span": int, "col_span": int, '
        '"bbox": [x1, y1, x2, y2], "confidence": 0.0-1.0}]. '
        "Use pixel coordinates. Return a JSON array of table objects."
    )

    result = vlm(image_path=image_path, question=prompt)
    if not result.ok:
        return [], ""

    try:
        raw = result.data
        if isinstance(raw, str):
            tables = json.loads(raw)
        else:
            tables = raw

        if not isinstance(tables, list):
            tables = [tables]

        # Ensure each table has required fields
        for table in tables:
            if "cells" not in table:
                table["cells"] = []
            for cell in table["cells"]:
                cell.setdefault("text", None)
                cell.setdefault("row_span", 1)
                cell.setdefault("col_span", 1)
                cell.setdefault("confidence", 0.6)
            table.setdefault("confidence", 0.6)
            table.setdefault("header_row_index", None)

        return tables, "vlm"
    except (json.JSONDecodeError, TypeError) as e:
        logger.warning("VLM table detection parse error: %s", e)
        return [], ""


# ---------------------------------------------------------------------------
# read_table composition helper
# ---------------------------------------------------------------------------


def read_table_cells(
    image_path: str,
    table: dict[str, Any] | None = None,
    region: BBox | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Compose detect_tables + ocr per cell to return header-keyed row dicts.

    If a table dict is provided (from a prior detect_tables call), reads
    its cells directly. Otherwise, runs detect_tables first and reads the
    first detected table.

    Args:
        image_path: Path to the page image.
        table: Optional table dict from detect_tables. If None, detect_tables
            is called first.
        region: Optional bounding box for detect_tables if no table provided.

    Returns:
        ToolResult with data = {"rows": [...], "headers": [...], "strategy": str}.
        Each row is a dict keyed by header text (or column index if no header).
    """
    strategy = "provided"

    if table is None:
        detect_result = detect_tables(image_path=image_path, region=region)
        if not detect_result.ok:
            return ToolResult(
                ok=False,
                error=f"detect_tables failed: {detect_result.error}",
                tool="read_table_cells",
            )
        tables = detect_result.data.get("tables", [])
        strategy = detect_result.data.get("strategy", "none")
        if not tables:
            return ToolResult(
                ok=True,
                data={"rows": [], "headers": [], "strategy": strategy},
                tool="read_table_cells",
            )
        table = tables[0]

    # Determine OCR provider
    from src.config import settings

    ocr_func = _get_ocr_func(settings.ocr_provider)
    if ocr_func is None:
        return ToolResult(
            ok=False,
            error=f"OCR provider '{settings.ocr_provider}' not available",
            tool="read_table_cells",
        )

    cells = table.get("cells", [])
    n_rows = table.get("n_rows", 0)
    n_cols = table.get("n_cols", 0)
    header_row_index = table.get("header_row_index")

    # Build a grid of cell texts
    grid: list[list[str | None]] = [[None] * n_cols for _ in range(n_rows)]
    for cell in cells:
        row = cell["row"]
        col = cell["col"]
        if 0 <= row < n_rows and 0 <= col < n_cols:
            if cell.get("text") is not None:
                grid[row][col] = cell["text"]
            else:
                # OCR the cell
                cell_bbox = tuple(cell["bbox"])
                crop_result = _crop_and_ocr(image_path, cell_bbox, ocr_func)
                grid[row][col] = crop_result
                cell["text"] = crop_result

    # Extract headers
    headers: list[str] = []
    if header_row_index is not None and header_row_index < n_rows:
        headers = [str(grid[header_row_index][c] or f"col_{c}") for c in range(n_cols)]
    else:
        headers = [f"col_{c}" for c in range(n_cols)]

    # Build row dicts
    rows: list[dict[str, str | None]] = []
    for row_idx in range(n_rows):
        if header_row_index is not None and row_idx == header_row_index:
            continue
        row_dict = {}
        for col_idx in range(n_cols):
            key = headers[col_idx] if col_idx < len(headers) else f"col_{col_idx}"
            row_dict[key] = grid[row_idx][col_idx]
        rows.append(row_dict)

    return ToolResult(
        ok=True,
        data={"rows": rows, "headers": headers, "strategy": strategy},
        tool="read_table_cells",
    )


# ---------------------------------------------------------------------------
# OpenCV helper functions
# ---------------------------------------------------------------------------


def cv2_threshold_otsu(gray: "np.ndarray") -> "np.ndarray | None":
    """Apply Otsu thresholding and return binary image."""
    import numpy as np

    try:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        return binary
    except Exception:
        return None


def _find_line_positions(
    line_mask: "np.ndarray",
    axis: int,
    min_count: int = 2,
) -> list[int]:
    """Find positions of lines along an axis from a line mask.

    Args:
        line_mask: Binary mask of lines (from morphologyEx).
        axis: 0 for vertical lines (project onto x-axis), 1 for horizontal.
        min_count: Minimum number of distinct line positions required.

    Returns:
        Sorted list of pixel positions.
    """
    import numpy as np

    if axis == 0:
        # Vertical lines: project onto x-axis
        projection = np.sum(line_mask > 0, axis=0)
    else:
        # Horizontal lines: project onto y-axis
        projection = np.sum(line_mask > 0, axis=1)

    # Find peaks (positions where lines exist)
    threshold = max(3, int(np.max(projection) * 0.3)) if np.max(projection) > 0 else 3
    positions = np.where(projection > threshold)[0]

    if len(positions) == 0:
        return []

    # Cluster nearby positions (lines may be a few pixels thick)
    clusters = []
    current_cluster = [positions[0]]
    for pos in positions[1:]:
        if pos - current_cluster[-1] <= 5:
            current_cluster.append(pos)
        else:
            clusters.append(int(np.mean(current_cluster)))
            current_cluster = [pos]
    clusters.append(int(np.mean(current_cluster)))

    if len(clusters) < min_count:
        return []

    return clusters


def _find_gaps(
    projection: "np.ndarray",
    min_gap_height: int = 5,
) -> list[tuple[int, int]]:
    """Find whitespace gaps in a projection profile.

    Args:
        projection: 1D array of pixel counts per row/column.
        min_gap_height: Minimum height of a gap to be considered significant.

    Returns:
        List of (start, end) tuples for each gap.
    """
    import numpy as np

    threshold = max(1, int(np.max(projection) * 0.05)) if np.max(projection) > 0 else 1
    is_gap = projection <= threshold

    gaps = []
    gap_start = None
    for i, g in enumerate(is_gap):
        if g and gap_start is None:
            gap_start = i
        elif not g and gap_start is not None:
            if i - gap_start >= min_gap_height:
                gaps.append((gap_start, i))
            gap_start = None
    if gap_start is not None and len(is_gap) - gap_start >= min_gap_height:
        gaps.append((gap_start, len(is_gap)))

    return gaps


def _get_ocr_func(provider: str):
    """Get the OCR function for the configured provider."""
    try:
        if provider == "tesseract":
            from src.providers.ocr_tesseract import ocr

            return ocr
        elif provider == "paddle":
            from src.providers.ocr_paddle import ocr

            return ocr
    except ImportError:
        return None
    return None


def _crop_and_ocr(
    image_path: str,
    bbox: BBox,
    ocr_func,
) -> str | None:
    """Crop a region from the image and OCR it."""
    try:
        from src.providers.image_cv import crop

        crop_result = crop(image_path=image_path, bbox=bbox)
        if not crop_result.ok:
            return None
        cropped_path = crop_result.data
        ocr_result = ocr_func(image_path=cropped_path)
        if ocr_result.ok:
            text = ocr_result.data
            if isinstance(text, str):
                return text.strip()
            return str(text).strip()
        return None
    except Exception as e:
        logger.warning("Cell OCR failed for bbox %s: %s", bbox, e)
        return None
