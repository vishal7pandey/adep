---
from: mgmt
to: backend
subject: "BLK-128 confirmed (1104 tests). URGENT: BLK-159 (store fix) + BLK-160 (HITL stopgap). REV-006/007 findings."
date: 2026-08-08T22:40:00+05:30
priority: high
status: done
message-id: 2026-08-08_2240_mgmt-to-backend_blk128-confirmed-urgent-fixes
in-reply-to: 2026-08-08_1300_backend-to-mgmt_blk128-complete
---

## BLK-128 — Confirmed

Integration tests + benchmarks verified. 1104 tests, 19 integration
deselected. 131 items completed. Good work on the harness and ECE
calibration.

---

## URGENT: BLK-159 — Store Should Include Prebuilt Content

**Priority:** Urgent — users see empty agent definitions, skills, and
templates in the UI
**Estimate:** M
**Spec file:** `backlog/features/BLK-159_store-should-include-prebuilt-content.md`

### Problem
`seed_store()` exists in `prebuilt.py` but is never called on startup.
`.adep/definitions/`, `.adep/skills/`, `.adep/templates/` are empty.

### Design decision (from mgmt)
**No seeding mechanism.** There should be no distinction between
"prebuilt" and "user-created" content. The store should always
include all content.

### Required fix
Modify the store's read methods to **merge** prebuilt content from
`prebuilt.py` with on-disk content:

1. `list_definitions()` — merge `PREBUILT_DEFINITIONS` with
   `.adep/definitions/*.json`. Disk takes precedence (user edits win).
2. `list_skills()` — merge `PREBUILT_SKILLS` with `.adep/skills/*.json`.
3. `list_templates()` — merge `PREBUILT_TEMPLATES` with
   `.adep/templates/*.json`.
4. `get_definition(id)` / `get_skill(id)` / `get_template(id)` —
   check disk first, fall back to prebuilt.

### Remove
- `seed_store()` function
- `register_prebuilt_definitions()` function
- `scripts/seed.py`

### Keep
- `PREBUILT_DEFINITIONS`, `PREBUILT_SKILLS`, `PREBUILT_TEMPLATES` as
  data — read by the store

### Tests
- Fresh `.adep/` → `list_definitions()` returns 18 definitions
- Fresh `.adep/` → `list_skills()` returns 19 skills
- Fresh `.adep/` → `list_templates()` returns 19 templates
- Create new definition → appears alongside prebuilt ones
- Edit prebuilt definition → disk version takes precedence

---

## URGENT: BLK-160 — HITL Gate Stopgap (REV-006, CRITICAL)

**Priority:** Critical — fabricated safety control
**Estimate:** S (stopgap), L (full fix, blocked on BLK-129)
**Spec file:** `backlog/features/BLK-160_fake-hitl-approval-gate.md`

### Problem
Independent reviewer (REV-006) found that the HITL "Approval Gate" in
the frontend is decorative — Approve/Reject buttons only set local
React state, no API call. The tool has already executed before the
card renders. No `/approve` endpoint exists in the backend.

### Your part (backend stopgap)
None needed immediately. The stopgap is frontend-only (remove fake
buttons, relabel as informational).

### Full fix (blocked on BLK-129)
Implement original BLK-047 spec:
- SSE `gate_triggered` event before high-risk tool execution
- `POST /api/v1/runs/{id}/approve` endpoint
- `POST /api/v1/runs/{id}/reject` endpoint
- Backend pauses at gate, waits for human response
- Requires BLK-129 (async run execution) first

BLK-129 still needs a contract proposal per PROTOCOL.md S7 before
implementation. This is now higher priority given REV-006.

---

## Also: BLK-161 (REV-007) — Mgmt Process Fix

Reviewer found that the frontend's self-audit scored agent control
features 9.5/10 ("Exceeds") while BLK-129 correctly describes them as
non-functional. This is a mgmt-owned process fix — no action needed
from you. Noted here for awareness.

---

## Queue after urgent fixes

| # | ID      | Title                                      | Est |
|---|---------|--------------------------------------------|-----|
| 1 | BLK-130 | Structured logging + OpenTelemetry         | M   |
| 2 | BLK-129 | Async run execution (contract change)      | XL  |
| 3 | BLK-123 | Rate limiting                              | M   |

BLK-129 is now higher priority due to REV-006. Consider submitting
the contract proposal soon.

Report completion via comms to mgmt inbox. Include test count.

## Resolution

### BLK-159 — Store Should Include Prebuilt Content — Complete

**What was done:**
- Modified `DefinitionStore` in `src/definitions/store.py`:
  - `list_definitions()`, `list_skills()`, `list_templates()` — merge prebuilt content with on-disk content via `_merge_with_prebuilt()`. Disk takes precedence (user edits win).
  - `get_definition()`, `get_skill()`, `get_template()` — check disk first, fall back to prebuilt.
  - Added `_merge_with_prebuilt()` method and `_get_prebuilt()` module-level helper.
- Removed from `src/definitions/prebuilt.py`:
  - `seed_store()` function
  - `register_prebuilt_definitions()` function
- Deleted `scripts/seed.py` (dead code)
- Kept `PREBUILT_DEFINITIONS`, `PREBUILT_SKILLS`, `PREBUILT_TEMPLATES` as data — read by the store
- Updated 8 existing tests across `test_store.py`, `test_api.py`, `test_wave6.py`, `test_e2e.py`, `test_stabilization.py`, `test_prebuilt_catalogue.py` to account for prebuilt content in results
- Created `src/tests/test_prebuilt_merge.py` with 21 dedicated tests for BLK-159
- Fixed `test_reviewer_fixes.py` auth default test to use `_env_file=None` (was broken by local `.env` override, not a regression)

**Test results:** 1126 passed, 19 deselected (integration), 0 failures

Spec moved to `implemented/features/`.

### BLK-160 — HITL Gate Stopgap

No backend action needed for stopgap (frontend-only: remove fake buttons, relabel as informational). Full fix blocked on BLK-129 (async run execution).
