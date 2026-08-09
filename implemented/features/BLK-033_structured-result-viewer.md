---
id: BLK-033
type: feature
title: "Pane 2 — Extracted Data (Field Card Grid + editable JSON/Form view)"
priority: medium
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-028]
tags: [frontend, pane-2, extracted-data, field-cards, ui]
---

## Description

Build Pane 2 — the Extracted Data view in the 3-pane workbench.
Toggleable between two modes:

**Mode A: Field Card Grid (default)** — each field from the Pydantic template
gets its own card showing field name, extracted value, confidence badge
(green ≥ 80%, yellow ≥ 50%, red < 50%), and status (Verified/Failed).
Clicking a card fires `setActiveBBox(bbox, page)` to highlight the source
in Pane 3.

**Mode B: Editable JSON/Form View** — standard JSON schema form where fields
can be manually corrected by a human-in-the-loop. Useful for review and
correction of low-confidence extractions.

Every extracted field carries a provenance/grounding object:
```json
{
  "field_name": "subtotal",
  "value": 1450.50,
  "confidence": 0.95,
  "grounding": {"page": 1, "bbox": [120, 450, 310, 480]}
}
```

## Acceptance Criteria

- [ ] Field Card Grid mode: one card per template field
- [ ] Independent vertical scrollbar (overflow-y-auto, does not scroll the page)
- [ ] Sticky header (view toggle + export buttons stay visible while scrolling)
- [ ] Each card: field name, value, confidence badge (green/yellow/red), status
- [ ] Clicking a field card fires `setActiveBBox(bbox, page)` via ActiveHighlightContext
- [ ] Editable JSON/Form view mode: toggleable, human-in-the-loop corrections
- [ ] Toggle between Mode A and Mode B via UI control
- [ ] Table view for list fields (e.g., line_items) in card grid
- [ ] Gap report summary if extraction is partial
- [ ] Export result as JSON/CSV
- [ ] Auto-scroll to field when bbox clicked in Pane 3 (bidirectional linking)

## Dependencies

- BLK-026 (frontend scaffold — needs ActiveHighlightContext)
- BLK-027 (API client — needs run result types)

## Notes

- vision.md §0.2 (Pane 2 — Extracted Data), §7.2 criteria 13-14
- Bidirectional linking with BLK-038 (Pane 3 — Document Viewer)
