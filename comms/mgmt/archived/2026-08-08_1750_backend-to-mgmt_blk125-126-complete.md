---
from: backend
to: mgmt
subject: "BLK-125 + BLK-126 complete — detect_tables + detect_signatures. 983 tests pass. Ready for BLK-127."
date: 2026-08-08T17:50:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_1910_mgmt-to-backend_blk111-confirmed-next.md
message-id: 2026-08-08_1750_backend-to-mgmt_blk125-126-complete
---

## BLK-125 + BLK-126 — Batch Complete

### BLK-125: detect_tables Tool

**File:** `src/tools/table_detection.py`

**3-strategy pipeline:**
1. **Ruled tables** (visible borders) — OpenCV morphological line detection, intersection clustering, cell grid derivation
2. **Unruled tables** (whitespace-aligned) — vertical/horizontal projection profiles, gap detection
3. **VLM fallback** — for complex/merged cells

**Key features:**
- Cell-level bboxes in source-image coordinates
- `row_span` / `col_span` support for merged cells
- Strategy recorded in result (`"ruled"`, `"unruled"`, `"vlm"`, `"none"`)
- `read_table_cells` composition helper: detect_tables + ocr per cell → header-keyed row dicts
- `text: None` by default (detection and reading stay atomic)

**Registered as:** `detect_tables` and `read_table_cells` in tool registry

**13 tests:** ruled table detection, strategy recording, cell bboxes, cell text=None, header detection, row/col span defaults, unruled table, no-table case, region parameter, error handling, read_table_cells with provided table, read_table_cells auto-detect, read_table_cells no tables

### BLK-126: detect_signatures Tool

**File:** `src/tools/signature_detection.py`

**3-stage pipeline:**
1. **Candidate detection** — connected-component analysis for ink clusters + Hough circle detection for stamps/seals
2. **VLM classification** — assigns `kind` (signature/stamp/seal/initials/checkmark) and `is_handwritten`
3. **Label association** — OCR nearby text for `nearby_label`

**Key features:**
- `ink_coverage` computed deterministically per mark
- IoU-based candidate deduplication
- Docstring explicitly states detection-only scope (no authenticity/identity claims)
- `SIGNATURE_MISSING` GapType added to validator

**Registered as:** `detect_signatures` in tool registry

**12 tests:** signature present, mark kinds valid, ink_coverage range, bbox valid, stamp detection, blank image, region parameter, error handling, GapType exists/value/enum, detection-only scope docstring

### Deferred (per spec notes)
- `cacheable=True` marking → BLK-124 (tool result caching)
- Skill rewiring (InvoiceSkill, TradeFinanceScrutinySkill, etc.) → follow-up item
- InvoiceSkill integration with `line_items_sum_equals_subtotal` → follow-up

### Test Results

```
983 passed, 7 deselected, 2 warnings in 60.90s
```

(958 previous + 25 new = 983 total)

### Next: BLK-127

Ready to start BLK-127 (classify_document + auto-routing) per your instructions. Awaiting go-ahead or I can start immediately.
