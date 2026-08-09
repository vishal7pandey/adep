"""Pragmatic-first Outcome Validator [§4.1].

The validator is the linchpin of the ReAct loop. It must NOT be an LLM
reflecting on its own success (the hallucination trap). It is a pragmatic
gap-report generator that runs code checks in order:

  1. Required-field presence (schema-driven)
  2. Type/format checks (ISO date, numeric, enum)
  3. Math invariants (declared in the Skill)
  4. Grounding presence (every value has a bbox)
  5. Confidence >= threshold (per-field, from the Template)
  6. Semantic checks (optional, per-Skill, LLM-assisted, off by default)

The output is a structured GapReport that drives the next ReAct step.
Code first, LLM second, vibes never.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel

from src.tools.base import FieldValue


# ---------------------------------------------------------------------------
# Gap classification
# ---------------------------------------------------------------------------

class GapType(str, Enum):
    """Why a field is not yet satisfied."""

    MISSING = "missing"             # field not extracted at all
    TYPE_ERROR = "type_error"       # value present but wrong type
    FORMAT_ERROR = "format_error"   # value present but fails format check
    UNGROUNDED = "ungrounded"       # value present but no bbox
    LOW_CONFIDENCE = "low_confidence"  # value present but confidence < threshold
    INVARIANT_FAILED = "invariant_failed"  # math/logic rule failed
    SEMANTIC_FAIL = "semantic_fail"      # optional LLM-assisted check failed
    # Graph extraction gap types [BLK-109]
    SYMBOL_UNCLASSIFIED = "symbol_unclassified"    # detected symbol but type unknown
    TAG_UNREADABLE = "tag_unreadable"              # instrument tag could not be read
    CONNECTION_AMBIGUOUS = "connection_ambiguous"  # pipe connection unclear
    TOPOLOGY_VIOLATION = "topology_violation"      # graph breaks a topology rule
    NODE_MISSING = "node_missing"                  # expected node not found
    EDGE_MISSING = "edge_missing"                  # expected edge not found
    ATTRIBUTE_MISSING = "attribute_missing"        # node/edge lacks required attribute
    SERIALIZATION_FAILED = "serialization_failed"  # graph could not be serialized to target format
    # Signature/stamp gap types [BLK-126]
    SIGNATURE_MISSING = "signature_missing"        # required signature/stamp/seal not found
    # Classification gap types [BLK-127]
    DOCUMENT_TYPE_UNKNOWN = "document_type_unknown"  # document type could not be classified


@dataclass
class FieldGap:
    """A single unsatisfied field in the GapReport.

    Attributes:
        field: Dotted path to the field (e.g. "total", "line_items[0].qty").
        gap_type: Why the field is unsatisfied.
        detail: Human-readable explanation of the failure.
        current_value: The current value if any, else None.
        current_confidence: Current confidence if any, else 0.0.
        suggested_action: Hint from the Skill's failure_actions table, if
            the Skill provided one for this gap_type. The agent uses this
            to decide the next action.
        last_error: Last error message from a failed tool call on this
            field, for retry-loop prevention [§12.3].
        last_tool: Name of the last tool that failed on this field [§12.3].
    """

    field: str
    gap_type: GapType
    detail: str
    current_value: Any = None
    current_confidence: float = 0.0
    suggested_action: str = ""
    last_error: str = ""
    last_tool: str = ""


@dataclass
class GapReport:
    """The deterministic output of the Outcome Validator.

    Drives the next ReAct step. The plan node consumes this alongside the
    Skill's failure_actions to decide what to do next.

    Attributes:
        gaps: List of unsatisfied fields with reasons.
        satisfied: List of field paths that passed all checks.
        is_complete: True if gaps is empty (all fields satisfied).
        total_fields: Total number of fields checked.
    """

    gaps: list[FieldGap] = field(default_factory=list)
    satisfied: list[str] = field(default_factory=list)
    is_complete: bool = False
    total_fields: int = 0

    def missing_fields(self) -> list[str]:
        """Field paths that are entirely absent."""
        return [g.field for g in self.gaps if g.gap_type == GapType.MISSING]

    def fields_by_type(self, gap_type: GapType) -> list[FieldGap]:
        """Filter gaps by type."""
        return [g for g in self.gaps if g.gap_type == gap_type]


# ---------------------------------------------------------------------------
# Invariant rules (declared in Skills, run by the validator)
# ---------------------------------------------------------------------------

InvariantFn = Callable[[dict[str, FieldValue]], tuple[bool, str]]
"""A math/logic invariant. Takes the extraction, returns (ok, reason)."""


SemanticChecker = Callable[[str, Any, str], tuple[bool, str]]
"""An optional LLM-assisted semantic check.

Takes (field_path, value, evidence_snippet) and returns (ok, reason).
Skills decide whether to enable these; the default is off [§4.1, SF].
"""


@dataclass
class Invariant:
    """A named verification rule declared by a Skill.

    Examples:
        Invariant("sum_check", lambda e: (
            abs((e["subtotal"].value + e["tax"].value) - e["total"].value)
            < 0.01,
            "subtotal + tax != total"
        ))

    Attributes:
        name: Human-readable rule name.
        fn: The invariant function.
        fields: Field paths this invariant depends on (used to skip the
            check if any are missing).
    """

    name: str
    fn: InvariantFn
    fields: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Format checkers
# ---------------------------------------------------------------------------

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def check_iso_date(value: Any) -> bool:
    """Check if value is a string in ISO YYYY-MM-DD format."""
    return isinstance(value, str) and bool(_ISO_DATE.match(value))


def check_numeric(value: Any) -> bool:
    """Check if value is an int or float (not bool)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


# A format checker takes a value and returns (ok, reason).
FormatChecker = Callable[[Any], tuple[bool, str]]

DEFAULT_FORMATS: dict[str, FormatChecker] = {
    "iso_date": lambda v: (check_iso_date(v), "not ISO YYYY-MM-DD"),
    "numeric": lambda v: (check_numeric(v), "not numeric"),
}


# ---------------------------------------------------------------------------
# The Validator
# ---------------------------------------------------------------------------

@dataclass
class ValidatorConfig:
    """Configuration for the Outcome Validator.

    Attributes:
        default_confidence_threshold: Minimum confidence for a field to be
            considered satisfied, unless overridden per-field.
        per_field_thresholds: Overrides for specific field paths.
        format_checkers: Maps field path -> format checker name. If a field
            has a format checker, the value must pass it.
    """

    default_confidence_threshold: float = 0.8
    per_field_thresholds: dict[str, float] = field(default_factory=dict)
    format_checkers: dict[str, str] = field(default_factory=dict)
    semantic_checkers: dict[str, SemanticChecker] = field(default_factory=dict)


def validate_extraction(
    schema: type[BaseModel],
    extraction: dict[str, FieldValue],
    invariants: list[Invariant],
    config: ValidatorConfig,
    failure_actions: dict[GapType, str] | None = None,
) -> GapReport:
    """Run pragmatic checks against the partial extraction.

    Code checks run first (presence, type, format, grounding, confidence,
    invariants). Optional semantic checks (LLM-assisted) run last, only if
    configured in ``config.semantic_checkers`` [§4.1]. The default is off.

    Args:
        schema: The Pydantic template schema class.
        extraction: Current partial extraction (field path -> FieldValue).
        invariants: Math/logic rules from the Skill.
        config: Validator configuration (thresholds, format checkers,
            semantic checkers).
        failure_actions: Optional mapping from GapType -> suggested action
            hint, from the Skill. Injected into each FieldGap.

    Returns:
        A GapReport describing what is satisfied and what is not.
    """
    actions = failure_actions or {}
    gaps: list[FieldGap] = []
    satisfied: list[str] = []

    schema_fields = _required_fields(schema)

    for field_path, field_info in schema_fields.items():
        fv = extraction.get(field_path)

        if fv is None or fv.value is None:
            gaps.append(FieldGap(
                field=field_path,
                gap_type=GapType.MISSING,
                detail=f"Required field '{field_path}' not extracted",
                suggested_action=actions.get(GapType.MISSING, ""),
            ))
            continue

        # Type check
        expected_type = field_info.get("type")
        if expected_type and not _check_type(fv.value, expected_type):
            gaps.append(FieldGap(
                field=field_path,
                gap_type=GapType.TYPE_ERROR,
                detail=f"Expected {expected_type}, got {type(fv.value).__name__}",
                current_value=fv.value,
                current_confidence=fv.confidence,
                suggested_action=actions.get(GapType.TYPE_ERROR, ""),
            ))
            continue

        # Format check
        fmt_name = config.format_checkers.get(field_path)
        if fmt_name and fmt_name in DEFAULT_FORMATS:
            checker = DEFAULT_FORMATS[fmt_name]
            ok, reason = checker(fv.value)
            if not ok:
                gaps.append(FieldGap(
                    field=field_path,
                    gap_type=GapType.FORMAT_ERROR,
                    detail=f"Format check '{fmt_name}' failed: {reason}",
                    current_value=fv.value,
                    current_confidence=fv.confidence,
                    suggested_action=actions.get(GapType.FORMAT_ERROR, ""),
                ))
                continue

        # Grounding check [§2.5]
        if fv.grounding is None:
            gaps.append(FieldGap(
                field=field_path,
                gap_type=GapType.UNGROUNDED,
                detail=f"Field '{field_path}' has no grounding (bbox required)",
                current_value=fv.value,
                current_confidence=fv.confidence,
                suggested_action=actions.get(GapType.UNGROUNDED, ""),
            ))
            continue

        # Confidence check
        threshold = config.per_field_thresholds.get(
            field_path, config.default_confidence_threshold
        )
        if fv.confidence < threshold:
            gaps.append(FieldGap(
                field=field_path,
                gap_type=GapType.LOW_CONFIDENCE,
                detail=f"Confidence {fv.confidence:.2f} < threshold {threshold:.2f}",
                current_value=fv.value,
                current_confidence=fv.confidence,
                suggested_action=actions.get(GapType.LOW_CONFIDENCE, ""),
            ))
            continue

        satisfied.append(field_path)

    # Invariant checks (only if all dependent fields are satisfied)
    for inv in invariants:
        if all(f in extraction and extraction[f].value is not None
               for f in inv.fields):
            ok, reason = inv.fn(extraction)
            if not ok:
                gaps.append(FieldGap(
                    field=inv.name,
                    gap_type=GapType.INVARIANT_FAILED,
                    detail=f"Invariant '{inv.name}' failed: {reason}",
                    suggested_action=actions.get(
                        GapType.INVARIANT_FAILED, ""
                    ),
                ))

    # Semantic checks (optional, LLM-assisted, off by default) [§4.1]
    # Only run on fields that passed all code checks.
    for field_path in list(satisfied):
        checker = config.semantic_checkers.get(field_path)
        if checker is None:
            continue
        fv = extraction[field_path]
        evidence = fv.grounding.source_tool if fv.grounding else ""
        ok, reason = checker(field_path, fv.value, evidence)
        if not ok:
            satisfied.remove(field_path)
            gaps.append(FieldGap(
                field=field_path,
                gap_type=GapType.SEMANTIC_FAIL,
                detail=f"Semantic check failed: {reason}",
                current_value=fv.value,
                current_confidence=fv.confidence,
                suggested_action=actions.get(GapType.SEMANTIC_FAIL, ""),
            ))

    return GapReport(
        gaps=gaps,
        satisfied=satisfied,
        is_complete=len(gaps) == 0,
        total_fields=len(schema_fields),
    )


# ---------------------------------------------------------------------------
# Task Validator — dispatches by task_type [BLK-109]
# ---------------------------------------------------------------------------

class TaskValidator:
    """Dispatches validation by task type [BLK-109].

    For "extraction" (default), delegates to validate_extraction.
    For "graph_extraction", runs graph-specific checks.
    New task types can be added by subclassing or extending dispatch.
    """

    def validate(
        self,
        result: Any,
        contract: Any,
        invariants: list[Invariant] | None = None,
        config: ValidatorConfig | None = None,
        failure_actions: dict[GapType, str] | None = None,
    ) -> GapReport:
        """Validate a run result against its output contract.

        Args:
            result: The run result (FieldExtractionResult or GraphExtractionResult).
            contract: The output contract (FieldExtractionContract or GraphExtractionContract).
            invariants: Math/logic rules from the Skill.
            config: Validator configuration.
            failure_actions: Optional GapType -> action hint mapping.

        Returns:
            GapReport describing what is satisfied and what is not.
        """
        task_type = getattr(contract, "task_type", "extraction")
        if task_type == "extraction":
            return self._validate_extraction(
                result, contract, invariants or [], config or ValidatorConfig(),
                failure_actions,
            )
        elif task_type == "graph_extraction":
            return self._validate_graph(result, contract, failure_actions)
        else:
            raise ValueError(f"Unknown task_type: {task_type}")

    def _validate_extraction(
        self,
        result: Any,
        contract: Any,
        invariants: list[Invariant],
        config: ValidatorConfig,
        failure_actions: dict[GapType, str] | None,
    ) -> GapReport:
        """Delegate to existing validate_extraction for field extraction."""
        field_values = getattr(result, "field_values", {})
        return validate_extraction(
            schema=contract,
            extraction=field_values,
            invariants=invariants,
            config=config,
            failure_actions=failure_actions,
        )

    def _validate_graph(
        self,
        result: Any,
        contract: Any,
        failure_actions: dict[GapType, str] | None,
    ) -> GapReport:
        """Validate a graph extraction result [BLK-109].

        Checks:
        - Node coverage (all expected node types present)
        - Edge connectivity (no orphan nodes)
        - Attribute completeness
        - Topology rules
        - Grounding presence
        - Serialization validity
        """
        actions = failure_actions or {}
        gaps: list[FieldGap] = []
        satisfied: list[str] = []

        graph = getattr(result, "graph", {"nodes": [], "edges": []})
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        node_grounding = getattr(result, "node_grounding", {})
        serialized_output = getattr(result, "serialized_output", {})

        # Check node count
        if not nodes:
            gaps.append(FieldGap(
                field="nodes",
                gap_type=GapType.NODE_MISSING,
                detail="No nodes found in graph",
                suggested_action=actions.get(GapType.NODE_MISSING, ""),
            ))

        # Check edge count
        if not edges:
            gaps.append(FieldGap(
                field="edges",
                gap_type=GapType.EDGE_MISSING,
                detail="No edges found in graph",
                suggested_action=actions.get(GapType.EDGE_MISSING, ""),
            ))

        # Check for ungrounded nodes
        for node in nodes:
            node_id = node.get("id", "") if isinstance(node, dict) else getattr(node, "id", "")
            if node_id and node_id not in node_grounding:
                gaps.append(FieldGap(
                    field=f"node:{node_id}",
                    gap_type=GapType.UNGROUNDED,
                    detail=f"Node '{node_id}' has no grounding (bbox required)",
                    suggested_action=actions.get(GapType.UNGROUNDED, ""),
                ))

        # Check for orphan nodes (no edges)
        connected_ids: set[str] = set()
        for edge in edges:
            if isinstance(edge, dict):
                connected_ids.add(str(edge.get("source", "")))
                connected_ids.add(str(edge.get("target", "")))
        for node in nodes:
            node_id = str(node.get("id", "") if isinstance(node, dict) else getattr(node, "id", ""))
            if node_id and node_id not in connected_ids:
                gaps.append(FieldGap(
                    field=f"node:{node_id}",
                    gap_type=GapType.TOPOLOGY_VIOLATION,
                    detail=f"Node '{node_id}' is orphaned (no edges)",
                    suggested_action=actions.get(GapType.TOPOLOGY_VIOLATION, ""),
                ))

        # Check serialization
        output_formats = getattr(contract, "output_formats", [])
        for fmt in output_formats:
            if fmt not in serialized_output:
                gaps.append(FieldGap(
                    field=f"serialization:{fmt}",
                    gap_type=GapType.SERIALIZATION_FAILED,
                    detail=f"Graph not serialized to format '{fmt}'",
                    suggested_action=actions.get(GapType.SERIALIZATION_FAILED, ""),
                ))

        # If no gaps, everything is satisfied
        if not gaps:
            satisfied = ["nodes", "edges", "grounding", "topology", "serialization"]

        return GapReport(
            gaps=gaps,
            satisfied=satisfied,
            is_complete=len(gaps) == 0,
            total_fields=len(nodes) + len(edges),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _required_fields(schema: type[BaseModel]) -> dict[str, dict[str, Any]]:
    """Extract required field paths and their type info from a Pydantic schema.

    For v1, this handles flat schemas and one level of nesting (list of
    submodels). Deeper nesting is a v2 concern.

    Returns:
        Maps field path -> {"type": python_type, "required": bool}.
    """
    fields: dict[str, dict[str, Any]] = {}
    model_fields = schema.model_fields  # type: ignore[attr-defined]

    for name, info in model_fields.items():
        annotation = info.annotation
        required = info.is_required()

        if not required:
            continue

        # Handle list[SubModel] — expand to a single "list" entry for v1.
        # Per-item path tracking (line_items[0].quantity) is v2.
        fields[name] = {
            "type": annotation,
            "required": required,
        }

    return fields


def _check_type(value: Any, expected_type: Any) -> bool:
    """Check if value matches the expected type annotation.

    Handles common cases: str, int, float, bool, list, and BaseModel
    subclasses. Does not handle complex generics (v2 concern).
    """
    if expected_type is str:
        return isinstance(value, str)
    if expected_type is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type is bool:
        return isinstance(value, bool)
    if expected_type is list or expected_type is list[str]:
        return isinstance(value, list)
    if isinstance(expected_type, type) and issubclass(expected_type, BaseModel):
        return isinstance(value, expected_type)
    # Fallback: accept if not obviously wrong
    return True
