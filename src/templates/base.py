"""Template base and ExtractedResult [§3.1, §7, §20].

A Template is a declarative extraction spec: a Pydantic schema with field
descriptions, types, constraints, and confidence thresholds. It is
document-agnostic — it says *what* a valid result looks like, nothing about
*how* to obtain it.

ExtractedResult is the output of a run: the filled schema instance plus
grounding, confidence, and a full trace for debugging and evaluation.

BLK-109 generalizes these into OutputContract and RunResult hierarchies
to support graph extraction and other task types beyond flat field
extraction. Template and ExtractedResult remain as aliases for backward
compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from src.agent.state import TraceEntry
from src.agent.validator import GapReport
from src.tools.base import BBox, FieldValue


# ---------------------------------------------------------------------------
# Output Contract hierarchy [BLK-109, §20]
# ---------------------------------------------------------------------------


class OutputContract(BaseModel):
    """Base class for all output contracts [BLK-109].

    An OutputContract defines *what* a valid result looks like for a given
    task type. Subclasses define the specific schema or graph structure.

    Attributes:
        task_type: Identifies the type of task (e.g. "extraction",
            "graph_extraction"). Used by the validator to dispatch.
        name: Human-readable contract name.
        description: What this contract represents.
    """

    task_type: str = Field(default="extraction", description="Task type identifier")
    name: str = Field(default="", description="Human-readable contract name")
    description: str = Field(default="", description="What this contract represents")

    model_config = {"arbitrary_types_allowed": True}


class FieldExtractionContract(OutputContract):
    """Output contract for flat field extraction [BLK-109].

    This is the current Template behavior — a Pydantic schema with fields
    describing the outcome. Subclass this with Pydantic fields.

    Example:
        class InvoiceTemplate(FieldExtractionContract):
            invoice_number: str = Field(description="Vendor invoice ID")
            total: float = Field(description="Total amount due")
    """

    task_type: str = Field(default="extraction", description="Task type identifier")


class GraphExtractionContract(OutputContract):
    """Output contract for graph extraction [BLK-109, §20].

    Defines a graph structure with node types, edge types, topology rules,
    and output serialization formats. Used for P&ID → DEXPI and similar
    graph extraction tasks.

    Attributes:
        node_types: Specifications for each node type in the graph.
        edge_types: Specifications for each edge type.
        required_attributes: Per-node-type required attributes.
        topology_rules: Rules the graph topology must satisfy.
        output_formats: Supported serialization formats (e.g. "dexpi", "graphml").
    """

    task_type: str = Field(default="graph_extraction", description="Task type identifier")
    node_types: list[dict[str, Any]] = Field(default_factory=list)
    edge_types: list[dict[str, Any]] = Field(default_factory=list)
    required_attributes: dict[str, list[str]] = Field(default_factory=dict)
    topology_rules: list[dict[str, Any]] = Field(default_factory=list)
    output_formats: list[str] = Field(default_factory=lambda: ["graphml"])


# Backward-compatible alias — all existing templates use Template [BLK-109]
Template = FieldExtractionContract


# ---------------------------------------------------------------------------
# Run Result hierarchy [BLK-109, §20]
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    """Base class for all run results [BLK-109].

    The output of a run. Subclasses add task-specific data (field values
    for extraction, graph for graph extraction).

    Even on give-up [§2.6], a run returns a RunResult with
    ``is_complete=False`` and the gaps populated — a failed extraction is a
    structured object, not an exception.

    Attributes:
        is_complete: True if all fields/nodes/edges were satisfied.
        gap_report: The final GapReport (empty if complete).
        trace: Full trace of tool calls for debugging and evaluation.
        total_cycles: Total ReAct cycles executed.
        status: RunStatus value (complete / partial / error).
        provider_errors: List of provider error messages accumulated during
            the run, for debugging [§2.7].
        token_usage_summary: Token usage breakdown by provider.
    """

    is_complete: bool
    gap_report: GapReport = field(default_factory=GapReport)
    trace: list[TraceEntry] = field(default_factory=list)
    total_cycles: int = 0
    status: str = "complete"
    provider_errors: list[str] = field(default_factory=list)
    token_usage_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class FieldExtractionResult(RunResult):
    """Result of a field extraction run [BLK-109].

    Attributes:
        values: The filled template instance, or a partial dict if incomplete.
        field_values: Per-field FieldValue with grounding and confidence.
    """

    values: Any = None
    field_values: dict[str, FieldValue] = field(default_factory=dict)


@dataclass
class GraphExtractionResult(RunResult):
    """Result of a graph extraction run [BLK-109, §20].

    Attributes:
        graph: The extracted graph with nodes and edges.
        node_grounding: Maps node ID to bounding box in the source image.
        edge_grounding: Maps edge ID to list of bounding boxes along the
            connection path.
        serialized_output: Maps format name to serialized string (e.g.
            {"dexpi": "<xml>...", "graphml": "<graphml>..."}).
    """

    graph: dict[str, Any] = field(default_factory=lambda: {"nodes": [], "edges": []})
    node_grounding: dict[str, BBox] = field(default_factory=dict)
    edge_grounding: dict[str, list[BBox]] = field(default_factory=dict)
    serialized_output: dict[str, str] = field(default_factory=dict)


# Backward-compatible alias — all existing code uses ExtractedResult [BLK-109]
ExtractedResult = FieldExtractionResult
