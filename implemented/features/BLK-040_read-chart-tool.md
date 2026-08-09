---
id: BLK-040
type: feature
title: "read_chart tool — extract numerical data from charts and infographics"
priority: high
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T22:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-006]
tags: [tools, vlm, chart, infographic, utility, energy]
---

## Description

Implement a `read_chart` tool that extracts underlying numerical data
series from bar charts, line graphs, pie charts, and infographics by
routing cropped pixels directly to the VLM. This bypasses OCR entirely —
the VLM natively interprets the visual geometry of charts to reconstruct
the data.

## Motivation

Utility bills, financial reports, and energy consumption documents
present critical historical metrics solely as charts/graphs. Text-only
extraction pipelines cannot parse these. The ADE industry mapping
identifies this as a key differentiator for the Utility and Energy
sectors (§Sectors 5, 10-11).

Benchmarks: ChartQA, OmniMapBench show VLMs excel at native chart
interpretation without text extraction.

## Acceptance Criteria

- [ ] `read_chart` ToolSpec registered in ToolRegistry
- [ ] Input: image handle (cropped chart region), optional chart_type hint
- [ ] Output: structured data series `{"series": [{"label": "...", "values": [...]}], "x_axis": [...], "y_axis": {...}}`
- [ ] Grounding: bbox of the chart region
- [ ] VLM provider dispatch (uses Azure GPT-5.4 vision)
- [ ] Handles bar, line, pie, and stacked area charts
- [ ] Fallback: if VLM confidence < threshold, return partial data with gap
- [ ] Unit tests with sample chart images
- [ ] Integration test: UtilityBill skill extracts 12-month consumption from bar chart

## Constraints

- VLM-only tool — no OCR fallback (charts are visual, not textual) [SF]
- Must return structured data, not free-text descriptions
- Grounding is non-negotiable [§2.5]

## Dependencies

- BLK-006 (Azure GPT-5.4 VLM provider)

## Notes

- ADE industry mapping: §Sectors 10-11 (Utility bills, energy consumption charts)
- vision.md §2.3 (Verification tools category)
- ChartQA benchmark for evaluation
