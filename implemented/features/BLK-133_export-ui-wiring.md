---
id: BLK-133
type: feature
title: "Export UI — wire JSON/CSV endpoints, add copy-to-clipboard and download"
priority: medium
status: done
completed: 2026-08-08T10:15:00+05:30
phase: 4
owner: frontend
created: 2026-08-08T13:50:00+05:30
estimate: S
depends-on: []
tags: [frontend, export, ux, quick-win]
---

## Problem

Backend shipped export endpoints in BLK-060:

- `GET /api/v1/runs/{id}/export/json` — full run JSON
- `GET /api/v1/runs/{id}/export/csv` — field CSV

These are not wired into the UI. The user can extract data but cannot
easily get it out — which is the entire point of the product.

## Requirements

### 1. Export Menu in Pane 2

An Export dropdown in the Pane 2 header:

```
  Export ▾
    Download JSON        (full run: fields, trace, tokens)
    Download CSV         (fields only, spreadsheet-ready)
    Copy JSON            (to clipboard)
    Copy field values    (tab-separated, paste into Excel)
```

Filename convention: `{document_name}_{run_id}_{yyyy-mm-dd}.{ext}`

### 2. Copy-to-Clipboard Affordances

- Per-field copy button on hover over each field card
- "Copy all field values" as tab-separated text — pastes cleanly into
  a spreadsheet row
- Toast confirmation on copy ("Copied invoice_number")

### 3. Export Scope Awareness

Be explicit about what is being exported when a run is incomplete:

- Complete run: export normally
- Partial run: warn that the export contains partial results and
  include the gap report in the JSON
- Failed run: still allow export — partial data has value

### 4. Graph Export (forward-looking)

When BLK-112 lands and graph extraction results exist, the same menu
should offer DEXPI XML, Smart P&ID JSON, and GraphML. Structure the
export menu so adding formats is trivial rather than a rewrite.

## Acceptance Criteria

- [ ] Export dropdown in Pane 2 header
- [ ] Download JSON wired to the export endpoint
- [ ] Download CSV wired to the export endpoint
- [ ] Copy JSON to clipboard
- [ ] Copy all field values as tab-separated text
- [ ] Per-field copy button on hover
- [ ] Toast confirmation on copy actions
- [ ] Filename convention applied
- [ ] Partial-run exports carry an explicit warning + gap report
- [ ] Failed runs are still exportable
- [ ] Export menu structured for easy format addition
- [ ] Error handling if an export endpoint fails

## Notes

Smallest-effort, highest-immediate-utility item in the frontend
queue. The endpoints already exist and are tested — this is pure
wiring.
