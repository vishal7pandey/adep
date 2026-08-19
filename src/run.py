"""Run entry point: compose Template + Skill + Document into an extraction run [§3.3].

    run(template, skill, document) -> ExtractedResult

A run instantiates the ReAct agent (LangGraph) with the skill's prompt and
tool set, hands it the document and the template, and lets it loop to
completion. The output is the filled schema plus grounding, confidence, and
a full trace of tool calls for debugging and evaluation.

This module wires the pieces together. The actual LangGraph graph nodes are
in agent/graph.py (to be implemented next). For now, this provides the
public API and the initial State construction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.agent.state import AgentState, DocumentHandle, DocumentState, RunStatus
from src.agent.validator import (
    Invariant,
    ValidatorConfig,
    validate_extraction,
)
from src.config import settings
from src.skills.base import Skill
from src.templates.base import ExtractedResult, Template
from src.tools.base import ToolRegistry, ToolSpec

logger = logging.getLogger(__name__)


def build_validator_config(skill: Skill) -> ValidatorConfig:
    """Build a ValidatorConfig from global settings + skill overrides.

    Args:
        skill: The active skill, whose confidence_overrides take precedence.

    Returns:
        A ValidatorConfig with thresholds merged from settings and skill.
    """
    return ValidatorConfig(
        default_confidence_threshold=settings.default_confidence_threshold,
        per_field_thresholds=skill.confidence_overrides,
    )


def build_initial_state(
    document_path: str,
    template: type[Template],
    skill: Skill,
    task_type: str = "extraction",
    page_paths: list[str] | None = None,
    confidence_threshold: float | None = None,
) -> AgentState:
    """Construct the initial AgentState for a run.

    The state starts with a document handle (path, not pixels) [§2.7], the
    template schema, and empty extraction/trace. The agent's first action
    is typically detect_layout to populate the region index.

    Args:
        document_path: Path to the source document (image or PDF).
        template: The Pydantic template schema class.
        skill: The active skill.
        task_type: The task type for this run.
        page_paths: Optional list of per-page image paths from the document
            store. When provided, the DocumentHandle is initialized with
            the correct page count and page_paths, and DocumentState is
            initialized with matching page count [BLK-220]. When None or
            empty, falls back to single-page behavior (backward compat).

    Returns:
        The initial AgentState dict.
    """
    path = Path(document_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {document_path}")

    resolved = str(path.resolve())

    if page_paths:
        handle = DocumentHandle(
            path=resolved,
            pages=len(page_paths),
            page_paths=page_paths,
        )
        doc_state = DocumentState.from_page_count(len(page_paths))
    else:
        handle = DocumentHandle(
            path=resolved,
            pages=1,
            page_paths=[resolved],
        )
        doc_state = DocumentState.from_page_count(1)

    return AgentState(
        document=handle,
        template_schema=template,
        skill_name=skill.name,
        regions={},
        extraction={},
        trace=[],
        step=0,
        field_attempts={},
        total_cycles=0,
        status=RunStatus.PLANNING,
        attempted={},
        provider_errors=[],
        compaction_summary="",
        _planned_action=None,
        _tool_result=None,
        _compact_requested=False,
        document_state=doc_state,
        consecutive_non_improving=0,
        token_usage=[],
        total_tokens=0,
        total_cost_usd=0.0,
        task_type=task_type,
        confidence_threshold=confidence_threshold or settings.default_confidence_threshold,
    )


def build_tool_registry(tool_names: list[str] | None = None) -> ToolRegistry:
    """Build the ToolRegistry with v1 providers based on config [§9].

    Provider selection is config-driven. v1 uses hardcoded imports with
    config-based dispatch — a one-line swap with zero plugin infrastructure.
    The swappability win comes from the interface contract, not the loader.

    Args:
        tool_names: Optional list of tool names to include. When provided
            and non-empty, the registry is filtered to only those tools.
            Names not found in the full registry are logged as warnings.
            When None or empty, all available tools are registered (backward
            compat) [BLK-217].

    Returns:
        A populated ToolRegistry with all v1 tools registered.
    """
    registry = ToolRegistry()

    # --- OCR provider (config-driven) [§9] ---
    if settings.ocr_provider == "paddle":
        from src.providers.ocr_paddle import detect_layout, detect_text, ocr as _ocr_impl
        registry.register(
            ToolSpec(
                name="detect_layout",
                description="Detect layout regions (text, table, figure) in a document image.",
                arg_schema={"image_path": str},
                return_description="List of regions with type, bbox, and confidence.",
                cacheable=True,
            ),
            detect_layout,
        )
        registry.register(
            ToolSpec(
                name="detect_text",
                description="Detect text boxes in an image with bounding boxes and scores.",
                arg_schema={"image_path": str, "lang": str},
                return_description="List of text boxes with bbox and confidence.",
            ),
            detect_text,
        )
        registry.register(
            ToolSpec(
                name="ocr",
                description="Run OCR on an image, returning full text with grounding.",
                arg_schema={"image_path": str, "lang": str},
                return_description="Full text string with grounding bbox.",
                cacheable=True,
            ),
            _ocr_impl,
        )
    elif settings.ocr_provider == "tesseract":
        from src.providers.ocr_tesseract import ocr as _ocr_impl
        registry.register(
            ToolSpec(
                name="ocr",
                description="Run Tesseract OCR on an image, returning full text with grounding.",
                arg_schema={"image_path": str, "lang": str},
                return_description="Full text string with grounding bbox.",
                cacheable=True,
            ),
            _ocr_impl,
        )

    # --- VLM provider (config-driven) [§9] ---
    if settings.vlm_provider == "azure":
        from src.providers.vlm_azure import vlm, read_chart, read_table
        registry.register(
            ToolSpec(
                name="vlm",
                description="Ask the VLM a question about an image (GPT-5.4 vision).",
                arg_schema={"image_path": str, "question": str, "model": str},
                return_description="Answer string from the VLM.",
                cacheable=True,
            ),
            vlm,
        )
        registry.register(
            ToolSpec(
                name="read_table",
                description="Extract a table from an image as structured data using VLM.",
                arg_schema={"image_path": str, "question": str},
                return_description="Structured table data.",
                cacheable=True,
            ),
            read_table,
        )
        registry.register(
            ToolSpec(
                name="read_chart",
                description="Extract structured data series from a chart/infographic image using VLM. Bypasses OCR — VLM interprets chart geometry directly.",
                arg_schema={"image_path": str, "chart_type": str, "question": str},
                return_description='Structured dict: {"series": [...], "x_axis": [...], "y_axis": {...}, "chart_type": "..."}.',
                cacheable=True,
            ),
            read_chart,
        )

    # --- Geometry provider (PIL + OpenCV) [§9] ---
    from src.providers.image_cv import (
        auto_orient,
        crop,
        denoise,
        deskew,
        resize,
        rotate,
        threshold,
    )
    registry.register(
        ToolSpec(
            name="crop",
            description="Crop a region from an image given a bounding box.",
            arg_schema={"image_path": str, "bbox": tuple},
            return_description="Path to the cropped image.",
            cacheable=True,
        ),
        crop,
    )
    registry.register(
        ToolSpec(
            name="rotate",
            description="Rotate an image by an explicit angle (agent-supplied, deliberate only).",
            arg_schema={"image_path": str, "angle": float},
            return_description="Path to the rotated image.",
        ),
        rotate,
    )
    registry.register(
        ToolSpec(
            name="deskew",
            description="Auto-deskew an image by estimating the skew angle (no agent input needed).",
            arg_schema={"image_path": str},
            return_description="Path to the deskewed image.",
            is_auto_geometry=True,
            cacheable=True,
        ),
        deskew,
    )
    registry.register(
        ToolSpec(
            name="auto_orient",
            description="Auto-orient an image using EXIF or layout estimation (no agent input needed).",
            arg_schema={"image_path": str},
            return_description="Path to the oriented image.",
            is_auto_geometry=True,
        ),
        auto_orient,
    )
    registry.register(
        ToolSpec(
            name="resize",
            description="Resize an image by a scale factor.",
            arg_schema={"image_path": str, "scale": float},
            return_description="Path to the resized image.",
        ),
        resize,
    )
    registry.register(
        ToolSpec(
            name="denoise",
            description="Denoise an image using fastNlMeansDenoising.",
            arg_schema={"image_path": str},
            return_description="Path to the denoised image.",
        ),
        denoise,
    )
    registry.register(
        ToolSpec(
            name="threshold",
            description="Apply adaptive thresholding to enhance text on noisy backgrounds.",
            arg_schema={"image_path": str},
            return_description="Path to the thresholded image.",
        ),
        threshold,
    )

    logger.info(
        "ToolRegistry built with %d tools: %s",
        len(registry.names()),
        ", ".join(registry.names()),
    )

    if len(registry.names()) == 0:
        raise RuntimeError(
            f"Tool registry is empty. Check provider configuration: "
            f"ocr_provider={settings.ocr_provider}, "
            f"vlm_provider={settings.vlm_provider}. "
            f"Ensure required packages are installed."
        )

    # --- Graph extraction tools [BLK-110] ---
    from src.tools.graph.symbol_detection import detect_symbols, classify_symbol
    from src.tools.graph.connection import detect_connections, trace_line
    from src.tools.graph.tag_reading import read_tag
    from src.tools.graph.graph_building import build_graph, validate_topology
    from src.tools.graph.serialization import serialize_graph

    registry.register(
        ToolSpec(
            name="detect_symbols",
            description="Detect engineering symbols in a P&ID diagram using VLM.",
            arg_schema={"image_path": str, "symbol_library": str},
            return_description="List of symbols with bbox, class, and confidence.",
        ),
        detect_symbols,
    )
    registry.register(
        ToolSpec(
            name="classify_symbol",
            description="Classify a single symbol at a given bounding box using VLM.",
            arg_schema={"image_path": str, "bbox": tuple},
            return_description="Symbol class and confidence.",
        ),
        classify_symbol,
    )
    registry.register(
        ToolSpec(
            name="detect_connections",
            description="Detect pipe connections between symbols in a P&ID diagram.",
            arg_schema={"image_path": str, "symbols": list},
            return_description="List of connections with from_id, to_id, path, type, confidence.",
        ),
        detect_connections,
    )
    registry.register(
        ToolSpec(
            name="trace_line",
            description="Trace a pipe line from a starting point through the diagram.",
            arg_schema={"image_path": str, "start_point": tuple, "direction": str},
            return_description="Path bboxes, end point, connected symbol, confidence.",
        ),
        trace_line,
    )
    registry.register(
        ToolSpec(
            name="read_tag",
            description="Read and parse an ISA-5.1 instrument tag from a diagram region.",
            arg_schema={"image_path": str, "bbox": tuple},
            return_description="Tag string, parsed ISA-5.1 components, and confidence.",
            cacheable=True,
        ),
        read_tag,
    )
    registry.register(
        ToolSpec(
            name="build_graph",
            description="Build a graph structure from detected symbols and connections.",
            arg_schema={"symbols": list, "connections": list},
            return_description="Graph dict with nodes and edges.",
        ),
        build_graph,
    )
    registry.register(
        ToolSpec(
            name="validate_topology",
            description="Validate graph topology against engineering rules.",
            arg_schema={"graph": dict, "rules": list},
            return_description="List of topology violations and overall ok flag.",
        ),
        validate_topology,
    )
    registry.register(
        ToolSpec(
            name="serialize_graph",
            description="Serialize a graph to json, graphml, dexpi_xml, or smart_pid_json.",
            arg_schema={"graph": dict, "format": str},
            return_description="Serialized graph content in the requested format.",
        ),
        serialize_graph,
    )

    # --- Table and signature detection tools [BLK-125, BLK-126] ---
    from src.tools.table_detection import detect_tables, read_table_cells
    from src.tools.signature_detection import detect_signatures

    registry.register(
        ToolSpec(
            name="detect_tables",
            description="Detect table structures in a document page with cell-level bounding boxes.",
            arg_schema={"image_path": str, "region": tuple},
            return_description="List of tables with bbox, rows, cols, cells (each with bbox).",
        ),
        detect_tables,
    )
    registry.register(
        ToolSpec(
            name="read_table_cells",
            description="Detect tables and OCR each cell, returning header-keyed row dicts. Composition of detect_tables + ocr.",
            arg_schema={"image_path": str, "table": dict, "region": tuple},
            return_description="Rows as list of dicts keyed by header text, plus headers list.",
        ),
        read_table_cells,
    )
    registry.register(
        ToolSpec(
            name="detect_signatures",
            description="Detect signature, stamp, and seal regions in a document page. Detection only — no authenticity verification.",
            arg_schema={"image_path": str, "region": tuple},
            return_description="List of marks with bbox, kind, confidence, is_handwritten, nearby_label, ink_coverage.",
        ),
        detect_signatures,
    )

    # --- Document classification tool [BLK-127] ---
    from src.tools.classify import classify_document as _classify_doc

    registry.register(
        ToolSpec(
            name="classify_document",
            description="Classify a document into a known type using VLM analysis. Returns ranked predictions with confidence scores and suggested agent definition IDs.",
            arg_schema={"image_path": str, "candidates": list, "page_paths": list},
            return_description="Ranked predictions with document_type, confidence, reasoning, and suggested_definition_id.",
        ),
        _classify_doc,
    )

    # Apply tool_names filter if provided [BLK-217]
    if tool_names:
        all_names = set(registry.names())
        wanted = set(tool_names)
        missing = wanted - all_names
        if missing:
            logger.warning(
                "tool_names references unknown tools (ignored): %s [BLK-217]",
                ", ".join(sorted(missing)),
            )
        for name in list(registry.names()):
            if name not in wanted:
                registry._tools.pop(name, None)
        if not registry.names():
            raise RuntimeError(
                f"Tool registry is empty after filtering by tool_names={tool_names}. "
                f"None of the requested tools exist in the registry. "
                f"Available: {sorted(all_names)}"
            )
        logger.info(
            "ToolRegistry filtered to %d tools: %s [BLK-217]",
            len(registry.names()),
            ", ".join(registry.names()),
        )

    return registry


def run(
    template: type[Template],
    skill: Skill,
    document: str,
) -> ExtractedResult:
    """Execute an extraction run: Template + Skill + Document -> ExtractedResult.

    This is the public API. It builds the initial state, constructs the tool
    registry, and invokes the LangGraph ReAct loop. On completion (or
    give-up), it returns an ExtractedResult with grounding and trace.

    Args:
        template: The Pydantic template schema class defining the outcome.
        skill: The skill playbook for this document type.
        document: Path to the source document (image or PDF).

    Returns:
        An ExtractedResult. If the run gave up [§2.6], is_complete is False
        and gap_report describes the unresolved fields.

    Example:
        >>> from src.templates.invoice import InvoiceTemplate
        >>> from src.skills.invoice import InvoiceSkill
        >>> result = run(InvoiceTemplate, InvoiceSkill, "invoice.png")
        >>> print(result.is_complete, result.values)
    """
    logger.info(
        "Starting extraction run",
        extra={
            "document": document,
            "template": template.__name__,
            "skill": skill.name,
        },
    )

    state = build_initial_state(document, template, skill)
    registry = build_tool_registry()
    validator_config = build_validator_config(skill)

    # Build and invoke the LangGraph ReAct loop [§2.2, §4]
    from src.agent.graph import build_react_graph, CircuitBreaker

    breaker = CircuitBreaker(threshold=3)
    graph = build_react_graph(
        registry=registry,
        skill=skill,
        validator_config=validator_config,
        breaker=breaker,
    )

    final_state = graph.invoke(state, config={"recursion_limit": settings.max_cycles_per_document + 10})

    result = final_state.get("result")
    if result is None:
        # Fallback: build result from state if terminate node didn't run
        gap_report = validate_extraction(
            schema=template,
            extraction=final_state.get("extraction", {}),
            invariants=skill.invariants,
            config=validator_config,
            failure_actions=skill.failure_actions,
        )
        status = final_state.get("status", RunStatus.PARTIAL)
        result = ExtractedResult(
            is_complete=status == RunStatus.COMPLETE,
            values=None,
            field_values=final_state.get("extraction", {}),
            gap_report=gap_report,
            trace=final_state.get("trace", []),
            total_cycles=final_state.get("total_cycles", 0),
            status=status,
            provider_errors=final_state.get("provider_errors", []),
        )

    logger.info(
        "Extraction run complete: status=%s, cycles=%d, gaps=%d",
        result.status,
        result.total_cycles,
        len(result.gap_report.gaps),
    )

    return result
