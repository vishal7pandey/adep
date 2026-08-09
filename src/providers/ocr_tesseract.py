"""Tesseract OCR provider — secondary ocr backend [§9, BLK-005].

Fallback/comparison OCR backend. Trivial wrap of pytesseract. Selected
when ADE_OCR_PROVIDER=tesseract. Returns ToolResult with Grounding.
"""

from __future__ import annotations

import logging
from typing import Any

from src.tools.base import Grounding, ToolResult

logger = logging.getLogger(__name__)


def ocr(image_path: str, lang: str = "eng", **kwargs: Any) -> ToolResult:
    """Run Tesseract OCR on an image.

    Args:
        image_path: Path to the image file.
        lang: Tesseract language code (default "eng").

    Returns:
        ToolResult with data=full text string, grounding=approximate bbox.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ToolResult(
            ok=False,
            error="pytesseract or Pillow not installed. Install with: uv add pytesseract Pillow",
            tool="ocr",
        )

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=lang)
        data = pytesseract.image_to_data(img, lang=lang, output_type=pytesseract.Output.DICT)

        # Find first non-empty text box for grounding
        bbox = (0, 0, img.width, img.height)
        confidence = 0.0
        for i, txt in enumerate(data["text"]):
            if txt.strip():
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                bbox = (x, y, x + w, y + h)
                confidence = float(data["conf"][i]) / 100.0 if data["conf"][i] != -1 else 0.5
                break

        grounding = Grounding(bbox=bbox, page=0, source_tool="ocr", confidence=confidence)
        return ToolResult(ok=True, data=text.strip(), grounding=grounding, tool="ocr")
    except Exception as e:
        return ToolResult(ok=False, error=f"Tesseract OCR failed: {e}", tool="ocr")
