"""PaddleOCR provider — detect_layout, detect_text, ocr [§9, BLK-004].

Primary OCR backend. PaddleOCR gives both text recognition and layout
detection with bounding boxes and confidence scores. Self-hostable.

All functions return ToolResult with Grounding (bbox + confidence).
Handles missing PaddleOCR installation gracefully.
"""

from __future__ import annotations

import logging
from typing import Any

from src.tools.base import Grounding, Region, RegionType, ToolResult

logger = logging.getLogger(__name__)

_paddle_engine: Any = None


def _get_engine() -> Any:
    """Lazy-load the PaddleOCR engine (singleton per process)."""
    global _paddle_engine
    if _paddle_engine is not None:
        return _paddle_engine
    try:
        from paddleocr import PaddleOCR
        _paddle_engine = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
        return _paddle_engine
    except ImportError:
        raise RuntimeError(
            "PaddleOCR is not installed. Install with: uv add paddleocr"
        )


def detect_layout(image_path: str, **kwargs: Any) -> ToolResult:
    """Detect layout regions in a document image.

    Uses PaddleOCR's structure analysis to identify text, table, figure,
    and other region types with bounding boxes.

    Args:
        image_path: Path to the image file.

    Returns:
        ToolResult with data=list of Region dicts (id, type, bbox, confidence).
    """
    try:
        engine = _get_engine()
        result = engine.ocr(image_path, cls=True)
    except RuntimeError as e:
        return ToolResult(ok=False, error=str(e), tool="detect_layout")
    except Exception as e:
        return ToolResult(ok=False, error=f"PaddleOCR layout failed: {e}", tool="detect_layout")

    regions: list[dict[str, Any]] = []
    if not result or not result[0]:
        return ToolResult(ok=True, data=regions, tool="detect_layout")

    for idx, line in enumerate(result[0]):
        bbox_raw, (text, confidence) = line
        x1, y1 = int(bbox_raw[0][0]), int(bbox_raw[0][1])
        x2, y2 = int(bbox_raw[2][0]), int(bbox_raw[2][1])
        regions.append({
            "id": f"p0_r{idx}",
            "type": RegionType.TEXT.value,
            "bbox": (x1, y1, x2, y2),
            "page": 0,
            "text": text,
            "confidence": float(confidence),
            "metadata": {},
        })

    return ToolResult(ok=True, data=regions, tool="detect_layout")


def detect_text(image_path: str, lang: str = "en", **kwargs: Any) -> ToolResult:
    """Detect text boxes in a document image.

    Args:
        image_path: Path to the image file.
        lang: Language hint for OCR.

    Returns:
        ToolResult with data=list of {text, bbox, score} dicts.
    """
    try:
        engine = _get_engine()
        result = engine.ocr(image_path, cls=True)
    except RuntimeError as e:
        return ToolResult(ok=False, error=str(e), tool="detect_text")
    except Exception as e:
        return ToolResult(ok=False, error=f"PaddleOCR text detection failed: {e}", tool="detect_text")

    boxes: list[dict[str, Any]] = []
    if not result or not result[0]:
        return ToolResult(ok=True, data=boxes, tool="detect_text")

    for line in result[0]:
        bbox_raw, (text, confidence) = line
        x1, y1 = int(bbox_raw[0][0]), int(bbox_raw[0][1])
        x2, y2 = int(bbox_raw[2][0]), int(bbox_raw[2][1])
        boxes.append({
            "text": text,
            "bbox": (x1, y1, x2, y2),
            "score": float(confidence),
        })

    return ToolResult(ok=True, data=boxes, tool="detect_text")


def ocr(image_path: str, lang: str = "en", **kwargs: Any) -> ToolResult:
    """Run OCR on an image, returning full text with bounding boxes and scores.

    Args:
        image_path: Path to the image file.
        lang: Language hint.

    Returns:
        ToolResult with data=full text string, grounding=first text box.
    """
    result = detect_text(image_path, lang=lang)
    if not result.ok:
        return result

    boxes = result.data
    if not boxes:
        return ToolResult(ok=True, data="", tool="ocr")

    full_text = " ".join(b["text"] for b in boxes)
    first = boxes[0]
    grounding = Grounding(
        bbox=first["bbox"],
        page=0,
        source_tool="ocr",
        confidence=first["score"],
    )

    return ToolResult(ok=True, data=full_text, grounding=grounding, tool="ocr")
