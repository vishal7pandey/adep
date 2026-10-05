---
name: pid-dexpi-digitizer
description: >
  Digitize a P&ID drawing into a DEXPI-shaped graph (equipment nodes, valves, instruments,
  off-page connectors, piping/signal edges) ready for DEXPI 1.3 XML export. NOT for plain
  free-form extraction with no fixed output shape, NOT for design-rule audits.
modality: graph_digitization
visual_cues:
  - P&ID drawing with equipment symbols, piping runs, instrument bubbles, and valve symbols
  - "ISA-5.1 instrument bubbles: a circle with a horizontal line, function code above, loop number below"
  - Pipe line number labels along piping runs (e.g. 6"-HC-1001-A1A)
  - Off-page connectors / flags at drawing edges linking to other sheets
  - Title block in a corner naming the drawing number, title, and revision
document_aliases:
  - P&ID to DEXPI
  - P&ID Digitization
  - P&ID to graph
probe_order:
  - step: 1
    target: Title block
    tool: crop_and_read
    question: >
      Extract drawing metadata for the header: drawing_number, drawing_title, revision,
      project_name, unit_area.
  - step: 2
    target: Equipment and nozzles
    tool: crop_and_read
    question: >
      Identify every piece of equipment as a node with nozzles. For each: id, tag, type
      (Vessel, Column, Pump, Compressor, HeatExchanger, ...), nozzles (id, direction,
      nominal_diameter).
  - step: 3
    target: Valves and in-line components
    tool: crop_and_read
    question: >
      Identify every valve. For each: id, tag, valve_type (Control, Gate, Globe, Check, Ball),
      fail_position (FC, FO, FL), actuator, line_number.
  - step: 4
    target: Instrumentation (ISA-5.1)
    tool: crop_and_read
    question: >
      Identify every instrument bubble and signal line. For each: id, tag (e.g. FT-101),
      function_code, loop_number, location (Field, DCS), signal_to.
  - step: 5
    target: Off-page connectors and piping routes
    tool: crop_and_read
    question: >
      Trace every pipe route and boundary connector. Off-page connectors: id, tag, label,
      direction. Edges: id, from_id, to_id, edge_type, line_number, diameter, piping_class.
invariants:
  - name: nodes_non_empty
    check: non_empty
    fields: [nodes]
  - name: edges_non_empty
    check: non_empty
    fields: [edges]
  - name: all_nodes_have_tag_and_type
    check: all_rows_have
    fields: [nodes]
    require: [tag, type]
  - name: all_edges_have_endpoints
    check: all_rows_have
    fields: [edges]
    require: [from_id, to_id]
---

# P&ID to DEXPI-shaped graph digitization

## Overview

Reconstructs a 2D P&ID drawing into a graph of equipment nodes, valves, instruments, off-page
connectors, and piping/signal edges — the shape a real DEXPI 1.3 / Proteus XML exporter (ADE-14,
not yet built) will serialize. Every node needs a tag and type; every edge needs both endpoints —
a drawing that reconstructs to zero of either was almost certainly surveyed incompletely, not
genuinely empty.

## Output format

Return JSON with `header`, `nodes`, `valves`, `instruments`, `off_page_connectors`, `edges`, and
(once `to_dexpi_xml` is available) `dexpi_xml`.
