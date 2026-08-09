---
id: BLK-038
type: feature
title: "Pane 3 — Document Viewer (PDF/Image + SVG bbox overlay)"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T21:00:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-026]
tags: [frontend, pane-3, document-viewer, pdf, bbox, grounding, ui]
---

## Description

Build Pane 3 — the Document Viewer in the 3-pane workbench. Renders the
input document (PDF or image) with an interactive SVG overlay layer for
bounding box highlighting. This is the pixel-grounding surface that makes
extractions auditable — users can see exactly where each value came from.

Key mechanics:
1. **Document Canvas** — uses `react-pdf` for PDF rendering or custom
   `<canvas>` for images. Normalized coordinates (0-1000 scale) mapped to
   actual canvas pixel dimensions.
2. **SVG Bbox Overlay** — transparent SVG layer on top of the canvas.
   Bounding boxes drawn as highlighted rectangles with high-contrast outline.
3. **Bidirectional Click Linking**:
   - Clicking a field in Pane 2 → Pane 3 scrolls to the correct page,
     draws a glowing/pulsing bbox at the field's grounding coordinates.
   - Clicking a bbox in Pane 3 → Pane 2 scrolls to and highlights the
     corresponding field card.
4. **Active Highlight** — shared `ActiveHighlightContext` between Pane 2
   and Pane 3 manages the currently selected bbox. Brief pulse animation
   (yellow fill, high-contrast outline) on selection.

## Acceptance Criteria

- [ ] PDF rendering via `react-pdf` (multi-page support, page navigation)
- [ ] Image rendering via custom `<canvas>` for PNG/JPG
- [ ] Page navigation toolbar: `<` `>` buttons + "Page X of N" indicator
- [ ] Page navigation jumps to the correct page when a field in Pane 2 is clicked (bidirectional linking uses grounding.page)
- [ ] Independent vertical scrollbar for document content (overflow-y-auto)
- [ ] Horizontal scrollbar for zoomed/oversized documents (overflow-x-auto)
- [ ] Sticky toolbar (page nav + zoom controls stay visible while scrolling)
- [ ] SVG overlay layer on top of document canvas
- [ ] Normalized bbox coordinates (0-1000 scale) mapped to canvas pixels
- [ ] Bounding boxes rendered as highlighted rectangles with outline
- [ ] Clicking a field in Pane 2 → Pane 3 scrolls to page, pulses bbox
- [ ] Clicking a bbox in Pane 3 → Pane 2 scrolls to corresponding field card
- [ ] `ActiveHighlightContext` shared between Pane 2 and Pane 3
- [ ] Pulse animation on bbox selection (yellow fill, high-contrast outline)
- [ ] All bboxes for current extraction displayed as subtle outlines
- [ ] Zoom and pan support for large documents

## Constraints

- `react-pdf` for PDF rendering (or custom canvas if simpler for v1) [SF]
- SVG overlay for bboxes — not canvas drawing (easier to style and animate)
- Normalized coordinates (0-1000) to handle different document resolutions

## Dependencies

- BLK-026 (frontend scaffold — needs ActiveHighlightContext and 3-pane layout)

## Notes

- vision.md §0.2 (Pane 3 — Document Viewer), §7.2 criterion 14
- Bidirectional linking with BLK-033 (Pane 2 — Extracted Data)
- The grounding coordinates come from the backend's `Grounding` type (bbox + page)
