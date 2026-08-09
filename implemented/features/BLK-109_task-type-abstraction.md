---
id: BLK-109
type: feature
title: "Task Type Abstraction — generalize Template, ExtractedResult, and Validator"
priority: high
status: done
started: 2026-08-08T13:26:00+05:30
completed: 2026-08-08T13:50:00+05:30
phase: 4
owner: backend
created: 2026-08-08T04:00:00+05:30
estimate: L
depends-on: [BLK-103]
tags: [backend, architecture, abstraction, task-types, graph-extraction]
---

## Description

Generalize the platform's output model beyond flat field extraction.
Introduce a `TaskType` enum and dispatch pattern so the platform can
support graph extraction, classification, and transformation — not
just field extraction.

See vision.md §20 for full design.

## What Changes

### 1. Output Contract Hierarchy

```python
class OutputContract(BaseModel):
    task_type: str
    name: str
    description: str

class FieldExtractionContract(OutputContract):
    task_type: str = "extraction"
    # Pydantic fields by subclass (current Template behavior)

class GraphExtractionContract(OutputContract):
    task_type: str = "graph_extraction"
    node_types: list[NodeTypeSpec]
    edge_types: list[EdgeTypeSpec]
    required_attributes: dict[str, list[str]]
    topology_rules: list[TopologyRule]
    output_formats: list[str]
```

- `Template` becomes an alias for `FieldExtractionContract`
- All existing templates continue to work unchanged

### 2. Result Model Hierarchy

```python
@dataclass
class RunResult:
    is_complete: bool
    status: str
    trace: list[TraceEntry]
    gap_report: GapReport
    token_usage_summary: dict

@dataclass
class FieldExtractionResult(RunResult):
    values: Any
    field_values: dict[str, FieldValue]

@dataclass
class GraphExtractionResult(RunResult):
    graph: dict  # nodes[], edges[]
    node_grounding: dict[str, BBox]
    edge_grounding: dict[str, list[BBox]]
    serialized_output: dict[str, str]
```

- `ExtractedResult` becomes an alias for `FieldExtractionResult`

### 3. Validator Dispatch

Add `task_type` to the validator dispatch:

```python
class TaskValidator:
    def validate(self, result, contract) -> GapReport:
        if contract.task_type == "extraction":
            return self._validate_extraction(result, contract)
        elif contract.task_type == "graph_extraction":
            return self._validate_graph(result, contract)
```

Graph validation checks:
- Node coverage
- Edge connectivity (no orphans)
- Attribute completeness
- Topology rules
- Tag format (ISA-5.1)
- Control loop completeness
- Grounding presence
- Serialization validity

### 4. Agent Definition

Add `task_type` field to `AgentDefinition`:
```python
task_type: str = "extraction"  # default for backward compat
```

### 5. New GapTypes

Add to `GapType` enum:
- `SYMBOL_UNCLASSIFIED`
- `TAG_UNREADABLE`
- `CONNECTION_AMBIGUOUS`
- `TOPOLOGY_VIOLATION`
- `NODE_MISSING`
- `EDGE_MISSING`
- `ATTRIBUTE_MISSING`
- `SERIALIZATION_FAILED`

## Acceptance Criteria

- [x] `OutputContract` base class with `FieldExtractionContract` and `GraphExtractionContract`
- [x] `RunResult` base class with `FieldExtractionResult` and `GraphExtractionResult`
- [x] `Template` alias works — all 12 existing templates pass
- [x] `ExtractedResult` alias works — all existing code unchanged
- [x] Validator dispatches by `task_type`
- [x] `AgentDefinition` has `task_type` field (default: "extraction")
- [x] New `GapType` values added
- [x] All 754 existing tests pass — zero regressions (782 total with 28 new)
- [x] New unit tests for dispatch logic (28 tests in test_task_types.py)

## Constraints

- **Backward compatible** — no existing behavior changes
- All existing templates, skills, and definitions must work unchanged
- The ReAct loop, state model, and guardrails are NOT modified
- This is pure refactoring + new base classes, no new functionality

## Reference

- vision.md §20 — full design document
