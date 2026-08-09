---
from: backend
to: mgmt
subject: "BLK-159 complete — store merges prebuilt content. 1126 tests. BLK-160 no backend action."
date: 2026-08-08T13:15:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_2240_mgmt-to-backend_blk128-confirmed-urgent-fixes.md
message-id: 2026-08-08_1315_backend-to-mgmt_blk159-complete
---

## BLK-159 — Store Should Include Prebuilt Content — Complete

### What was done

**Store merge logic** (`src/definitions/store.py`):
- `list_definitions()`, `list_skills()`, `list_templates()` now merge prebuilt content with on-disk content. Disk takes precedence (user edits win).
- `get_definition()`, `get_skill()`, `get_template()` check disk first, fall back to prebuilt.
- Added `_merge_with_prebuilt()` method and `_get_prebuilt()` helper.

**Removed dead code:**
- `seed_store()` from `src/definitions/prebuilt.py`
- `register_prebuilt_definitions()` from `src/definitions/prebuilt.py`
- `scripts/seed.py` deleted

**Kept as data (read by store):**
- `PREBUILT_DEFINITIONS` (18 definitions)
- `PREBUILT_SKILLS` (19 skills)
- `PREBUILT_TEMPLATES` (19 templates)

**Tests:**
- Created `src/tests/test_prebuilt_merge.py` — 21 dedicated tests for BLK-159
- Updated 8 existing tests across 6 files to account for prebuilt content in list/search results
- Fixed `test_reviewer_fixes.py` auth default test (was broken by local `.env` override, not a regression)

### Test Results

```
1126 passed, 19 deselected (integration), 0 failures
```

### BLK-160 — HITL Gate Stopgap

No backend action needed for stopgap. Full fix (SSE `gate_triggered`, `/approve`, `/reject` endpoints) blocked on BLK-129 (async run execution). Ready to submit BLK-129 contract proposal when directed.

### Spec

Moved to `implemented/features/BLK-159_store-should-include-prebuilt-content.md`.
