"""Symbol detection tools — detect and classify engineering symbols [BLK-110].

Uses VLM (GPT-5.4 vision) for symbol detection and classification.
Falls back to cropping + retry for low-confidence results.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.base import BBox, Grounding, ToolResult

logger = logging.getLogger(__name__)


def detect_symbols(
    image_path: str,
    symbol_library: str | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Detect engineering symbols in a P&ID or diagram image.

    Uses VLM to identify and locate symbols (valves, pumps, instruments,
    heat exchangers, etc.) with bounding boxes and confidence scores.

    Args:
        image_path: Path to the diagram image.
        symbol_library: Optional symbol library name for few-shot prompting
            (e.g. "ISA-5.1", "DEXPI").

    Returns:
        ToolResult with data = list of {id, bbox, class, confidence}.
    """
    from src.providers.vlm_azure import vlm

    prompt = (
        "You are analyzing a P&ID (Piping and Instrumentation Diagram). "
        "Identify all engineering symbols (valves, pumps, instruments, "
        "heat exchangers, vessels, tanks, etc.). "
        "Return a JSON array where each element has: "
        '"bbox": [x1, y1, x2, y2], "class": "symbol_type", "confidence": 0.0-1.0. '
        "Use pixel coordinates for the bounding box."
    )
    if symbol_library:
        prompt += f" Use the {symbol_library} symbol library for classification."

    result = vlm(image_path=image_path, question=prompt)
    if not result.ok:
        return ToolResult(
            ok=False,
            error=f"VLM call failed: {result.error}",
            tool="detect_symbols",
        )

    try:
        raw = result.data
        if isinstance(raw, str):
            symbols = json.loads(raw)
        else:
            symbols = raw

        if not isinstance(symbols, list):
            symbols = [symbols]

        # Assign IDs and normalize
        normalized = []
        for i, sym in enumerate(symbols):
            bbox = sym.get("bbox", sym.get("bounding_box", [0, 0, 0, 0]))
            if isinstance(bbox, list) and len(bbox) == 4:
                bbox = tuple(bbox)
            normalized.append({
                "id": f"sym_{i}",
                "bbox": bbox,
                "class": sym.get("class", sym.get("type", "unknown")),
                "confidence": float(sym.get("confidence", 0.0)),
            })

        return ToolResult(
            ok=True,
            data=normalized,
            grounding=Grounding(
                bbox=(0, 0, 0, 0),
                source_tool="detect_symbols",
                confidence=1.0,
            ),
            tool="detect_symbols",
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse VLM symbol detection response: %s", e)
        return ToolResult(
            ok=False,
            error=f"Failed to parse symbol detection response: {e}",
            tool="detect_symbols",
        )


def classify_symbol(
    image_path: str,
    bbox: BBox,
    **kwargs: Any,
) -> ToolResult:
    """Classify a single symbol at the given bounding box [BLK-110].

    Crops the region and sends to VLM with a classification prompt.

    Args:
        image_path: Path to the diagram image.
        bbox: Bounding box (x1, y1, x2, y2) of the symbol to classify.

    Returns:
        ToolResult with data = {class, confidence}.
    """
    from src.providers.image_cv import crop
    from src.providers.vlm_azure import vlm

    crop_result = crop(image_path=image_path, bbox=bbox)
    if not crop_result.ok:
        return ToolResult(
            ok=False,
            error=f"Failed to crop symbol region: {crop_result.error}",
            tool="classify_symbol",
        )

    cropped_path = crop_result.data
    prompt = (
        "What type of engineering symbol is shown in this image? "
        "Respond as JSON: {\"class\": \"symbol_type\", \"confidence\": 0.0-1.0}. "
        "Common types: valve, gate_valve, ball_valve, check_valve, "
        "pump, centrifugal_pump, instrument, temperature_sensor, "
        "pressure_sensor, flow_meter, heat_exchanger, vessel, tank, "
        "pipe, reducer, or_unknown."
    )

    result = vlm(image_path=cropped_path, question=prompt)
    if not result.ok:
        return ToolResult(
            ok=False,
            error=f"VLM classification failed: {result.error}",
            tool="classify_symbol",
        )

    try:
        raw = result.data
        if isinstance(raw, str):
            parsed = json.loads(raw)
        else:
            parsed = raw

        return ToolResult(
            ok=True,
            data={
                "class": parsed.get("class", "unknown"),
                "confidence": float(parsed.get("confidence", 0.0)),
            },
            grounding=Grounding(
                bbox=bbox,
                source_tool="classify_symbol",
                confidence=float(parsed.get("confidence", 0.0)),
            ),
            tool="classify_symbol",
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse classification response: %s", e)
        return ToolResult(
            ok=False,
            error=f"Failed to parse classification: {e}",
            tool="classify_symbol",
        )
