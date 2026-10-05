"""Signature, stamp, and seal detection tool [BLK-126].

Detects signature regions in document images using:
1. Connected-component analysis for dense non-text ink clusters
2. Hough detection for circular/rectangular stamps and seals
3. VLM classification to assign kind and is_handwritten

IMPORTANT: This tool answers "is there a signature here?" — NOT
"is this signature authentic?" or "whose signature is this?".
Signature verification (identity matching, forgery detection) is
explicitly out of scope and requires separate legal review.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.base import BBox, ToolResult

logger = logging.getLogger(__name__)


# Signature mark kinds
MARK_KINDS = {"signature", "stamp", "seal", "initials", "checkmark"}


def detect_signatures(
    image_path: str,
    region: BBox | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Detect signature, stamp, and seal regions in a document page.

    Uses connected-component analysis and Hough detection for candidate
    regions, then VLM classification to assign kind and is_handwritten.

    Args:
        image_path: Path to the page image.
        region: Optional bounding box to restrict detection to a sub-region.

    Returns:
        ToolResult with data = {"marks": [...]}.
        Each mark has: bbox, kind, confidence, is_handwritten, nearby_label,
        ink_coverage.

    Note:
        This tool detects the *presence* of marks — it does NOT verify
        authenticity, identity, or detect forgery. Do not use this output
        to make legal or financial decisions about document validity.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return ToolResult(
            ok=False,
            error="OpenCV (cv2) and numpy are required for detect_signatures. Install with: uv add opencv-python numpy",
            tool="detect_signatures",
        )

    img = cv2.imread(image_path)
    if img is None:
        return ToolResult(
            ok=False,
            error=f"Could not load image: {image_path}",
            tool="detect_signatures",
        )

    if region is not None:
        x1, y1, x2, y2 = region
        img = img[y1:y2, x1:x2]
        offset_x, offset_y = x1, y1
    else:
        offset_x, offset_y = 0, 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Strategy 1: Connected-component analysis for ink clusters
    candidates = _find_ink_clusters(gray, offset_x, offset_y)

    # Strategy 2: Hough detection for circular stamps/seals
    hough_candidates = _find_circular_marks(gray, offset_x, offset_y)
    candidates.extend(hough_candidates)

    # Deduplicate overlapping candidates
    candidates = _deduplicate_candidates(candidates)

    if not candidates:
        return ToolResult(
            ok=True,
            data={"marks": []},
            tool="detect_signatures",
        )

    # Strategy 3: VLM classification
    marks = _classify_marks_vlm(image_path, candidates, offset_x, offset_y)

    # Compute ink_coverage for each mark
    for mark in marks:
        mark["ink_coverage"] = _compute_ink_coverage(gray, mark["bbox"], offset_x, offset_y)

    # Find nearby labels
    marks = _associate_labels(image_path, marks, gray, offset_x, offset_y)

    return ToolResult(
        ok=True,
        data={"marks": marks},
        tool="detect_signatures",
    )


def _find_ink_clusters(
    gray: "np.ndarray",
    offset_x: int,
    offset_y: int,
) -> list[dict[str, Any]]:
    """Find dense non-text ink clusters via connected-component analysis."""
    import cv2
    import numpy as np

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Morphological operations to connect nearby ink
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 5))
    dilated = cv2.dilate(binary, kernel, iterations=2)

    # Find connected components
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(dilated)

    candidates = []
    img_h, img_w = gray.shape

    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]

        # Filter by size — signatures are typically 50-300px wide
        if w < 30 or h < 15:
            continue
        if w > img_w * 0.8 or h > img_h * 0.5:
            continue

        # Filter by aspect ratio — signatures are wider than tall
        aspect = w / h if h > 0 else 0
        if aspect < 0.5 or aspect > 15:
            continue

        # Check ink density within the region
        roi = binary[y : y + h, x : x + w]
        density = float(np.count_nonzero(roi)) / (w * h) if w * h > 0 else 0

        # Signatures have moderate ink density (not solid, not empty)
        if density < 0.05 or density > 0.85:
            continue

        candidates.append(
            {
                "bbox": (
                    int(x + offset_x),
                    int(y + offset_y),
                    int(x + w + offset_x),
                    int(y + h + offset_y),
                ),
                "density": density,
                "area": int(area),
            }
        )

    return candidates


def _find_circular_marks(
    gray: "np.ndarray",
    offset_x: int,
    offset_y: int,
) -> list[dict[str, Any]]:
    """Find circular stamps and seals using Hough circle detection."""
    import cv2
    import numpy as np

    img_h, img_w = gray.shape

    # Blur for smoother detection
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Hough circle detection
    min_radius = max(20, int(min(img_w, img_h) * 0.03))
    max_radius = int(min(img_w, img_h) * 0.25)

    try:
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1.5,
            minDist=50,
            param1=50,
            param2=30,
            minRadius=min_radius,
            maxRadius=max_radius,
        )
    except Exception:
        return []

    candidates = []
    if circles is not None:
        for circle in circles[0]:
            cx, cy, r = circle
            x1 = int(cx - r + offset_x)
            y1 = int(cy - r + offset_y)
            x2 = int(cx + r + offset_x)
            y2 = int(cy + r + offset_y)
            candidates.append(
                {
                    "bbox": (x1, y1, x2, y2),
                    "density": 0.3,
                    "area": int(3.14159 * r * r),
                    "circular": True,
                }
            )

    return candidates


def _deduplicate_candidates(
    candidates: list[dict[str, Any]],
    iou_threshold: float = 0.5,
) -> list[dict[str, Any]]:
    """Remove overlapping candidate regions using IoU."""
    if len(candidates) <= 1:
        return candidates

    filtered = []
    for cand in candidates:
        is_dup = False
        for kept in filtered:
            iou = _compute_iou(cand["bbox"], kept["bbox"])
            if iou > iou_threshold:
                is_dup = True
                break
        if not is_dup:
            filtered.append(cand)

    return filtered


def _compute_iou(bbox1: BBox, bbox2: BBox) -> float:
    """Compute Intersection over Union of two bounding boxes."""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def _classify_marks_vlm(
    image_path: str,
    candidates: list[dict[str, Any]],
    offset_x: int,
    offset_y: int,
) -> list[dict[str, Any]]:
    """Classify candidate regions using VLM."""
    try:
        from src.providers.vlm_azure import vlm
    except ImportError:
        # No VLM available — return candidates with default classification
        return [
            {
                "bbox": c["bbox"],
                "kind": "signature",
                "confidence": 0.5,
                "is_handwritten": True,
                "nearby_label": None,
            }
            for c in candidates
        ]

    prompt = (
        "You are analyzing a document for signatures, stamps, and seals. "
        "I have detected candidate regions. For each region, classify it as one of: "
        '"signature", "stamp", "seal", "initials", "checkmark". '
        "Also determine if it appears to be handwritten. "
        "Return a JSON array where each element has: "
        '"bbox": [x1, y1, x2, y2], "kind": str, "confidence": 0.0-1.0, '
        '"is_handwritten": bool. '
        "Only include regions that are actually signatures, stamps, seals, initials, or checkmarks."
    )

    try:
        result = vlm(image_path=image_path, question=prompt)
        if not result.ok:
            # Fallback to default classification
            return [
                {
                    "bbox": c["bbox"],
                    "kind": "signature",
                    "confidence": 0.5,
                    "is_handwritten": True,
                    "nearby_label": None,
                }
                for c in candidates
            ]

        raw = result.data
        if isinstance(raw, str):
            marks = json.loads(raw)
        else:
            marks = raw

        if not isinstance(marks, list):
            marks = [marks]

        # Validate and normalize
        valid_marks = []
        for mark in marks:
            kind = mark.get("kind", "signature")
            if kind not in MARK_KINDS:
                kind = "signature"
            valid_marks.append(
                {
                    "bbox": tuple(mark.get("bbox", c["bbox"])) if "bbox" in mark else c["bbox"],
                    "kind": kind,
                    "confidence": float(mark.get("confidence", 0.6)),
                    "is_handwritten": bool(mark.get("is_handwritten", True)),
                    "nearby_label": None,
                }
            )

        return valid_marks

    except (json.JSONDecodeError, TypeError, ImportError) as e:
        logger.warning("VLM signature classification failed: %s", e)
        return [
            {
                "bbox": c["bbox"],
                "kind": "signature",
                "confidence": 0.5,
                "is_handwritten": True,
                "nearby_label": None,
            }
            for c in candidates
        ]


def _compute_ink_coverage(
    gray: "np.ndarray",
    bbox: BBox,
    offset_x: int,
    offset_y: int,
) -> float:
    """Compute the fraction of a bbox region that contains ink."""
    import cv2
    import numpy as np

    x1, y1, x2, y2 = bbox
    # Convert to local coordinates
    lx1 = max(0, x1 - offset_x)
    ly1 = max(0, y1 - offset_y)
    lx2 = min(gray.shape[1], x2 - offset_x)
    ly2 = min(gray.shape[0], y2 - offset_y)

    if lx2 <= lx1 or ly2 <= ly1:
        return 0.0

    roi = gray[ly1:ly2, lx1:lx2]
    _, binary = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    total_pixels = (lx2 - lx1) * (ly2 - ly1)
    if total_pixels == 0:
        return 0.0

    ink_pixels = int(np.count_nonzero(binary))
    return round(ink_pixels / total_pixels, 4)


def _associate_labels(
    image_path: str,
    marks: list[dict[str, Any]],
    gray: "np.ndarray",
    offset_x: int,
    offset_y: int,
) -> list[dict[str, Any]]:
    """Find nearby text labels for each mark using OCR.

    Looks for text lines below or to the left of each mark, which is
    the typical signature-block layout.
    """
    try:
        from src.config import settings

        ocr_func = _get_ocr_func(settings.ocr_provider)
    except ImportError:
        ocr_func = None

    if ocr_func is None:
        return marks

    for mark in marks:
        bbox = mark["bbox"]
        # Search region: 50px below the mark, same width
        search_bbox = (
            max(0, bbox[0] - 20),
            bbox[3],
            bbox[2] + 20,
            min(gray.shape[0] + offset_y, bbox[3] + 60),
        )

        try:
            from src.providers.image_cv import crop

            crop_result = crop(image_path=image_path, bbox=search_bbox)
            if crop_result.ok:
                ocr_result = ocr_func(image_path=crop_result.data)
                if ocr_result.ok and ocr_result.data:
                    text = str(ocr_result.data).strip()
                    # Take the first short line as the label
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    if lines:
                        label = lines[0][:80]  # Cap at 80 chars
                        mark["nearby_label"] = label
        except Exception as e:
            logger.debug("Label association failed for mark %s: %s", bbox, e)

    return marks


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
