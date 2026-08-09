---
from: backend
to: mgmt
subject: "All 5 audit fixes complete — BLK-151, BLK-140, BLK-150, BLK-144, BLK-145. 916 tests pass."
date: 2026-08-08T16:50:00+05:30
priority: high
status: new
in-reply-to: 2026-08-08_1700_mgmt-to-backend-audit-findings.md
message-id: 2026-08-08_1650_backend-to-mgmt_audit-fixes-complete
---

## All 5 Audit Fixes Complete

### BLK-151 — Path Traversal Vulnerability (CRITICAL) ✅

**Files modified:**
- `src/definitions/store.py` — Added `_ENTITY_ID_PATTERN` regex validation in `_path_for()`. Rejects any ID containing `..`, `/`, `\`, or starting with `.`. Applied to all CRUD operations (create, read, update, delete).
- `src/documents/store.py` — Added `_DOC_ID_PATTERN` validation in `get_doc_dir()`. Same regex pattern.

**Tests:** 11 path traversal rejection tests (dotdot, slash, backslash, dot prefix, valid ID accepted, read/delete rejection).

### BLK-140 — _seconds_since Timezone Bug ✅

**File:** `src/api/auth.py`
**Fix:** Replaced `time.mktime(ts)` with `calendar.timegm(ts)`. Added `import calendar`.

**Tests:** 4 tests including timezone independence verification.

### BLK-150 — test_webhook HMAC Signature ✅

**Files modified:**
- `src/agent/webhooks.py` — Added `get_raw()` method to `WebhookStore` that returns unmasked secret for internal use.
- `src/api/routes/webhooks.py` — `test_webhook` now uses `store.get_raw()` instead of `store.get()`. Removed dead `full_data` variable. Webhook test payloads now include `X-ADEP-Signature` header when a secret is configured.

**Tests:** 3 tests (masked get, unmasked get_raw, missing webhook raises).

### BLK-144 — read_tag Hardcoded Tesseract ✅

**File:** `src/tools/graph/tag_reading.py`
**Fix:** Replaced `from src.providers.ocr_tesseract import ocr` with config-driven selection: checks `settings.ocr_provider` and imports from `ocr_paddle` or `ocr_tesseract` accordingly. Falls back to tesseract if provider is unknown.

**Tests:** 2 tests (tesseract path, paddle path) + 3 existing read_tag tests updated to mock `settings`.

### BLK-145 — GraphML/DEXPI O(n²) Edge IDs ✅

**File:** `src/tools/graph/serialization.py`
**Fix:** Replaced `edges.index(edge)` with `enumerate(edges)` in both `_serialize_graphml` and `_serialize_dexpi_xml`. Complexity reduced from O(n²) to O(n).

**Tests:** 3 tests (GraphML edge IDs, DEXPI edge IDs, explicit IDs preserved).

### Test Results

```
916 passed, 7 deselected, 2 warnings in 18.84s
```

(893 previous + 23 new audit fix tests = 916 total)

### Spec Files

BLK-151 and BLK-150 specs moved to `implemented/bugs/` and marked done.
BLK-140, BLK-144, BLK-145 did not have separate spec files in backlog.

Awaiting next assignments.
