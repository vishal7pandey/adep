---
id: BLK-110
type: feature
title: "Graph extraction tools — symbol detection, connection tracing, graph building, serialization"
priority: high
status: done
started: 2026-08-08T15:15:00+05:30
completed: 2026-08-08T15:45:00+05:30
phase: 4
owner: backend
created: 2026-08-08T04:00:00+05:30
estimate: L
depends-on: [BLK-109]
tags: [backend, tools, graph-extraction, pid, dexpi, symbol-detection]
---

## Description

Implement the tool layer for graph extraction. These tools are
**additive** — they don't replace existing tools. The agent can use
both extraction tools (ocr, vlm, crop) and graph tools in the same
run.

See vision.md §20.6 for full tool table.

## Tools to Implement

### Symbol Detection

#### `detect_symbols(image, symbol_library?) -> symbols[]`
- Input: image, optional symbol library/config
- Output: list of `{bbox, class, confidence}`
- Implementation: Use VLM (GPT-5.4 vision) to detect and classify
  engineering symbols. Can use a reference symbol library for
  few-shot prompting.
- Fallback: If VLM confidence is low, crop region and retry with
  higher resolution.

#### `classify_symbol(image, bbox) -> {class, confidence}`
- Input: image, bounding box
- Output: symbol class + confidence
- Implementation: Crop the bbox, send to VLM with a symbol
  classification prompt.

### Connection Detection

#### `detect_connections(image, symbols[]) -> connections[]`
- Input: image, list of detected symbols
- Output: list of `{from_id, to_id, path_bbox[], type, confidence}`
- Implementation: Use VLM to identify pipe lines connecting symbols.
  Can use line detection (OpenCV Hough) as a preprocessing step.

#### `trace_line(image, start_point, direction?) -> path`
- Input: image, start point (bbox or coordinate), optional direction
- Output: `{bboxes[], end_point, connected_to_id?, confidence}`
- Implementation: Follow a pipe line from a starting point through
  the diagram. Use line tracing (OpenCV) + VLM for ambiguous
  intersections.

### Tag Reading

#### `read_tag(image, bbox) -> {tag, parsed_components, confidence}`
- Input: image, bounding box of tag area
- Output: tag string + parsed components (per ISA-5.1) + confidence
- Implementation: Crop tag area, OCR, parse ISA-5.1 format
  (e.g., "FT-101" → {function: "FT", number: "101"})
- ISA-5.1 parsing is deterministic code, not LLM.

### Graph Building

#### `build_graph(symbols[], connections[]) -> graph`
- Input: detected symbols + connections
- Output: `{nodes[], edges[]}` graph structure
- Implementation: Pure deterministic code. Map symbols to nodes,
  connections to edges. No LLM.

#### `validate_topology(graph, rules) -> {violations[], ok}`
- Input: graph + topology rules from contract
- Output: list of violations + overall ok flag
- Implementation: Pure deterministic code. Check:
  - Every valve connected to at least one pipe
  - Every instrument tag follows ISA-5.1
  - Control loops complete (sensor → controller → final element)
  - No orphan pipes

### Serialization

#### `serialize_graph(graph, format) -> {format, content}`
- Input: graph + target format name
- Output: serialized string in target format
- Formats to implement:
  - `dexpi_xml` — DEXPI XML format (ISO 15926-based)
  - `smart_pid_json` — Smart P&ID JSON representation
  - `graphml` — GraphML (universal graph exchange format)
  - `json` — plain JSON (debugging/inspection)
- Implementation: Deterministic code, no LLM. Each format has a
  serializer function.

## File Structure

```
src/tools/
    graph/
        __init__.py
        symbol_detection.py    # detect_symbols, classify_symbol
        connection.py          # detect_connections, trace_line
        tag_reading.py         # read_tag + ISA-5.1 parser
        graph_building.py      # build_graph, validate_topology
        serialization/
            __init__.py
            dexpi.py           # DEXPI XML serializer
            smart_pid.py       # Smart P&ID JSON serializer
            graphml.py         # GraphML serializer
            base.py            # Serializer interface
```

## Acceptance Criteria

- [x] All 8 tools implemented with ToolSpec schemas
- [x] Tools registered in Tool Registry
- [x] `detect_symbols` works with VLM on sample P&ID images (mocked)
- [x] `read_tag` parses ISA-5.1 tags correctly (deterministic)
- [x] `build_graph` produces valid graph from symbols + connections
- [x] `validate_topology` catches all 4 topology rule violations
- [x] `serialize_graph` produces valid DEXPI XML
- [x] `serialize_graph` produces valid GraphML
- [x] `serialize_graph` produces valid JSON
- [x] Unit tests for each tool (mocked providers)
- [x] Integration test: detect_symbols → read_tag → detect_connections
      → build_graph → validate_topology → serialize_graph

## Notes

- DEXPI format spec: https://dexpi.org/ — use the DEXPI data model
  as reference for the XML serializer
- ISA-5.1 tag format: `[function_letter(s)]-[number]` e.g. "FT-101",
  "PIC-202", "LV-303"
- Symbol detection will primarily use VLM (GPT-5.4 vision) since
  engineering symbols vary widely across drawing standards
- Line tracing can use OpenCV HoughLinesP as a preprocessing step
  before VLM confirmation
