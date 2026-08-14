---
id: BLK-252
type: bug
title: "Workbench session deep-link (?run=XYZ) never restores the run — URL param is decorative"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T13:00:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, workbench, deep-link, routing, session, ux]
---

## Description

`Sidebar.tsx` (lines ~38, ~82) pushes `/?run=${id}` when a session is selected. `WorkbenchLayout.tsx` reads `useSearchParams()` but only consumes `view`; nothing hydrates `WorkbenchContext` from a `run` query param. On refresh of `/?run=xyz`, the app re-mounts with `phase='chat'` and no active session — the run param is decorative dead state.

## Problem Statement

Session deep-linking is a core navigation expectation (share a URL, refresh during a run, browser-back). Currently refreshing the workbench during or after a run loses the document/session entirely, forcing the user to re-select the run. The Sidebar already writes the param that the layout ignores.

## Acceptance Criteria

- [ ] `WorkbenchLayout` (or the workbench page) reads `run` from the query string on mount and restores the corresponding session (fetch run, set activeRunId, hydrate Pane state phase/document)
- [ ] If the id is missing/invalid, show a clean empty state (not a spinner/blank)
- [ ] URL and context stay in sync when the user switches sessions (no stale param)
- [ ] A test: load `/?run=<id>` → WorkbenchContext contains that run's metadata

## Constraints

- Keep the upgrade from phase=chat → document workbench explicit and reversible
- Follow the REST source of truth for run metadata (BLK-176 #2 / fetchRun)

## Dependencies

- `frontend/components/layout/WorkbenchLayout.tsx`
- `frontend/context/WorkbenchContext.tsx`
- `frontend/components/layout/Sidebar.tsx`
- `frontend/lib/api.ts` (`fetchRun`)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:00 (mgmt)**: Filed after reading the search-params handling in WorkbenchLayout and the Sidebar's run URL usage.
