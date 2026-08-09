---
id: BLK-060
type: feature
title: "Trace export & audit report — download run trace and result PDF"
priority: low
status: backlog
phase: 4
owner: unassigned
created: 2026-08-08T00:05:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-022, BLK-050]
tags: [backend, frontend, audit, export, compliance, trace, pdf]
---

## Description

Allow users to export a run's trace and extracted data as structured
JSON or as a human-readable PDF audit report. Critical for compliance
and reviewing extraction decisions.

## Motivation

Enterprise users need audit trails. A PDF report with the document,
bboxes, extraction values, and agent trace satisfies regulatory and
QA requirements.

## Export Options

### 1. JSON Export

`GET /api/v1/runs/{id}/export/json`

Returns:
```json
{
  "run_id": "...",
  "definition": {...},
  "skill": {...},
  "template": {...},
  "document": {"pages": 2, "page_paths": [...]},
  "extraction": {...},
  "trace": [...],
  "token_usage": [...},
  "gap_report": {...},
  "status": "complete"
}
```

### 2. PDF Audit Report

`GET /api/v1/runs/{id}/export/pdf`

Generates a multi-page PDF:
- Page 1: cover (run ID, timestamp, definition, result status, token cost)
- Page 2: summary table of extracted fields (name, value, confidence, page)
- Page 3+: each document page with bboxes overlaid and extracted values labeled
- Final pages: trace summary (compacted trace, tool calls, gaps)

### 3. CSV Export

`GET /api/v1/runs/{id}/export/csv`

One row per field:
```
field_name,value,confidence,status,page,bbox_x,bbox_y,bbox_w,bbox_h
vendor_name,ACME Corporation,0.98,extracted,1,120,340,310,60
```

## Frontend Integration

- Pane 2 header: "Export" dropdown with JSON / CSV / PDF options
- Admin panel: export from run row actions

## Acceptance Criteria

- [ ] `GET /api/v1/runs/{id}/export/json` returns full run JSON
- [ ] `GET /api/v1/runs/{id}/export/csv` returns field CSV
- [ ] `GET /api/v1/runs/{id}/export/pdf` returns PDF audit report
- [ ] PDF includes document pages with bbox overlay
- [ ] PDF includes trace summary
- [ ] Export buttons in Pane 2 header and admin runs table
- [ ] Token usage and cost on PDF cover page
- [ ] Unit tests for JSON and CSV export
- [ ] Integration test: complete run → PDF generated with correct field count

## Constraints

- PDF generation uses ReportLab or WeasyPrint. Keep simple in v1 [SF].
- Audit report does not include full raw trace (too long) — use
  `compaction_summary` or top-level trace only

## Dependencies

- BLK-022 (runs API)
- BLK-050 (token usage for cost on PDF cover)
