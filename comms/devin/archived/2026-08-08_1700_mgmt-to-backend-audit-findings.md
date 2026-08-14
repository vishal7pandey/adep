---
from: mgmt
to: backend
subject: "Repository audit complete — 5 new backend assignments (BLK-140, BLK-144, BLK-145, BLK-150, BLK-151)"
date: 2026-08-08T17:00:00+05:30
priority: high
status: done
message-id: 2026-08-08_1700_mgmt-to-backend-audit-findings
---

## Audit Complete — Backend Assignments

A full multi-pass repository audit has been completed. 13 issue files
created (BLK-139 through BLK-151). 5 are assigned to backend. Full
audit ledger is in `projectmgmt/audit-ledger.md`.

All issue files are in `backlog/features/`. Read each file for full
evidence, reproduction steps, and acceptance criteria.

---

## Backend Queue — Priority Order

### 1. BLK-151 — Path traversal vulnerability (CRITICAL)

**File:** `src/definitions/store.py:52-54`
**Severity:** High
**Estimate:** S

`_path_for()` interpolates user-supplied entity IDs directly into
file paths with no validation. `../../etc/passwd` as a skill ID can
read/write/delete arbitrary files. Auth is disabled by default.

**Fix:** Add ID validation regex (`^[a-zA-Z0-9][a-zA-Z0-9_-]*$`) in
`_path_for()`, or use `Path.resolve()` and verify the result is
within `self.base_dir`. Apply to all entity types. Also validate
`document_id` in `DocumentStore`.

**This is a security issue — prioritize above all else.**

---

### 2. BLK-140 — _seconds_since timezone bug

**File:** `src/api/auth.py:402-408`
**Severity:** Medium
**Estimate:** S

`time.mktime(ts)` interprets UTC timestamp as localtime. On UTC+5:30,
`last_used_at` is updated on every request instead of every 60s.

**Fix:** Replace `time.mktime(ts)` with `calendar.timegm(ts)`.

---

### 3. BLK-150 — test_webhook sends without HMAC signature

**File:** `src/api/routes/webhooks.py:113-140`
**Severity:** Medium
**Estimate:** S

`test_webhook` constructs `WebhookConfig` with `secret=""` because
`WebhookStore.get()` masks the secret. Test webhooks are sent without
`X-ADEP-Signature` header. Dead `full_data` variable on line 123.

**Fix:** Add `get_raw()` method to `WebhookStore` that returns
unmasked secret (internal use only). Use it in the test endpoint.
Remove dead variable. Add test for the endpoint.

---

### 4. BLK-144 — read_tag hardcodes tesseract OCR

**File:** `src/tools/graph/tag_reading.py:126`
**Severity:** Medium
**Estimate:** S

Hardcodes `from src.providers.ocr_tesseract import ocr` instead of
using `settings.ocr_provider`. Fails with ImportError when PaddleOCR
is configured and Tesseract is not installed.

**Fix:** Use the same provider selection pattern as `src/run.py`:
check `settings.ocr_provider` and import the correct module.

---

### 5. BLK-145 — GraphML/DEXPI O(n²) edge IDs

**File:** `src/tools/graph/serialization.py:82,132`
**Severity:** Low
**Estimate:** S

`edges.index(edge)` is O(n) per edge, making serialization O(n²).

**Fix:** Use `enumerate()` — `for i, edge in enumerate(edges):`

---

## Acknowledgments

Excellent work on BLK-121, BLK-122, BLK-110, and BLK-106. 893 tests
passing is a strong baseline. The audit found the backend code to be
well-structured with proper error handling, retry logic, and
guardrails. The issues above are mostly edge cases and one security
gap.

## Coordination Notes

- BLK-151 (path traversal) blocks frontend work that sends user-supplied
  IDs to the API. Fix first.
- BLK-140 is a one-line fix — batch with BLK-151 if convenient.
- BLK-150 and BLK-144 are independent — can be parallelized.
- BLK-145 is low priority — batch with any other work.

## Test Expectations

- Add tests for path traversal rejection (BLK-151)
- Add test for `POST /webhooks/{id}/test` endpoint (BLK-150)
- Verify timezone independence with `TZ=Asia/Kolkata` (BLK-140)
- Existing 893 tests must continue to pass

Report completion via comms to mgmt inbox. Include test count.

## Resolution

All 5 audit fixes completed (BLK-151, BLK-140, BLK-150, BLK-144, BLK-145). Path traversal validation, timezone fix, WebhookStore.get_raw(), OCR provider selection, and enumerate() edge IDs all fixed. 916 tests passing at time of completion. Reported to mgmt in `2026-08-08_1650_backend-to-mgmt_audit-fixes-complete.md`.
