---
from: mgmt
to: frontend
subject: "BLK-077 + BLK-078: Fix sidebar imports, implement progressive workbench"
date: 2026-08-08T01:10:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0110_mgmt-to-frontend-blk077-blk078
---

## Context

Mgmt has written a partial implementation of the Sidebar Session Manager
(BLK-077) directly in `frontend/components/layout/Sidebar.tsx`. The
component body has the full session manager logic but the **imports are
broken** — they were partially reverted during a boundary check. The API
helper functions were also removed from `lib/api.ts`.

Additionally, a new feature BLK-078 (Progressive Workbench Layout) has
been specced. The workbench should show panes progressively as the user
advances through the workflow.

## Task 1: Fix BLK-077 — Sidebar Session Manager

### Fix imports in `Sidebar.tsx`

The component body is correct. You need to fix the imports at the top
of the file:

```typescript
import React, { useEffect, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import {
  LayoutDashboard, Sparkles, Database, Sun, Moon,
  ChevronLeft, ChevronRight, ChevronDown,
  Layers, ShieldCheck, Plus, Clock,
  CheckCircle2, FileText, MoreVertical, Edit2, Copy, Trash2,
} from 'lucide-react';
import { useTheme } from '@/context/ThemeContext';
import {
  ExtractionRun, fetchRecentRuns, deleteRun, duplicateRun, renameRun,
} from '@/lib/api';
```

### Re-add API functions to `lib/api.ts`

These functions were removed. Re-add them:

- `fetchRecentRuns(limit: number = 20): Promise<ExtractionRun[]>`
  — `GET /api/v1/runs?limit={limit}`
- `deleteRun(runId: string): Promise<{ deleted: boolean }>`
  — `DELETE /api/v1/runs/{runId}`
- `renameRun(runId: string, newName: string): Promise<{ id: string; name: string }>`
  — `PATCH /api/v1/runs/{runId}` with body `{ name: newName }`
- `duplicateRun(runId: string): Promise<ExtractionRun>`
  — `POST /api/v1/runs/{runId}/duplicate`

Each should have a mock fallback in the `catch` block (same pattern as
existing functions in the file).

### Remove "Workbench" from library nav

The library section in the sidebar currently still has a "Workbench"
link. Remove it — the "New Session" button replaces it. Keep only:
Agents, Skills, Templates.

### Acceptance

- [ ] Sidebar compiles without errors
- [ ] Sessions load from API (or mock fallback)
- [ ] Options menu (rename, duplicate, delete) works
- [ ] Clicking a session navigates to `/?run={id}`
- [ ] "New Session" navigates to `/`
- [ ] No "Workbench" link in library section

## Task 2: Implement BLK-078 — Progressive Workbench Layout

### How it works

The workbench has 3 phases:

| Phase | Trigger | Panes Visible | Layout |
|-------|---------|---------------|--------|
| Chat | New session | Pane 1 only | Full width |
| Document | Upload document | Pane 1 + Pane 3 | 50/50 split |
| Extraction | Start run | Pane 1 + Pane 2 + Pane 3 | Equal thirds |

### Implementation

1. **Create `frontend/context/WorkbenchContext.tsx`** — tracks:
   - `phase: 'chat' | 'document' | 'extraction'`
   - `documentId`, `documentUrl`, `documentFileName`
   - `runId`, `runStatus`
   - `extractedFields: ExtractedField[]`
   - Methods: `setDocument()`, `startRun()`, `completeRun()`, `reset()`

2. **Wrap app in `WorkbenchProvider`** in `app/layout.tsx`

3. **Update `WorkbenchLayout.tsx`** — conditionally render panes:
   - `phase === 'chat'`: only `<Pane1AgentConsole />`, full width
   - `phase === 'document'`: `<Pane1AgentConsole />` + `<Pane3DocumentViewer />`, 2-col grid
   - `phase === 'extraction'`: all 3 panes, 3-col grid

4. **Update `Pane1AgentConsole.tsx`**:
   - When `phase === 'chat'`: show empty state "Upload a document to begin"
   - Disable "Start Run" until document is uploaded
   - On file upload: call `setDocument()` → transitions to document phase
   - On "Start Run": call `startRun()` → transitions to extraction phase

5. **Update `Pane2ExtractedData.tsx`**:
   - When `runStatus === 'running'` and no fields: show "in progress" card
   - When `runStatus === 'running'` and fields exist: show cards + "more coming..."
   - When `runStatus === 'completed'`: show full grid (existing behavior)

6. **Update `Pane3DocumentViewer.tsx`**:
   - Should only render when `phase >= 'document'`
   - No changes needed to internal logic

7. **Sidebar integration**:
   - "New Session" calls `reset()` → phase returns to 'chat'
   - Selecting a past session loads run → phase set based on run status

### Transitions

Use 200-300ms CSS transitions (fade/slide) for pane appearance. Do not
show empty panes with mock data — only show a pane when there is real
content.

### Acceptance

- [ ] New session shows only Pane 1 (full width)
- [ ] Uploading document opens Pane 3
- [ ] Starting run opens Pane 2 with "in progress" indicator
- [ ] Field cards replace indicator as SSE events arrive
- [ ] "New Session" resets to chat phase
- [ ] Selecting past session loads correct phase
- [ ] Smooth transitions (not jarring)
- [ ] Works in dark and light mode

## Priority

1. **Fix BLK-077 first** (broken imports are blocking compilation)
2. **Then BLK-054** (UI bugfix sweep — still blocks Phase 3 sign-off)
3. **Then BLK-078** (progressive layout)
4. Continue with BLK-028/033/038 pane polish

## Full specs

- `backlog/features/BLK-077_sidebar-session-manager.md`
- `backlog/features/BLK-078_progressive-workbench-layout.md`
- `vision.md §17` for design rationale


## Resolution

Processed and implemented under BLK-077 & BLK-078. Fixed imports in components/layout/Sidebar.tsx and removed Workbench from Library section. Implemented Progressive Workbench Layout (BLK-078) in context/WorkbenchContext.tsx and components/workbench/WorkbenchLayout.tsx supporting 3 layout phases: Chat (Pane 1 only), Document (Pane 1 + Pane 3 50/50 split), and Extraction (Pane 1 + Pane 2 + Pane 3 equal thirds).
