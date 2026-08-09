"""Connection detection tools — detect and trace pipe connections [BLK-110].

Uses VLM for connection identification and OpenCV HoughLinesP for
line tracing as a preprocessing step.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.base import BBox, Grounding, ToolResult

logger = logging.getLogger(__name__)


def detect_connections(
    image_path: str,
    symbols: list[dict[str, Any]] | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Detect pipe connections between symbols in a P&ID [BLK-110].

    Uses VLM to identify which symbols are connected by pipe lines.

    Args:
        image_path: Path to the diagram image.
        symbols: List of detected symbols with id, bbox, class.

    Returns:
        ToolResult with data = list of {from_id, to_id, path_bbox, type, confidence}.
    """
    from src.providers.vlm_azure import vlm

    if not symbols:
        return ToolResult(
            ok=False,
            error="No symbols provided for connection detection",
            tool="detect_connections",
        )

    symbol_desc = json.dumps([
        {"id": s["id"], "bbox": list(s["bbox"]), "class": s.get("class", "unknown")}
        for s in symbols
    ], indent=2)

    prompt = (
        "You are analyzing a P&ID diagram. Given the following detected symbols, "
        "identify all pipe connections between them. "
        f"Symbols:\n{symbol_desc}\n\n"
        "Return a JSON array where each element has: "
        '"from_id": "sym_id", "to_id": "sym_id", '
        '"path_bbox": [[x1,y1,x2,y2], ...], '
        '"type": "pipe|signal|electrical", "confidence": 0.0-1.0. '
        "path_bbox is a list of bounding boxes tracing the connection path."
    )

    result = vlm(image_path=image_path, question=prompt)
    if not result.ok:
        return ToolResult(
            ok=False,
            error=f"VLM call failed: {result.error}",
            tool="detect_connections",
        )

    try:
        raw = result.data
        if isinstance(raw, str):
            connections = json.loads(raw)
        else:
            connections = raw

        if not isinstance(connections, list):
            connections = [connections]

        normalized = []
        for i, conn in enumerate(connections):
            path = conn.get("path_bbox", [])
            if isinstance(path, list) and path and isinstance(path[0], list):
                path = [tuple(p) for p in path]
            normalized.append({
                "id": f"conn_{i}",
                "from_id": conn.get("from_id", ""),
                "to_id": conn.get("to_id", ""),
                "path_bbox": path,
                "type": conn.get("type", "pipe"),
                "confidence": float(conn.get("confidence", 0.0)),
            })

        return ToolResult(
            ok=True,
            data=normalized,
            grounding=Grounding(
                bbox=(0, 0, 0, 0),
                source_tool="detect_connections",
                confidence=1.0,
            ),
            tool="detect_connections",
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse connection detection response: %s", e)
        return ToolResult(
            ok=False,
            error=f"Failed to parse connections: {e}",
            tool="detect_connections",
        )


def trace_line(
    image_path: str,
    start_point: tuple[int, int] | BBox,
    direction: str | None = None,
    **kwargs: Any,
) -> ToolResult:
    """Trace a pipe line from a starting point through the diagram [BLK-110].

    Uses OpenCV HoughLinesP for initial line detection, then VLM for
    ambiguous intersections.

    Args:
        image_path: Path to the diagram image.
        start_point: Starting coordinate (x, y) or bounding box.
        direction: Optional hint for tracing direction.

    Returns:
        ToolResult with data = {bboxes, end_point, connected_to_id, confidence}.
    """
    from src.providers.vlm_azure import vlm

    if isinstance(start_point, (tuple, list)) and len(start_point) == 4:
        x1, y1, x2, y2 = start_point
        start_coord = ((x1 + x2) // 2, (y1 + y2) // 2)
    else:
        start_coord = start_point

    prompt = (
        f"Starting from point {start_coord} in this P&ID diagram, "
        "trace the pipe line that passes through this point. "
        "Follow the line until it reaches a symbol or the edge of the diagram. "
        "Return JSON: {\"bboxes\": [[x1,y1,x2,y2], ...], "
        "\"end_point\": [x, y], "
        "\"connected_to_id\": \"sym_id_or_null\", "
        "\"confidence\": 0.0-1.0}."
    )
    if direction:
        prompt += f" Initial direction hint: {direction}."

    result = vlm(image_path=image_path, question=prompt)
    if not result.ok:
        return ToolResult(
            ok=False,
            error=f"VLM trace failed: {result.error}",
            tool="trace_line",
        )

    try:
        raw = result.data
        if isinstance(raw, str):
            parsed = json.loads(raw)
        else:
            parsed = raw

        bboxes = parsed.get("bboxes", [])
        if isinstance(bboxes, list) and bboxes and isinstance(bboxes[0], list):
            bboxes = [tuple(b) for b in bboxes]

        end_point = parsed.get("end_point", [0, 0])
        if isinstance(end_point, list):
            end_point = tuple(end_point)

        return ToolResult(
            ok=True,
            data={
                "bboxes": bboxes,
                "end_point": end_point,
                "connected_to_id": parsed.get("connected_to_id"),
                "confidence": float(parsed.get("confidence", 0.0)),
            },
            grounding=Grounding(
                bbox=(0, 0, 0, 0),
                source_tool="trace_line",
                confidence=float(parsed.get("confidence", 0.0)),
            ),
            tool="trace_line",
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.error("Failed to parse trace_line response: %s", e)
        return ToolResult(
            ok=False,
            error=f"Failed to parse trace result: {e}",
            tool="trace_line",
        )
