---
from: backend
to: mgmt
subject: "BLK-111 complete — P&ID to DEXPI skill + contract. 958 tests pass. Proposing next assignment."
date: 2026-08-08T17:20:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_1730_mgmt-to-backend-audit-confirmed-next-assignments.md
message-id: 2026-08-08_1720_backend-to-mgmt_blk111-complete
---

## BLK-111 — P&ID to DEXPI/Smart P&ID Complete

### What Was Built

**1. PnIDContract** (`src/templates/pid_diagram.py`)
- Extends `GraphExtractionContract` (BLK-109)
- 5 node types: equipment, valve, instrument, pipe, fitting (with subtypes)
- 4 edge types: connected_to, branches_from, measures, controls
- 4 topology rules: valve-pipe connectivity, ISA-5.1 tag format, control loop completeness, no orphan pipes
- 3 output formats: dexpi_xml, smart_pid_json, graphml

**2. PnIDSkill** (`src/skills/pid_diagram.py`)
- 7-step probe order: title_block → legend → main_diagram → tags → connections → topology → serialize
- 4 topology invariants with ISA-5.1-aware sensor detection (`_is_sensor_tag` helper)
- 14 failure actions covering all graph-specific GapTypes
- Tool preferences: detect_symbols, ocr+vlm, trace_line
- Confidence override: graph @ 0.75

**3. Prebuilt Definition** (`def-pnid-to-dexpi`)
- `task_type: "graph_extraction"`
- 13 tools: detect_layout, detect_symbols, classify_symbol, ocr, vlm, read_tag, trace_line, detect_connections, build_graph, validate_topology, serialize_graph, crop, deskew
- max_cycles_per_document: 50, confidence_threshold: 0.75

**4. Registration**
- Skill + template registered in `run_engine.py` (19 skills, 19 templates)
- Prebuilt definition added to `prebuilt.py` (18 definitions)
- All existing test counts updated

### Files Created
- `src/templates/pid_diagram.py`
- `src/skills/pid_diagram.py`
- `src/tests/test_pid_skill.py` — 42 tests

### Files Modified
- `src/api/run_engine.py` — Registered PnIDSkill + PnIDContract
- `src/definitions/prebuilt.py` — Added skill, template, prebuilt definition
- `src/tests/test_prebuilt_catalogue.py` — Updated counts (17→18 definitions)
- `src/tests/test_e2e.py` — Updated counts (18→19 skills/templates, 17→18 defs)
- `src/tests/test_stabilization.py` — Updated counts
- `src/tests/test_new_doc_types.py` — Updated definition count

### Deferred
- Sample P&ID diagrams in `sample-data/pid/` — requires sourcing real-world P&ID drawings

### Test Results

```
958 passed, 7 deselected, 2 warnings in 19.65s
```

(916 previous + 42 new = 958 total)

### Proposed Next Assignment

From the remaining backlog, I'd recommend **BLK-124 (Tool Result Caching)** next:
- It's an M-sized item that directly improves performance
- Builds on the tool registry infrastructure we've been working with
- Benefits all document types including the new P&ID pipeline (graph tools are expensive)

Alternatively, **BLK-125 (Detect Tables Tool)** or **BLK-127 (Classify Document Routing)** would be good picks if you prefer feature breadth over performance.

Awaiting your decision.
