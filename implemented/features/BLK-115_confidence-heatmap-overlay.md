---
id: BLK-115
type: feature
title: "Confidence heatmap overlay in document viewer"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: M
depends-on: []
tags: [frontend, ux, confidence, heatmap, document-viewer, pane3]
---

## Description

Add a "Confidence Overlay" toggle in the Pane 3 toolbar that renders
semi-transparent colored rectangles over every extracted field's
bounding box.

## Requirements

- Toggle button in Pane 3 toolbar
- Color-coded: Green (>0.9), Yellow (0.7-0.9), Red (<0.7)
- Opacity proportional to confidence (low confidence = more opaque)
- Click any overlay rectangle → selects that field in Pane 2 and
  scrolls to its card
- Works with existing bbox data from `ExtractedField[]`

## Acceptance Criteria

- [ ] Toggle button in Pane 3 toolbar
- [ ] All field bboxes rendered with correct color coding
- [ ] Click overlay → selects field in Pane 2
- [ ] Performance: no lag on documents with 50+ fields
- [ ] No backend dependency

## Source

Frontend proposal #3 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`
