"""Perception tools for the new engine (ADE-38).

survey_layout / survey_region are new to ade (VLM-based zone and symbol detection over a
downscaled-then-native-resolution image), ported from ade2's src/ade2/tools.py (read in full as
part of ADE-30). crop_and_read / ocr_page are thin wrappers around ade's existing, already-tested
providers (src/providers/vlm_azure.py, image_cv.py, ocr_tesseract.py) — nothing here reimplements
the Azure or Tesseract calls.

Every tool returns pixel-space bboxes (ade's convention, src/tools/base.py::BBox/Grounding), never
ade2's bare normalized-coordinate dicts: the VLM is asked for normalized coordinates internally
(resolution independence), but values are converted to pixel space against the real page before
they leave this module. A missing document/page (DocumentStore raises FileNotFoundError) or a
malformed VLM response never propagates as an exception — every tool returns a structured
{"error": ...} result instead, the same shape a normal empty result would carry.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any

from PIL import Image

from src.documents.store import get_document_store
from src.providers import image_cv, ocr_tesseract, vlm_azure
from src.tools.base import BBox, Grounding

logger = logging.getLogger(__name__)

_MAX_SURVEY_DIM = 1024

SURVEY_PROMPT = """\
Analyze this document image and identify all major visual zones.

For engineering drawings (P&ID, PFD, isometrics), look for:
- Equipment (vessels, pumps, heat exchangers, columns, compressors)
- Valve clusters (along piping runs between equipment)
- Instrument bubbles (circles with ISA-5.1 tag codes like FT, PI, TIC)
- Piping runs (lines connecting equipment, with line number labels)
- Off-page connectors (arrows or flags at drawing edges)
- Title block / drawing header
- Notes, legends, and design data tables

For general documents, look for: title blocks, tables, schedules, notes, charts, headers, footers.

Return a JSON array of zones. Each zone must have:
- "id": "zone_N" (sequential)
- "type": one of [equipment, valve_cluster, instrument, piping_run, off_page_connector,
  title_block, table, schedule, notes, header, footer, chart, text_block, image]
- "bbox": [ymin, xmin, ymax, xmax] — normalized coordinates (0.0 to 1.0)
- "description": brief description of what's in this zone, including any visible tags or labels

Return ONLY the JSON array. No markdown fences, no commentary.
"""

SURVEY_REGION_PROMPT = """\
This is a zoomed-in sub-region of a larger engineering drawing. Identify all \
symbols and elements visible in this region at high resolution.

Look specifically for:
- Valves (ball, globe, butterfly, check, safety, control, operated)
- Instrument bubbles (circles containing ISA-5.1 function codes like PI, FT, TIC, HS, SV)
- Pipe fittings (flanges, reducers, tees, blinds, orifices)
- Off-page connectors (arrows or flags connecting to other drawings)
- Pipe line number labels
- Equipment nozzles and connections

Return a JSON array of found elements. Each element must have:
- "id": "elem_N" (sequential)
- "type": valve | instrument | fitting | connector | line_label | equipment | piping
- "bbox": [ymin, xmin, ymax, xmax] — normalized coordinates within THIS crop (0.0 to 1.0)
- "tag": the tag or label text visible on the element (empty string if none)
- "description": what the symbol looks like and any surrounding context

Return ONLY the JSON array. No markdown fences, no commentary.
"""

TRANSCRIBE_PROMPT = (
    "Transcribe all visible text in this document verbatim. Return only the text, no commentary."
)


def _get_page_image_path(document_id: str, page_num: int):
    """Resolve a page's image path, or None if the document/page doesn't exist."""
    try:
        return get_document_store().get_page_path(document_id, page_num)
    except (FileNotFoundError, ValueError) as exc:
        logger.debug("Page resolution failed: %s", exc)
        return None


def _parse_json_array(raw: str) -> list[dict]:
    """Parse a JSON array from VLM output, tolerant of markdown fences and a wrapping object."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        for key in ("zones", "elements"):
            if key in parsed:
                return parsed[key]
    return []


def _downscale_for_survey(img: Image.Image) -> Image.Image:
    w, h = img.size
    scale = min(1.0, _MAX_SURVEY_DIM / max(w, h))
    if scale >= 1.0:
        return img
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def _save_temp_png(img: Image.Image, prefix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".png", prefix=f"{prefix}_")
    os.close(fd)
    img.save(path, "PNG")
    return path


def survey_layout(document_id: str, page_num: int = 1) -> dict[str, Any]:
    """Survey a page for semantic zones using the VLM; returns pixel-space bboxes."""
    page_path = _get_page_image_path(document_id, page_num)
    if page_path is None:
        return {"error": f"Page {page_num} not found for document '{document_id}'", "zones": []}

    img = Image.open(page_path)
    w, h = img.size
    survey_img = _downscale_for_survey(img)
    temp_path = _save_temp_png(survey_img, "ade_survey")

    try:
        result = vlm_azure.vlm(temp_path, SURVEY_PROMPT)
    finally:
        os.unlink(temp_path)

    if not result.ok:
        logger.warning("survey_layout: VLM call failed: %s", result.error)
        return {
            "error": result.error or "VLM survey call failed",
            "image_size": [w, h],
            "zones": [],
        }

    raw_zones = _parse_json_array(result.data or "")
    zones: list[dict[str, Any]] = []
    for zone in raw_zones:
        bbox = zone.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        ymin, xmin, ymax, xmax = bbox
        pixel_bbox: BBox = (round(xmin * w), round(ymin * h), round(xmax * w), round(ymax * h))
        zones.append(
            {
                "id": zone.get("id", ""),
                "type": zone.get("type", "unknown"),
                "bbox": pixel_bbox,
                "description": zone.get("description", ""),
            }
        )

    logger.info("survey_layout: doc=%s page=%d -> %d zone(s)", document_id, page_num, len(zones))
    return {"image_size": [w, h], "zone_count": len(zones), "zones": zones, "page": page_num - 1}


def survey_region(document_id: str, bbox_pixel: BBox, page_num: int = 1) -> dict[str, Any]:
    """Re-survey a sub-region at native resolution for dense symbols; returns full-page bboxes."""
    page_path = _get_page_image_path(document_id, page_num)
    if page_path is None:
        return {"error": f"Page {page_num} not found for document '{document_id}'", "elements": []}

    img = Image.open(page_path)
    x1, y1, x2, y2 = bbox_pixel
    if x2 <= x1 or y2 <= y1:
        return {"error": "Invalid bbox produces an empty crop", "elements": []}

    crop_img = img.crop((x1, y1, x2, y2))
    crop_w, crop_h = crop_img.size
    survey_img = _downscale_for_survey(crop_img)
    temp_path = _save_temp_png(survey_img, "ade_survey_region")

    try:
        result = vlm_azure.vlm(temp_path, SURVEY_REGION_PROMPT)
    finally:
        os.unlink(temp_path)

    if not result.ok:
        logger.warning("survey_region: VLM call failed: %s", result.error)
        return {
            "error": result.error or "VLM region survey failed",
            "crop_size": [crop_w, crop_h],
            "elements": [],
        }

    raw_elements = _parse_json_array(result.data or "")
    elements: list[dict[str, Any]] = []
    for elem in raw_elements:
        rel_bbox = elem.get("bbox")
        if not rel_bbox or len(rel_bbox) != 4:
            continue
        rymin, rxmin, rymax, rxmax = rel_bbox
        full_bbox: BBox = (
            round(x1 + rxmin * (x2 - x1)),
            round(y1 + rymin * (y2 - y1)),
            round(x1 + rxmax * (x2 - x1)),
            round(y1 + rymax * (y2 - y1)),
        )
        elements.append(
            {
                "id": elem.get("id", ""),
                "type": elem.get("type", "unknown"),
                "bbox": full_bbox,
                "tag": elem.get("tag", ""),
                "description": elem.get("description", ""),
            }
        )

    logger.info(
        "survey_region: doc=%s bbox=%s -> %d element(s)", document_id, bbox_pixel, len(elements)
    )
    return {
        "crop_size": [crop_w, crop_h],
        "element_count": len(elements),
        "elements": elements,
        "page": page_num - 1,
    }


def crop_and_read(
    document_id: str, bbox_pixel: BBox, question: str, page_num: int = 1
) -> dict[str, Any]:
    """Crop a native-resolution region and ask the VLM about it."""
    page_path = _get_page_image_path(document_id, page_num)
    if page_path is None:
        return {"error": f"Page {page_num} not found for document '{document_id}'"}

    crop_result = image_cv.crop(str(page_path), bbox_pixel)
    if not crop_result.ok:
        logger.warning("crop_and_read: crop failed: %s", crop_result.error)
        return {"error": crop_result.error or "crop failed"}

    vlm_result = vlm_azure.vlm(crop_result.data, question)
    if not vlm_result.ok:
        logger.warning("crop_and_read: VLM call failed: %s", vlm_result.error)
        return {"error": vlm_result.error or "VLM call failed on cropped region"}

    return {
        "answer": vlm_result.data,
        "grounding": Grounding(bbox=bbox_pixel, page=page_num - 1, source_tool="crop_and_read"),
    }


def ocr_page(document_id: str, page_num: int = 1) -> dict[str, Any]:
    """OCR a page; falls back to a VLM transcription if Tesseract is unavailable."""
    page_path = _get_page_image_path(document_id, page_num)
    if page_path is None:
        return {"error": f"Page {page_num} not found for document '{document_id}'"}

    ocr_result = ocr_tesseract.ocr(str(page_path))
    if ocr_result.ok:
        return {"text": ocr_result.data, "engine": "tesseract", "page": page_num - 1}

    logger.warning("ocr_page: Tesseract unavailable (%s) — falling back to VLM", ocr_result.error)
    vlm_result = vlm_azure.vlm(str(page_path), TRANSCRIBE_PROMPT)
    if not vlm_result.ok:
        logger.error("ocr_page: no OCR engine available for doc=%s page=%d", document_id, page_num)
        return {"text": "", "engine": "none", "error": "No OCR engine available"}

    return {
        "text": vlm_result.data,
        "engine": "vlm_fallback",
        "page": page_num - 1,
        "warning": (
            f"Tesseract unavailable ({ocr_result.error}). This text came from a downsampled "
            "full-page VLM read and may omit small or dense text. For fine detail, use "
            "crop_and_read on a specific region instead."
        ),
    }
