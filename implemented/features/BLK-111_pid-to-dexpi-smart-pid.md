---
id: BLK-111
type: feature
title: "P&ID → DEXPI/Smart P&ID — skill, contract, agent definition, sample data"
priority: high
status: done
started: 2026-08-08T16:50:00+05:30
completed: 2026-08-08T17:15:00+05:30
phase: 4
owner: backend
created: 2026-08-08T04:00:00+05:30
estimate: M
depends-on: [BLK-109, BLK-110]
tags: [backend, pid, dexpi, smart-pid, graph-extraction, engineering]
---

## Description

Implement the first graph extraction use case: converting P&ID
(Piping and Instrumentation Diagram) drawings to DEXPI XML and
Smart P&ID JSON formats.

See vision.md §20.7 for full design.

## Deliverables

### 1. PnIDContract (GraphExtractionContract)

**File:** `src/templates/pid.py`

```python
class PnIDContract(GraphExtractionContract):
    name = "P&ID to DEXPI/Smart P&ID"
    node_types = [
        NodeTypeSpec("equipment", ["vessel", "pump", "heat_exchanger",
                                   "tank", "compressor"]),
        NodeTypeSpec("valve", ["manual", "control", "check", "relief"]),
        NodeTypeSpec("instrument", ["sensor", "controller", "indicator"]),
        NodeTypeSpec("pipe", []),
        NodeTypeSpec("fitting", ["reducer", "elbow", "tee"]),
    ]
    edge_types = [
        EdgeTypeSpec("connected_to", "any", "any"),
        EdgeTypeSpec("branches_from", "pipe", "pipe"),
        EdgeTypeSpec("measures", "instrument", "equipment|pipe"),
        EdgeTypeSpec("controls", "instrument", "valve"),
    ]
    topology_rules = [
        "every valve connected to at least one pipe",
        "every instrument tag follows ISA-5.1 (XX-NNN)",
        "control loops complete: sensor → controller → final_element",
        "no orphan pipes (both ends connected or explicitly capped)",
    ]
    output_formats = ["dexpi_xml", "smart_pid_json", "graphml"]
```

### 2. PnIDSkill

**File:** `src/skills/pid.py`

```python
PnIDSkill = Skill(
    name="pid_to_dexpi",
    system_prompt=PnID_SYSTEM_PROMPT,
    tool_preferences={
        "symbol_detection": "detect_symbols",
        "tag_reading": "ocr + vlm",
        "connection_tracing": "trace_line",
    },
    probe_order=[
        ("title_block", "Read drawing title, revision, scale"),
        ("legend", "Identify symbol library / legend"),
        ("main_diagram", "Detect all symbols in the main drawing area"),
        ("tags", "Read instrument tags for each detected symbol"),
        ("connections", "Trace pipe lines between symbols"),
        ("topology", "Build and validate the process graph"),
        ("serialize", "Convert to target output format"),
    ],
    invariants=[
        _every_valve_connected,
        _isa_51_tag_format,
        _control_loop_completeness,
        _no_orphan_pipes,
    ],
    failure_actions={
        GapType.SYMBOL_UNCLASSIFIED: "crop region, vlm with symbol library",
        GapType.TAG_UNREADABLE: "crop tag area, deskew, ocr",
        GapType.CONNECTION_AMBIGUOUS: "trace_line from both endpoints",
        GapType.TOPOLOGY_VIOLATION: "re-examine region, check for missed symbol",
    },
    known_failures=(
        "Hand-drawn P&IDs may need deskew before symbol detection. "
        "Older scans may have faded lines — use VLM for connection "
        "detection when line tracing fails. "
        "Non-ISA tag formats (e.g., KKS) require custom parsing."
    ),
)
```

### 3. Prebuilt Agent Definition

**File:** Add to `src/definitions/prebuilt.py`

```python
{
    "id": "def-pnid-to-dexpi",
    "name": "P&ID to DEXPI Converter",
    "version": "1.0.0",
    "task_type": "graph_extraction",
    "skill_id": "pid_to_dexpi",
    "template_id": "pid_to_dexpi",
    "tool_names": [
        "detect_layout", "detect_symbols", "classify_symbol",
        "ocr", "vlm", "read_tag", "trace_line", "detect_connections",
        "build_graph", "validate_topology", "serialize_graph",
        "crop", "deskew"
    ],
    "agent_config": {
        "max_cycles_per_field": 10,
        "max_cycles_per_document": 50,
        "confidence_threshold": 0.75,
    },
}
```

### 4. Sample P&ID Data

Download sample P&ID diagrams to `sample-data/pid/`:
- Search for free P&ID sample drawings (PDF/PNG)
- Need 2-3 samples with varying complexity
- Include at least one with ISA-5.1 instrument tags
- Include one hand-drawn or scanned sample for degraded testing

### 5. Tests

- Structure test: PnIDContract has all required node/edge types
- Invariant tests: each topology rule passes/fails correctly
- E2E smoke test: detect_symbols → read_tag → build_graph →
  serialize_graph → validate DEXPI XML parses

## Acceptance Criteria

- [x] `PnIDContract` defined with all node/edge types and topology rules
- [x] `PnIDSkill` defined with probe order, invariants, failure actions
- [x] `def-pnid-to-dexpi` prebuilt definition registered
- [ ] 2-3 sample P&ID diagrams in `sample-data/pid/` (deferred — requires sourcing real samples)
- [x] Invariant tests pass (4 topology rules × pass/fail)
- [x] E2E test produces valid DEXPI XML from a sample P&ID
- [x] E2E test produces valid GraphML from a sample P&ID
- [x] No regression in existing tests

## Notes

- DEXPI data model: https://dexpi.org/data-model/
- ISA-5.1 instrument tag format: function letters + number
  (e.g., FT = Flow Transmitter, PIC = Pressure Indicator Controller)
- Smart P&ID is Intergraph's proprietary format — we produce a
  JSON representation that can be imported; full Smart P&ID XML
  schema may require licensing
- Start with DEXPI XML + GraphML as output formats; Smart P&ID JSON
  can follow once the graph extraction pipeline is proven
