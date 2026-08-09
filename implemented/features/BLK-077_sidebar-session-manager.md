---
id: BLK-077
type: feature
title: "Sidebar session manager — New Session, recent sessions, and asset library"
priority: high
status: backlog
phase: 3
owner: frontend
created: 2026-08-08T00:45:00+05:30
started: 2026-08-08T00:50:00+05:30
completed: null
estimate: S
depends-on: [BLK-026, BLK-022]
tags: [frontend, sidebar, sessions, runs, navigation, ui]
---

## Description

Redesign the left sidebar into a session manager. Users switch between
extraction sessions quickly, start new sessions, and access the asset
library (Agents, Skills, Templates) in one place.

## Sidebar Structure

```
[ADEP Workbench header]

[New Session]  ← primary button

Recent Sessions
  ◆ Session 1  ...
  ◆ Session 2  ...
  ◆ Session 3  ...
  more...       ← expands to show all

─────────────────

Library
  Agents
  Skills
  Templates

─────────────────

[Theme toggle]
[collapse]
```

## Sections

### New Session
- Button at the top of the sidebar
- Clears current run and loads blank workbench at `/`
- Active state (solid Mobility Blue) when no `?run=` in URL

### Recent Sessions
- Shows latest 3 sessions by default
- Each session shows:
  - Status icon (color-coded by run state)
  - Session name (document name or run ID)
  - Status label + extraction progress %
  - `...` options menu on hover
- `more...` expands to show full list (up to 50)
- Clicking a session navigates to `/?run={id}`

### Session Options Menu
- Rename
- Duplicate
- Export (JSON)
- Delete

### Library
- Links to `/definitions`, `/skills`, `/templates`
- Labels simplified to:
  - Agents
  - Skills
  - Templates

## Acceptance Criteria

- [ ] `New Session` button at top of sidebar
- [ ] Recent sessions list with status, name, progress
- [ ] `...` options menu per session
- [ ] `more...` expand/collapse
- [ ] Horizontal divider before Library
- [ ] Library section with Agents/Skills/Templates
- [ ] Click session → load run in workbench
- [ ] Collapsed sidebar shows session status icons only
- [ ] New `fetchRecentRuns`, `deleteRun`, `duplicateRun`, `renameRun` in
      `lib/api.ts`
- [ ] Backend `GET /api/v1/runs?limit=N` returns recent runs
- [ ] Dark mode and light mode support
- [ ] LTTS brand colors

## Constraints

- Remove old "Workbench" nav link — New Session replaces it
- Session names derive from `document_url` until `name` field is added
- v1: options menu uses a simple inline dropdown, not a full menu component

## Dependencies

- BLK-026 (frontend scaffold)
- BLK-022 (runs API)

## Implementation Notes (from mgmt)

Mgmt has written a partial implementation in `Sidebar.tsx`. The component
body has the session manager logic but the **imports are broken** — they
were partially reverted. The frontend team must:

1. **Fix imports in `Sidebar.tsx`** — add `useEffect`, `useRouter`,
   `useSearchParams` from `next/navigation`, plus lucide icons: `Plus`,
   `Clock`, `ChevronDown`, `CheckCircle2`, `FileText`, `MoreVertical`,
   `Edit2`, `Copy`, `Trash2`. Import `ExtractionRun`, `fetchRecentRuns`,
   `deleteRun`, `duplicateRun`, `renameRun` from `@/lib/api`.
2. **Re-add API functions to `lib/api.ts`** — `fetchRecentRuns`,
   `deleteRun`, `duplicateRun`, `renameRun` were removed. Re-add them
   with proper API calls and mock fallbacks.
3. **Test the component** — verify sessions load, options menu works,
   navigation to `/?run={id}` functions correctly.
4. **Remove "Workbench" from library nav** — the New Session button
   replaces it. Keep Agents, Skills, Templates only.
