---
id: BLK-125
type: feature
title: "detect_tables tool — table structure detection with cell-level grounding"
priority: high
status: done
started: 2026-08-08T17:20:00+05:30
completed: 2026-08-08T17:50:00+05:30
phase: 4
owner: backend
created: 2026-08-08T13:50:00+05:30
estimate: L
depends-on: []
tags: [backend, tools, tables, line-items, structure]
---

## Problem

`detect_tables` does not exist. It is referenced as the canonical
example in `comms/README.md` and is needed by several shipped skills:

- `InvoiceSkill` — line items table (`line_items` field, with a
  `line_items_sum_equals_subtotal` invariant)
- `BillOfQuantitiesSkill` — the entire document is a table
- `AdBuySkill` — insertion order line items
- `MetallurgicalAssaySkill` — composition table

Today these skills extract line items by prompting the VLM on the
whole page and hoping the model returns well-formed rows. That is
fragile: rows get merged, columns shift, and the sum invariants fail
for structural reasons rather than perception errors.

## Requirements

### Tool Contract

```python
detect_tables(image, region: BBox | None = None) -> TablesResult
```

Returns:

```python
{
  "tables": [
    {
      "bbox": BBox,
      "confidence": float,
      "n_rows": int,
      "n_cols": int,
      "header_row_index": int | None,
      "cells": [
        {
          "row": int,
          "col": int,
          "row_span": int,
          "col_span": int,
          "bbox": BBox,
          "text": str | None,       # None if not yet OCR'd
          "confidence": float,
        }
      ],
    }
  ]
}
```

### Implementation Strategy

1. **Ruled tables** (visible borders): OpenCV line detection —
   morphological ops to isolate horizontal/vertical lines, find
   intersections, derive the cell grid. Deterministic and cheap.
2. **Unruled tables** (whitespace-aligned): column detection via
   vertical whitespace projection profiles; row detection via
   horizontal projection. Fall back to VLM when the projection is
   ambiguous.
3. **Complex/merged cells**: VLM pass with the detected grid as
   context to resolve spans.

Try 1, then 2, then 3. Report which strategy produced the result so
the trace is auditable.

### Cell Text

`detect_tables` returns cell **geometry** with `text: None`. Text is
filled by a subsequent `ocr` call per cell, or a batched OCR over the
table region. Keep the tools atomic — detection and reading stay
separate, consistent with the existing tool design.

Add a convenience helper `read_table(image, table) -> rows[]` that
composes `detect_tables` + `ocr` per cell and returns row dicts keyed
by header text. This is a composition, not a new primitive.

### Grounding

Every cell must carry a bbox in source-image coordinates so Pane 3
can highlight individual cells. This is what makes line-item
verification auditable.

## Acceptance Criteria

- [x] `detect_tables` registered in the Tool Registry with a ToolSpec
- [x] Ruled-table detection via OpenCV (deterministic, no LLM)
- [x] Unruled-table detection via projection profiles
- [x] VLM fallback for merged/complex cells
- [x] Strategy used is recorded in the result and trace
- [x] Cell-level bboxes in source coordinates
- [x] `row_span` / `col_span` correct for merged cells
- [x] `read_table_cells` composition helper returns header-keyed row dicts
- [ ] Marked `cacheable=True` for BLK-124 (deferred to BLK-124)
- [x] Tests: ruled table, unruled table, merged cells, nested/no table,
      cell bbox accuracy, header detection
- [ ] Integration: `InvoiceSkill` line items via `detect_tables`
      satisfies the `line_items_sum_equals_subtotal` invariant (follow-up)

## Notes

Once this lands, revisit `InvoiceSkill`, `BillOfQuantitiesSkill`,
`AdBuySkill`, and `MetallurgicalAssaySkill` to prefer `detect_tables`
in their `tool_preferences` and probe orders. That skill rewiring can
be a follow-up item.
