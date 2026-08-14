---
id: BLK-250
type: bug
title: "Pane3 pagination and bbox overlays are driven by field heatmap data, so multi-page documents collapse and overlays misalign"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T12:50:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-220]
tags: [frontend, document-viewer, pagination, bbox, overlay, multi-page]
---

## Description

`frontend/components/workbench/Pane3DocumentViewer.tsx` computes pagination from extraction-field heatmap data, not from the document metadata:

- ~line 35: `const totalPages = Math.max(1, ...heatmapFields.map(f => f.page || 1))`.
- `heatmapFields` is built (in Pane2 ~lines 114-122) from fields that **have a bbox**. A 5-page document whose extracted fields all live on page 1 renders "Page 1 of 1" and disables `nextPage` — the user can never reach pages 2-5.
- The SVG overlay draws bboxes on a fixed `750×950` box while the `<img>` uses `object-contain` letterboxing at the real aspect ratio (lines ~159-165, ~204-208). When a page's aspect ratio differs from 10:9, the heatmap and active-field highlights do not align with the text they annotate — breaking the "show source" central UX.

## Problem Statement

The document viewer's entire purpose is per-page, per-field source verification. With data-dependent pagination and misaligned overlays it silently under-delivers:

- Multi-page source verification is impossible when all fields happen to be on page 1 (very common for invoices/statements).
- Bounding-box highlighters mislead the user about which text a field was grounded in, eroding trust in grounding evidence.

## Acceptance Criteria

- [ ] `totalPages` comes from the run's real document page count (e.g. `DocumentMetadata.total_pages` / page list), not derived from field bboxes
- [ ] Page navigation works across all pages even when no field has a bbox on a given page
- [ ] Overlay coordinates are transformed with the same aspect-ratio/scale math as the rendered `<img>` (draw on the same coordinate space or apply matching letterbox offsets)
- [ ] Tests: a 5-page doc with fields only on page 1 renders 5 pages; overlay alignment test with a non-10:9 page
- [ ] Empty-state on pages with no fields remains clean

## Constraints

- Do not break the existing image-rendering path or the heatmap layer
- Coordinate with BLK-220 (multi-page state from backend) and BLK-115 (heatmap overlay contract)

## Dependencies

- `frontend/components/workbench/Pane3DocumentViewer.tsx`
- `frontend/components/workbench/Pane2ExtractedData.tsx` (heatmapFields)
- Document metadata contract (BLK-185, BLK-220)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:50 (mgmt)**: Filed after reading Pane3 pagination and overlay geometry.
