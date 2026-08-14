---
id: BLK-248
type: bug
title: "Sidebar session management drops unhandled async errors and fabricates document_url from run names"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T12:40:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [frontend, sidebar, session, error-handling, data-corruption, reliability]
---

## Description

In `frontend/components/layout/Sidebar.tsx` the session management handlers have multiple defects:

1. **Delete has no confirmation and no error handling** (~lines 85-94) — `handleDeleteSession` calls `await deleteRun(id)` then removes the row immediately. If the delete fails, the run is repainted as gone on the client but persists server-side (data-loss confusion), with zero user feedback and an unhandled promise rejection.
2. **Duplicate has no error handling** (~lines 96-102) — same pattern; failure to duplicate is invisible.
3. **Rename mutates the wrong field** (~lines 103-113) — `renameRun(id, newName)` persists the name, but the local session list is updated with `{ ...s, document_url: newName }`. This corrupts the UI's source-document identity: the rename writes the display name into the document URL field, so subsequent session select and preview flows treat the run name as a file path (a real, user-visible corruption).

## Problem Statement

Session management is a primary workflow: rename/duplicate/delete. Each mutation is a fire-and-forget promise without error state, and rename mutates the wrong property. Given BLK-185 already notes the run metadata drift on `document_url`/`name`, this is the same domain touching the backend contract — the frontend currently thickens the inconsistency.

## Acceptance Criteria

- [ ] Delete has a confirm dialog (matching definitions/skills pages) and shows an error state on failure
- [ ] Rename/duplicate failures surface an inline error and do not optimistically corrupt local state
- [ ] Rename updates the correct display field (e.g. `name`), never `document_url`
- [ ] Keyboard shortcut dispatchers (Space/1/2/3) ignore events when focus is on any interactive element (button/link/etc.), not just text inputs
- [ ] Sidebar tests: rename updates `name`; delete failure keeps the row and shows error
- [ ] Document focus policy for keyboard listener volume

## Constraints

- Renaming must be consistent with the backend canonical metadata contract from BLK-185 (do not fork a third field)
- Keep optimistic UI where server confirmation is known (add/remove on confirmed success, rollback on failure)
- Scope the keyboard-guard piece narrowly and keep it in this ticket only if trivial; otherwise split it

## Dependencies

- `frontend/components/layout/Sidebar.tsx`
- `frontend/lib/api.ts` (`renameRun`, `deleteRun`, `duplicateRun`)
- Backend run metadata contract (BLK-185)
- `frontend/components/workbench/Pane1AgentConsole.tsx` (shortcut guard)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:40 (mgmt)**: Filed from reading Sidebar session handlers and the Pane 1 keyboard hook.
