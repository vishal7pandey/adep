"""Tag reading tool — OCR + ISA-5.1 tag parsing [BLK-110].

The ISA-5.1 parser is deterministic code, not LLM.
Tag format: [function_letter(s)]-[number] e.g. "FT-101", "PIC-202".
"""

from __future__ import annotations

import logging
import re
from typing import Any

from src.tools.base import BBox, Grounding, ToolResult

logger = logging.getLogger(__name__)

# ISA-5.1 function letters (common subset)
ISA_FUNCTION_LETTERS = {
    "T": "Temperature",
    "P": "Pressure",
    "F": "Flow",
    "L": "Level",
    "A": "Analyzer",
    "S": "Speed",
    "V": "Vibration",
    "W": "Weight",
    "D": "Density",
    "H": "Hand",
    "I": "Current",
    "Q": "Quantity",
}

ISA_MODIFIERS = {
    "T": "Transmitter",
    "I": "Indicator",
    "C": "Controller",
    "R": "Recorder",
    "S": "Switch",
    "V": "Valve",
    "G": "Gauge",
    "E": "Element",
    "Y": "Relay/Compute",
    "Z": "Final Element",
}

# ISA-5.1 tag pattern: function letters, optional modifier, dash, number
_TAG_PATTERN = re.compile(r"^([A-Z]{1,4})-?(\d+)$")


def parse_isa_tag(tag: str) -> dict[str, Any]:
    """Parse an ISA-5.1 instrument tag string [BLK-110].

    Examples:
        "FT-101" → {function: "F", modifier: "T", number: "101",
                     function_meaning: "Flow", modifier_meaning: "Transmitter"}
        "PIC-202" → {function: "P", modifier: "IC", number: "202",
                      function_meaning: "Pressure", modifier_meaning: "Indicator+Controller"}
        "LV-303" → {function: "L", modifier: "V", number: "303",
                     function_meaning: "Level", modifier_meaning: "Valve"}

    Args:
        tag: Raw tag string (e.g. "FT-101").

    Returns:
        Parsed components dict. If parsing fails, returns raw tag with
        parse_error flag.
    """
    tag = tag.strip().upper()
    match = _TAG_PATTERN.match(tag)
    if not match:
        return {
            "tag": tag,
            "parse_error": True,
            "function": None,
            "modifier": None,
            "number": None,
        }

    letters = match.group(1)
    number = match.group(2)

    # First letter is the function, rest is modifier
    function = letters[0]
    modifier = letters[1:] if len(letters) > 1 else None

    function_meaning = ISA_FUNCTION_LETTERS.get(function, "Unknown")
    modifier_meaning = None
    if modifier:
        if len(modifier) == 1:
            modifier_meaning = ISA_MODIFIERS.get(modifier, "Unknown")
        else:
            modifier_meaning = "+".join(ISA_MODIFIERS.get(m, "Unknown") for m in modifier)

    return {
        "tag": tag,
        "function": function,
        "modifier": modifier,
        "number": number,
        "function_meaning": function_meaning,
        "modifier_meaning": modifier_meaning,
        "parse_error": False,
    }


def read_tag(
    image_path: str,
    bbox: BBox,
    **kwargs: Any,
) -> ToolResult:
    """Read and parse an instrument tag from a P&ID diagram [BLK-110].

    Crops the tag area, runs OCR, then parses the ISA-5.1 tag format.

    Args:
        image_path: Path to the diagram image.
        bbox: Bounding box of the tag area.

    Returns:
        ToolResult with data = {tag, parsed_components, confidence}.
    """
    from src.providers.image_cv import crop
    from src.config import settings

    if settings.ocr_provider == "paddle":
        from src.providers.ocr_paddle import ocr as _ocr_impl
    elif settings.ocr_provider == "tesseract":
        from src.providers.ocr_tesseract import ocr as _ocr_impl
    else:
        from src.providers.ocr_tesseract import ocr as _ocr_impl

    crop_result = crop(image_path=image_path, bbox=bbox)
    if not crop_result.ok:
        return ToolResult(
            ok=False,
            error=f"Failed to crop tag region: {crop_result.error}",
            tool="read_tag",
        )

    cropped_path = crop_result.data
    ocr_result = _ocr_impl(image_path=cropped_path, lang="eng")
    if not ocr_result.ok:
        return ToolResult(
            ok=False,
            error=f"OCR failed on tag region: {ocr_result.error}",
            tool="read_tag",
        )

    raw_text = ocr_result.data
    if isinstance(raw_text, str):
        tag_text = raw_text.strip()
    elif isinstance(raw_text, dict):
        tag_text = raw_text.get("text", "").strip()
    else:
        tag_text = str(raw_text).strip()

    if not tag_text:
        return ToolResult(
            ok=False,
            error="No text found in tag region",
            tool="read_tag",
        )

    parsed = parse_isa_tag(tag_text)
    confidence = ocr_result.grounding.confidence if ocr_result.grounding else 0.5

    return ToolResult(
        ok=True,
        data={
            "tag": parsed["tag"],
            "parsed_components": parsed,
            "confidence": confidence,
        },
        grounding=Grounding(
            bbox=bbox,
            source_tool="read_tag",
            confidence=confidence,
        ),
        tool="read_tag",
    )
