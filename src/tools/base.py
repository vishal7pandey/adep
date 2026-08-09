"""Core type contracts for ADE tools.

Every tool, provider, agent node, and skill depends on the types defined here.
The contracts enforce the vision's core rules:
  - Grounding is non-negotiable (every value carries a bbox) [§2.5]
  - State carries handles, not pixels [§2.7]
  - Tools are atomic with explicit arg/return schemas [§2.3]
  - Geometry tools split by who computes the parameter [§2.3]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol, runtime_checkable

from src.config import settings


# ---------------------------------------------------------------------------
# Spatial primitives
# ---------------------------------------------------------------------------

BBox = tuple[int, int, int, int]
"""Axis-aligned bounding box in pixel coordinates: (x1, y1, x2, y2)."""


class RegionType(str, Enum):
    """Semantic category of a detected document region."""

    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    CHART = "chart"
    LOGO = "logo"
    SIGNATURE = "signature"
    STAMP = "stamp"
    HANDWRITING = "handwriting"
    MARGINALIA = "marginalia"
    HEADER = "header"
    FOOTER = "footer"
    LIST = "list"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Grounding:
    """Source location of an extracted value, traced to specific pixels.

    Non-negotiable: every FieldValue must carry one [§2.5]. No grounding,
    no value.

    Attributes:
        bbox: Pixel coordinates (x1, y1, x2, y2) relative to the page image.
        page: Zero-based page index.
        region_id: ID of the RegionState this grounding belongs to, if any.
        source_tool: Name of the tool that produced this grounding.
        confidence: Tool-reported confidence in the grounding itself
            (e.g. OCR recognition score), in [0.0, 1.0].
    """

    bbox: BBox
    page: int = 0
    region_id: str | None = None
    source_tool: str = ""
    confidence: float = 0.0


# ---------------------------------------------------------------------------
# Region index (lives in State; never carries pixels) [§2.7, §12.1]
# ---------------------------------------------------------------------------

@dataclass
class Region:
    """A detected region in the document's layout.

    Regions form the index the agent reasons over. They carry metadata only —
    never image data. To inspect a region's pixels, the agent calls
    ``crop(page, bbox)`` which materializes only that region for the tool.

    Attributes:
        id: Stable identifier within the run (e.g. "p0_r3").
        type: Semantic category of the region.
        bbox: Pixel coordinates (x1, y1, x2, y2) on the page.
        page: Zero-based page index.
        text: OCR text snippet if the region has been read, else None.
        confidence: OCR/recognition confidence if text is present.
        metadata: Extra provider-specific data (e.g. cell grid for tables).
    """

    id: str
    type: RegionType
    bbox: BBox
    page: int = 0
    text: str | None = None
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Extraction values
# ---------------------------------------------------------------------------

@dataclass
class FieldValue:
    """A single extracted field value with grounding and confidence.

    Attributes:
        name: Dotted path to the field in the template schema
            (e.g. "total", "line_items[0].quantity").
        value: The extracted value (str, int, float, bool, or nested dict).
        grounding: Source location of the value. Required for a value to be
            considered valid [§2.5].
        confidence: Overall confidence in the value, in [0.0, 1.0]. Derived
            from the source tool's confidence and any verification steps.
        attempts: Number of ReAct cycles spent on this field so far.
    """

    name: str
    value: Any
    grounding: Grounding | None = None
    confidence: float = 0.0
    attempts: int = 0


# ---------------------------------------------------------------------------
# Tool results
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Structured return value from any atomic tool.

    Tools never return raw strings or bare images. They return a ToolResult
    so the agent (and the trace) always has a consistent shape to reason over.

    Attributes:
        ok: Whether the tool call succeeded.
        data: Tool-specific structured output (text, boxes, regions, etc.).
        grounding: Source location if the tool produced a grounded value.
        error: Error message if ``ok`` is False.
        tool: Name of the tool that produced this result.
        cost: Optional cost metadata (tokens, latency_ms) for observability.
    """

    ok: bool
    data: Any = None
    grounding: Grounding | None = None
    error: str = ""
    tool: str = ""
    cost: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Tool specification and registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolSpec:
    """Declarative specification of an atomic tool.

    Tools register themselves with a ToolSpec. The agent sees only the name,
    description, and arg schema — enough to decide when to call the tool and
    with what parameters, without knowing the provider backend.

    Attributes:
        name: Unique tool name (e.g. "ocr", "crop", "vlm").
        description: What the tool does, for the agent's reasoning.
        arg_schema: Pydantic model or JSON schema describing the arguments.
        return_description: Human-readable description of the return shape.
        is_auto_geometry: True for auto-estimating geometry tools
            (deskew, auto_orient) that take no agent-supplied geometric
            parameter [§2.3]. Used to hint the agent.
    """

    name: str
    description: str
    arg_schema: type | dict[str, Any] = field(default_factory=dict)
    return_description: str = ""
    is_auto_geometry: bool = False
    cacheable: bool = False


@runtime_checkable
class ToolFunc(Protocol):
    """Protocol every tool function satisfies.

    A tool takes a dict of arguments (validated against its ToolSpec
    arg_schema) and returns a ToolResult. Tools are stateless and composable.
    """

    def __call__(self, **kwargs: Any) -> ToolResult: ...


@dataclass
class ToolRegistry:
    """Registry of available tools for a run.

    The registry maps tool names to their spec and callable. The agent
    discovers tools through the registry; providers are swappable behind the
    same tool interface [§9].

    Attributes:
        _tools: Maps tool name to (ToolSpec, ToolFunc).
    """

    _tools: dict[str, tuple[ToolSpec, ToolFunc]] = field(default_factory=dict)

    def register(self, spec: ToolSpec, func: ToolFunc) -> None:
        """Register a tool under its spec name."""
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._tools[spec.name] = (spec, func)

    def get(self, name: str) -> tuple[ToolSpec, ToolFunc]:
        """Retrieve a tool by name."""
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def call(self, name: str, **kwargs: Any) -> ToolResult:
        """Invoke a tool by name with keyword arguments.

        If the tool's ToolSpec has cacheable=True and caching is enabled,
        checks the cache first. On hit, returns the cached result. On miss,
        invokes the tool and stores the result in the cache [BLK-124].
        """
        spec, func = self.get(name)

        # Check cache for cacheable tools [BLK-124]
        if spec.cacheable and settings.cache_enabled:
            from src.tools.cache import get_cache, compute_cache_key

            image_path = kwargs.get("image_path")
            cache_key = compute_cache_key(
                tool_name=name,
                image_path=image_path if isinstance(image_path, str) else None,
                params={k: v for k, v in kwargs.items() if k != "image_path"},
                provider=settings.vlm_provider if name in ("vlm", "read_chart", "read_table") else settings.ocr_provider,
            )
            cache = get_cache()
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

        result = func(**kwargs)
        if not result.tool:
            result.tool = name

        # Store in cache for cacheable tools [BLK-124]
        if spec.cacheable and settings.cache_enabled:
            from src.tools.cache import get_cache

            image_path = kwargs.get("image_path")
            cache.put(cache_key, result, tool_name=name, image_path=image_path if isinstance(image_path, str) else None)

        return result

    def specs(self) -> list[ToolSpec]:
        """All registered tool specs (for the agent's context)."""
        return [spec for spec, _ in self._tools.values()]

    def names(self) -> list[str]:
        """All registered tool names."""
        return list(self._tools.keys())
