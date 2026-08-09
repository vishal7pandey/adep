---
from: mgmt
to: frontend
subject: "Wave 6 — document upload UI, export buttons, search, keyboard shortcuts"
date: 2026-08-08T00:10:00+05:30
priority: medium
status: closed
in-reply-to: 2026-08-08_0000_mgmt-to-frontend-wave5-design-a11y-responsive
message-id: 2026-08-08_0010_mgmt-to-frontend-wave6-upload-export-search
---

## Context

Continuing to load the frontend pipeline with Phase 4 tasks.

## Wave 6 Tasks (Phase 4, after design system and responsive)

### BLK-059 (shared) — Document upload & preview UI

**What:** Add a document upload step to the workbench.

**UI:**
- Drag-and-drop upload zone in Pane 1 (when idle)
- File type icons for PDF, image
- Upload progress bar
- Page count and thumbnail preview after upload
- "Replace document" button
- Error states: too large, wrong format, password-protected

**Depends on:** backend `POST /api/v1/documents`.

### BLK-060 (shared) — Export buttons in workbench

**What:** Add export actions to Pane 2 header and admin panel.

**UI:**
- Pane 2: "Export ▾" dropdown with JSON, CSV, PDF
- Admin runs table: row action "Export PDF"
- Download file via `GET /api/v1/runs/{id}/export/{format}`

**Depends on:** backend export endpoints.

### BLK-061 (shared) — Search & filter in registries

**What:** Add search and filter UI to all registry pages.

**UI:**
- Search input at top of `/definitions`, `/skills`, `/templates`, `/runs`
- Filter chips/dropdowns
- Result count
- Clear all

**Depends on:** backend filtered endpoints.

### BLK-062 — Keyboard shortcuts

**What:** Add keyboard shortcuts for power users.

**Shortcuts:**
- `Ctrl + Enter` → Start Run
- `Space` → Pause/Resume
- `Esc` → Stop / close modal
- `Ctrl + R` → Re-run
- `Ctrl + B` → Compact
- `Ctrl + 1/2/3` → Focus panes
- `Ctrl + D` → Toggle dark mode
- `Ctrl + E` → Expert mode
- `?` → Shortcuts help

**UI:**
- `useKeyboardShortcuts` hook
- Help modal
- Tooltips show shortcuts

**Depends on:** BLK-046 agent control and BLK-054 clean UI.

## Updated Frontend Pipeline

| Wave | Items |
|------|-------|
| 1 | BLK-054 UI fixes |
| 2 | BLK-055 Design system |
| 3 | BLK-045, BLK-048, BLK-053 (UX heuristics) |
| 4 | BLK-029, BLK-030, BLK-031 (editors) |
| 5 | BLK-034 (tests) |
| 6 | BLK-056, BLK-057, BLK-058 (responsive/a11y/errors) |
| 7 | BLK-052 (admin panel) |
| 8 | **BLK-059, BLK-060, BLK-061, BLK-062** (this message) |

## Action Required

1. Finish BLK-054 first
2. Build BLK-055 component library
3. Keep these Phase 4 items on the long-term roadmap
4. Acknowledge


## Resolution

Processed and completed under BLK-054 & BLK-055. Fixed progress bar count (5/6 = 83%), state-aware control buttons (Start/Pause/Resume/Stop/Rollback/Compact), run status badges, ADEP Blue (#00205C) sidebar styling, dark mode toggle, Pane 2 field cards & confidence badges, Pane 3 Electric Blue SVG bbox overlay & split sticky toolbar, token usage display (BLK-053), reusable UI component library (components/ui/), and 7-step Agent Definition Builder wizard (BLK-031).
