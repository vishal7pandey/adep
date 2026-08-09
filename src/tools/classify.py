"""classify_document tool — VLM-based document type classification + auto-routing [BLK-127].

Analyzes document pages using the VLM and returns ranked predictions of document
types with confidence scores. Supports multi-page documents and multi-type detection.

The tool is registered with cacheable=True for future BLK-124 caching support.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.config import settings
from src.definitions.prebuilt import PREBUILT_DEFINITIONS
from src.prompts.classify import (
    CLASSIFY_PROMPT_TEMPLATE,
    MULTI_PAGE_PROMPT_TEMPLATE,
    build_candidate_list,
)
from src.tools.base import ToolResult

logger = logging.getLogger(__name__)

# Default confidence threshold for auto-routing
DEFAULT_AUTO_ROUTE_THRESHOLD: float = 0.75

# Maximum pages to sample for multi-page classification
MAX_SAMPLE_PAGES: int = 5


def _get_candidate_types(candidates: list[str] | None = None) -> list[dict[str, str]]:
    """Build the candidate type list from prebuilt definitions.

    Args:
        candidates: Optional list of definition IDs to restrict the candidate set.
            If None, all registered prebuilt definitions are used.

    Returns:
        List of dicts with "type", "description", and "definition_id" keys.
    """
    result: list[dict[str, str]] = []
    for data in PREBUILT_DEFINITIONS:
        def_id = data["id"]
        if candidates and def_id not in candidates:
            continue
        # Use the skill_id as the type identifier (matches template/task naming)
        doc_type = data.get("skill_id", def_id)
        description = data.get("name", doc_type)
        result.append({
            "type": doc_type,
            "description": description,
            "definition_id": def_id,
        })
    return result


def _parse_vlm_response(text: str) -> list[dict[str, Any]]:
    """Parse the VLM JSON response into a list of predictions.

    Handles cases where the VLM wraps JSON in markdown code blocks.
    """
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse VLM classification response: %s", text[:200])
        return []

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "pages" in data:
        # Multi-page response — flatten to per-page predictions
        return data["pages"]
    if isinstance(data, dict):
        return [data]
    return []


def _parse_multi_page_response(text: str) -> tuple[list[dict[str, Any]], bool]:
    """Parse a multi-page VLM response.

    Returns:
        Tuple of (per_page_predictions, is_multi_type).
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse multi-page VLM response: %s", text[:200])
        return [], False

    if isinstance(data, dict) and "pages" in data:
        pages = data["pages"]
        is_multi = data.get("is_multi_type", False)
        return pages, is_multi
    if isinstance(data, list):
        # Single-page format returned for multi-page — treat as uniform
        return data, False
    return [], False


def _resolve_definition_id(
    doc_type: str,
    candidates: list[dict[str, str]],
) -> str | None:
    """Resolve a document type to its matching definition ID.

    Args:
        doc_type: The classified document type (e.g. "invoice").
        candidates: The candidate list with definition_id mappings.

    Returns:
        The matching definition_id, or None if no match.
    """
    for c in candidates:
        if c["type"] == doc_type:
            return c["definition_id"]
    return None


def _enrich_predictions(
    predictions: list[dict[str, Any]],
    candidates: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Add suggested_definition_id to each prediction."""
    for pred in predictions:
        doc_type = pred.get("document_type", "unknown")
        pred["suggested_definition_id"] = _resolve_definition_id(doc_type, candidates)
    return predictions


def classify_document(
    image_path: str,
    candidates: list[str] | None = None,
    page_paths: list[str] | None = None,
) -> ToolResult:
    """Classify a document into a known type using VLM analysis [BLK-127].

    Args:
        image_path: Path to the first page image (or the only page for single-page docs).
        candidates: Optional list of definition IDs to restrict the candidate set.
            If None, all registered prebuilt definitions are candidates.
        page_paths: Optional list of all page image paths for multi-page documents.
            If provided and contains more than 1 page, multi-page classification is used.

    Returns:
        ToolResult with data containing:
        - "predictions": ranked list of {document_type, confidence, reasoning, suggested_definition_id}
        - "page_count": number of pages analyzed
        - "is_multi_type": whether pages differ in type
    """
    candidate_list = _get_candidate_types(candidates)
    if not candidate_list:
        return ToolResult(
            ok=False,
            error="No candidate document types available for classification.",
            tool="classify_document",
        )

    candidate_str = build_candidate_list(candidate_list)

    # Determine if multi-page classification is needed
    all_pages = page_paths if page_paths and len(page_paths) > 1 else [image_path]
    page_count = len(all_pages)

    # Import VLM provider lazily to avoid import errors when not configured
    try:
        from src.providers.vlm_azure import _call_vlm
    except ImportError:
        return ToolResult(
            ok=False,
            error="VLM provider not available. Configure Azure OpenAI settings.",
            tool="classify_document",
        )

    is_multi_type = False

    if page_count > 1:
        # Multi-page: sample pages and classify each
        sample_pages = all_pages[:MAX_SAMPLE_PAGES]
        prompt = MULTI_PAGE_PROMPT_TEMPLATE.format(
            page_count=len(sample_pages),
            candidate_list=candidate_str,
        )

        # Classify each sampled page and aggregate
        all_predictions: list[dict[str, Any]] = []
        page_types: set[str] = set()

        for i, page_path in enumerate(sample_pages):
            page_prompt = CLASSIFY_PROMPT_TEMPLATE.format(
                candidate_list=candidate_str,
            )
            try:
                raw = _call_vlm(page_path, page_prompt)
                if raw is None:
                    logger.warning("VLM returned None for page %d", i + 1)
                    continue
                preds = _parse_vlm_response(raw)
                for pred in preds:
                    pred["page"] = i + 1
                    page_types.add(pred.get("document_type", "unknown"))
                all_predictions.extend(preds)
            except Exception as e:
                logger.error("VLM classification failed for page %d: %s", i + 1, e)

        is_multi_type = len(page_types) > 1

        # Merge predictions: take the highest-confidence prediction per type
        type_best: dict[str, dict[str, Any]] = {}
        for pred in all_predictions:
            dt = pred.get("document_type", "unknown")
            if dt not in type_best or pred.get("confidence", 0) > type_best[dt].get("confidence", 0):
                type_best[dt] = pred

        predictions = sorted(
            type_best.values(),
            key=lambda p: p.get("confidence", 0),
            reverse=True,
        )
    else:
        # Single-page classification
        prompt = CLASSIFY_PROMPT_TEMPLATE.format(candidate_list=candidate_str)
        try:
            raw = _call_vlm(image_path, prompt)
            if raw is None:
                return ToolResult(
                    ok=False,
                    error="VLM returned no response for classification.",
                    tool="classify_document",
                )
            predictions = _parse_vlm_response(raw)
        except Exception as e:
            logger.error("VLM classification failed: %s", e)
            return ToolResult(
                ok=False,
                error=f"VLM classification failed: {e}",
                tool="classify_document",
            )

    # Enrich with suggested_definition_id
    predictions = _enrich_predictions(predictions, candidate_list)

    # Sort by confidence (highest first)
    predictions.sort(key=lambda p: p.get("confidence", 0), reverse=True)

    return ToolResult(
        ok=True,
        data={
            "predictions": predictions,
            "page_count": page_count,
            "is_multi_type": is_multi_type,
        },
        tool="classify_document",
    )


def auto_route(
    image_path: str,
    page_paths: list[str] | None = None,
    candidates: list[str] | None = None,
    threshold: float | None = None,
) -> dict[str, Any]:
    """Classify a document and auto-select the best agent definition [BLK-127].

    Args:
        image_path: Path to the first page image.
        page_paths: Optional list of all page image paths.
        candidates: Optional list of definition IDs to restrict candidates.
        threshold: Confidence threshold for auto-routing. Defaults to 0.75.

    Returns:
        Dict with:
        - "routed": True if a definition was selected, False if below threshold.
        - "definition_id": The selected definition ID, or None.
        - "predictions": Full ranked prediction list.
        - "page_count": Number of pages analyzed.
        - "is_multi_type": Whether pages differ in type.
        - "reason": Explanation string.

    Raises:
        ValueError: If classification fails or no prediction clears the threshold.
    """
    if threshold is None:
        threshold = settings.auto_route_threshold

    result = classify_document(image_path, candidates=candidates, page_paths=page_paths)
    if not result.ok:
        raise ValueError(result.error)

    predictions = result.data["predictions"]
    if not predictions:
        raise ValueError("Classification returned no predictions.")

    top = predictions[0]
    top_confidence = top.get("confidence", 0)
    top_def_id = top.get("suggested_definition_id")

    if top_confidence >= threshold and top_def_id:
        return {
            "routed": True,
            "definition_id": top_def_id,
            "predictions": predictions,
            "page_count": result.data["page_count"],
            "is_multi_type": result.data["is_multi_type"],
            "reason": f"Auto-routed to {top_def_id} (confidence={top_confidence:.2f})",
        }

    # Below threshold — fail fast with candidate list
    candidate_names = [
        f"{p.get('document_type', 'unknown')} ({p.get('confidence', 0):.2f})"
        for p in predictions[:3]
    ]
    raise ValueError(
        f"No prediction cleared the confidence threshold ({threshold}). "
        f"Top candidates: {', '.join(candidate_names)}"
    )
