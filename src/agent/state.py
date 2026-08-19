"""LangGraph State for the ReAct extraction loop.

The State contract is the backbone of the agent. It enforces:
  - Image handles, not pixels [§2.7] — State carries paths/IDs, never base64.
  - Region index, not images [§12.1] — the agent reasons over Region metadata.
  - Cycle caps [§2.6] — per-field and per-document give-up thresholds.
  - Trace compaction [§12.3] — a rolling window of act/observe pairs, with
    resolved fields pruned by code, not by an LLM summarizer.

LangGraph requires State to be a TypedDict (or Pydantic model) that is
reduced across nodes. We use TypedDict with explicit keys so each node
declares which keys it reads and writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TypedDict

from src.agent.validator import GapReport
from src.tools.base import FieldValue, Region, ToolResult


# ---------------------------------------------------------------------------
# Trace entries (the rolling window) [§12.3]
# ---------------------------------------------------------------------------

@dataclass
class TraceEntry:
    """A single act/observe cycle in the ReAct trace.

    Only the last K entries are kept in the active trace (the rolling window).
    The full trace persists in the LangGraph checkpoint for eval/debug.

    Attributes:
        step: Monotonic step counter across the run.
        thought: The agent's reasoning for this action (from the plan node).
        tool_name: Name of the tool called.
        tool_args: Arguments passed to the tool (serializable).
        result: The ToolResult returned by the tool.
        field: Dotted field path this step was targeting, if any.
    """

    step: int
    thought: str
    tool_name: str
    tool_args: dict[str, Any]
    result: ToolResult
    field: str | None = None

    @property
    def tool(self) -> str:
        """Alias for tool_name — used by compact_node formatting [§12.4]."""
        return self.tool_name

    @property
    def args(self) -> dict[str, Any]:
        """Alias for tool_args — used by compact_node formatting [§12.4]."""
        return self.tool_args

    @property
    def result_summary(self) -> str:
        """Short summary of the tool result for compaction [§12.4]."""
        if self.result.ok:
            data = str(self.result.data) if self.result.data is not None else ""
            if len(data) > 80:
                data = data[:80] + "..."
            return f"ok: {data}"
        return f"error: {self.result.error}"


# ---------------------------------------------------------------------------
# Token usage tracking [BLK-050, §15]
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    """Token consumption for a single LLM call [BLK-050].

    Attributes:
        node: Which graph node made the call ("plan", "compact", "semantic_check").
        cycle: ReAct cycle number.
        input_tokens: Number of input (prompt) tokens.
        output_tokens: Number of output (completion) tokens.
        total_tokens: input_tokens + output_tokens.
        cost_usd: Calculated cost based on model pricing.
        timestamp: ISO 8601 UTC timestamp.
    """

    node: str
    cycle: int
    input_tokens: int
    output_tokens: int
    total_tokens: int = 0
    cost_usd: float = 0.0
    timestamp: str = ""

    def __post_init__(self) -> None:
        if self.total_tokens == 0:
            self.total_tokens = self.input_tokens + self.output_tokens
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSON persistence."""
        return {
            "node": self.node,
            "cycle": self.cycle,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Document handle (never pixels) [§2.7]
# ---------------------------------------------------------------------------

@dataclass
class DocumentHandle:
    """A reference to a document on disk, never its pixels.

    The agent and State interact with documents through this handle. Only
    a specific tool invocation (e.g. crop) materializes pixels, and only
    for the region it needs.

    Attributes:
        path: Filesystem path to the document (image or PDF).
        pages: Number of pages (1 for single-image documents).
        page_paths: Per-page image paths if the document was pre-rasterized.
            For single-image documents, this is [path].
    """

    path: str
    pages: int = 1
    page_paths: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Multi-page hierarchical state [BLK-041, §12.1]
# ---------------------------------------------------------------------------

class PageStatus(str, Enum):
    """Status of a single page in the document hierarchy."""

    PENDING = "pending"
    SCANNED = "scanned"
    EXTRACTED = "extracted"
    SKIPPED = "skipped"


@dataclass
class PageState:
    """State for a single page in a multi-page document [BLK-041].

    Stores region metadata only — never pixels [§2.7]. The agent navigates
    the page hierarchy to bound context on large documents.

    Attributes:
        page_number: Zero-based page index.
        regions: Region index for this page, keyed by region ID.
        status: Current page status.
        fields_extracted: Set of field paths extracted from this page.
        text_summary: Optional OCR text summary for the page.
    """

    page_number: int
    regions: dict[str, Region] = field(default_factory=dict)
    status: PageStatus = PageStatus.PENDING
    fields_extracted: set[str] = field(default_factory=set)
    text_summary: str = ""

    def add_region(self, region: Region) -> None:
        """Add a region to this page."""
        self.regions[region.id] = region

    def mark_scanned(self) -> None:
        """Mark page as scanned (layout detected)."""
        self.status = PageStatus.SCANNED

    def mark_extracted(self, field_path: str) -> None:
        """Mark a field as extracted from this page."""
        self.fields_extracted.add(field_path)
        self.status = PageStatus.EXTRACTED


@dataclass
class DocumentState:
    """Hierarchical document state: Document → Pages → Regions [BLK-041].

    Replaces the flat region index for multi-page documents. The plan node
    navigates this hierarchy to generate focused working sets, avoiding
    context dilution on 60-page leases or 100-page audits.

    Attributes:
        pages: List of PageState, one per page.
        total_pages: Total number of pages in the document.
        current_page: The page the agent is currently focused on.
    """

    pages: list[PageState] = field(default_factory=list)
    total_pages: int = 1
    current_page: int = 0

    @classmethod
    def from_page_count(cls, total_pages: int) -> DocumentState:
        """Create a DocumentState with the given number of empty pages."""
        return cls(
            pages=[PageState(page_number=i) for i in range(total_pages)],
            total_pages=total_pages,
        )

    def get_page(self, page_number: int) -> PageState | None:
        """Get PageState for a specific page, or None if out of range."""
        if 0 <= page_number < len(self.pages):
            return self.pages[page_number]
        return None

    @property
    def current_page_state(self) -> PageState | None:
        """Get the current page's state."""
        return self.get_page(self.current_page)

    def navigate_to(self, page_number: int) -> bool:
        """Navigate to a specific page. Returns True if valid."""
        if 0 <= page_number < self.total_pages:
            self.current_page = page_number
            return True
        return False

    def all_regions(self) -> dict[str, Region]:
        """Flatten all regions across all pages into a single dict.

        Useful for backward compatibility with code that expects a flat
        region index.
        """
        result: dict[str, Region] = {}
        for page in self.pages:
            result.update(page.regions)
        return result

    def pages_with_field(self, field_path: str) -> list[int]:
        """Get page numbers that have already extracted the given field."""
        return [
            p.page_number for p in self.pages
            if field_path in p.fields_extracted
        ]

    def summary(self) -> str:
        """Brief text summary of document state for plan node context."""
        lines = [f"Document: {self.total_pages} pages, current: page {self.current_page}"]
        for page in self.pages:
            n_regions = len(page.regions)
            n_fields = len(page.fields_extracted)
            lines.append(
                f"  Page {page.page_number}: {page.status.value}, "
                f"{n_regions} regions, {n_fields} fields extracted"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The LangGraph State
# ---------------------------------------------------------------------------

class AgentState(TypedDict, total=False):
    """The full state of a single extraction run.

    Nodes read and write subsets of these keys. LangGraph reduces the state
    across nodes. The ``total=False`` allows nodes to return only the keys
    they modify.

    Keys:
        document: Handle to the source document (paths, not pixels) [§2.7].
        template_schema: The Pydantic schema class defining the outcome
            contract [§3.1].
        skill_name: Name of the active Skill [§3.2].
        regions: Region index — the layout map the agent reasons over [§12.1].
            Keyed by region ID for O(1) lookup.
        extraction: Partial extraction: field path -> FieldValue. Filled
            incrementally as the agent works.
        gap_report: The latest deterministic GapReport from the validator
            [§4.1]. Drives the next plan step.
        trace: Rolling window of TraceEntry (last K cycles) [§12.3].
        step: Monotonic step counter.
        field_attempts: Per-field attempt count for give-up enforcement [§2.6].
        total_cycles: Total ReAct cycles across the run [§2.6].
        status: Current run status (see RunStatus).
        result: Final ExtractedResult on termination.
        attempted: Per-region set of "tool:args_hash" strings that failed,
            for retry-loop prevention [§12.3]. Lives outside the rolling
            trace window so failures are never forgotten mid-run.
        provider_errors: List of provider error messages accumulated during
            the run, included in ExtractedResult for debugging [§2.7].
        compaction_summary: LLM-generated narrative summary of the trace,
            produced by the compact node [§12.4]. Replaces raw trace entries
            in the plan node's LLM prompt after compaction. Empty string
            until first compaction.
        _compact_requested: Flag set by manual /compaction action from
            frontend [§12.4]. When true, the next reflect→plan transition
            routes to compact regardless of trace length.
    """

    document: DocumentHandle
    template_schema: type
    skill_name: str
    regions: dict[str, Region]
    extraction: dict[str, FieldValue]
    gap_report: GapReport
    trace: list[TraceEntry]
    step: int
    field_attempts: dict[str, int]
    total_cycles: int
    status: str
    result: Any
    attempted: dict[str, set[str]]
    provider_errors: list[str]
    compaction_summary: str
    _planned_action: Any
    _tool_result: Any
    _compact_requested: bool
    document_state: DocumentState
    consecutive_non_improving: int
    token_usage: list[TokenUsage]
    total_tokens: int
    total_cost_usd: float
    task_type: str
    confidence_threshold: float


# ---------------------------------------------------------------------------
# Run status constants
# ---------------------------------------------------------------------------

class RunStatus:
    """Status values for the run lifecycle."""

    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETE = "complete"
    PARTIAL = "partial"       # give-up: some fields unresolved [§2.6]
    PAUSED = "paused"         # auto-pause or manual pause [BLK-049, BLK-095]
    ERROR = "error"
    CANCELLED = "cancelled"   # user-requested cancellation [BLK-129]


# ---------------------------------------------------------------------------
# Trace compaction helper [§12.3]
# ---------------------------------------------------------------------------

def compact_trace(
    trace: list[TraceEntry],
    window_size: int,
    resolved_fields: set[str],
) -> list[TraceEntry]:
    """Prune the trace to a rolling window, dropping entries for resolved fields.

    Resolved fields have their final values in ``extraction``; their
    intermediate act/observe cycles are pruned from the active trace to bound
    context growth. The full trace remains in the LangGraph checkpoint.

    Args:
        trace: The current trace.
        window_size: Max number of entries to keep (K).
        resolved_fields: Field paths that are now satisfied and should be
            pruned from the active trace.

    Returns:
        The compacted trace (last ``window_size`` entries, excluding those
        targeting resolved fields).
    """
    pruned = [
        entry for entry in trace
        if entry.field not in resolved_fields
    ]
    return pruned[-window_size:] if len(pruned) > window_size else pruned
