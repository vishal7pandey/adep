# BLK-172: Duplicate P&ID prebuilt definitions (def-pid-to-dexpi and def-pnid-to-dexpi)

- **Priority:** P3 — Low
- **Status:** backlog
- **Owner:** unassigned
- **Phase:** 5
- **Type:** bug
- **Reported:** 2026-08-08

## Problem

Two identical prebuilt definitions exist in `prebuilt.py`:
- `def-pid-to-dexpi` (line 404)
- `def-pnid-to-dexpi` (line 385)

Both have the same name ("P&ID to DEXPI Converter"), same skill_id, same template_id, same tool_names, and same agent_config. This causes:
1. Two entries in the definition dropdown with the same display name
2. The frontend has to check both IDs in conditional logic (`Pane2ExtractedData.tsx` line 365)
3. User confusion — which one to select?

## Root Cause

Likely a copy-paste artifact during the P&ID feature implementation. One uses "pid" and the other "pnid" (Piping and Instrumentation Diagram).

## Files Affected

- `src/definitions/prebuilt.py` — lines 385-421
- `frontend/components/workbench/Pane2ExtractedData.tsx` — line 365 checks both IDs

## Fix

1. Remove `def-pid-to-dexpi` (keep `def-pnid-to-dexpi` as the canonical ID matching the vision document)
2. Update any frontend references to `def-pid-to-dexpi` to use `def-pnid-to-dexpi`
3. Update any tests that reference `def-pid-to-dexpi`

## Acceptance Criteria

- [ ] Only one P&ID prebuilt definition exists
- [ ] No duplicate names in definition dropdown
- [ ] All references updated to canonical ID
- [ ] All tests pass
