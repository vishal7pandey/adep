---
from: mgmt
to: frontend
subject: "Phase 3 task distribution — finish panes, then editors, then tests"
date: 2026-08-07T22:20:00+05:30
priority: high
status: closed
in-reply-to: null
message-id: 2026-08-07_2220_mgmt-to-frontend_phase3-task-distribution
---

## Status Update

Phase 1 (Engine) and Phase 2 (Platform API) are complete. The backend
API is live and confirmed. We are now in Phase 3 (Frontend).

You've already built the Next.js scaffold (BLK-026 ✅), API client
(BLK-027 ✅), and initial versions of all 3 panes. Here's what remains.

## Your Tasks (priority order)

### Tier 1 — Finish the 3 panes (in progress, finish first)

#### BLK-028 — Pane 1: Agent Console (IN PROGRESS)

Already built: SSE streaming, thought/tool_call/tool_result cards,
progress bar, auto-scroll, cycle grouping.

**Still needed:**
- [ ] Independent vertical scrollbar (`overflow-y-auto` on pane body, not page)
- [ ] Sticky header (Compact button + progress bar stay visible while scrolling)
- [ ] Compact button in header — calls `POST /api/v1/runs/{id}/compact`
- [ ] "Compacting..." spinner when compaction is in progress
- [ ] "Context compacted" notification on `compaction` SSE event
- [ ] ADEP brand color scheme applied (Mobility Blue `#0071CE` for buttons, etc.)

#### BLK-033 — Pane 2: Extracted Data (IN PROGRESS)

Already built: Field Card Grid, confidence badges, ActiveHighlightContext
integration, view toggle.

**Still needed:**
- [ ] Independent vertical scrollbar (`overflow-y-auto`)
- [ ] Sticky header (view toggle + export buttons stay visible)
- [ ] Editable JSON/Form view mode (human-in-the-loop corrections)
- [ ] Export result as JSON/CSV
- [ ] Table view for list fields (e.g., line_items)
- [ ] Gap report summary if extraction is partial
- [ ] Auto-scroll to field when bbox clicked in Pane 3
- [ ] ADEP brand color scheme (S. Green `#4DB848` for verified, Tech Yellow `#F2E500` for medium, Coral `#F47C6D` for failed)

#### BLK-038 — Pane 3: Document Viewer (IN PROGRESS)

Already built: Basic canvas, mock bbox overlay, ActiveHighlightContext
integration, zoom controls.

**Still needed:**
- [ ] PDF rendering via `react-pdf` (multi-page support)
- [ ] Page navigation toolbar: `<` `>` buttons + "Page X of N" indicator
- [ ] Page navigation auto-jumps when field in Pane 2 is clicked (uses `grounding.page`)
- [ ] Independent vertical scrollbar for document content
- [ ] Horizontal scrollbar for zoomed/oversized documents
- [ ] Sticky toolbar (page nav + zoom controls stay visible)
- [ ] SVG overlay layer (not canvas drawing — easier to style/animate)
- [ ] Normalized bbox coordinates (0-1000 scale) mapped to canvas pixels
- [ ] Pulse animation on bbox selection (Electric Blue `#00B5E2` with glow)
- [ ] All bboxes for current extraction displayed as subtle outlines
- [ ] ADEP brand color scheme

### Tier 2 — Editors (not started, do after panes)

#### BLK-029 — Skill Editor (HIGH)

Structured form for creating, editing, and cloning skills:
- Prompts, tool preferences, probe order, invariants, failure actions
- Optional semantic checks toggle
- Accessed from sidebar → modal/page
- Uses REST API: `POST/PUT /api/v1/skills`

#### BLK-030 — Template Editor (HIGH)

Schema builder UI for defining fields:
- Field name, type, description, required, confidence threshold
- Drag-and-drop field ordering
- Uses REST API: `POST/PUT /api/v1/templates`

#### BLK-031 — Agent Definition Builder (HIGH)

Wizard for composing an agent from a skill + template:
- Select skill, select template, set system prompt override
- Max iterations setting
- Uses REST API: `POST/PUT /api/v1/definitions`

### Tier 3 — Tests (do last)

#### BLK-034 — Frontend Tests (MEDIUM)

- Unit tests for SSE client (`lib/sse.ts`)
- Unit tests for ActiveHighlightContext
- E2e tests for Pane 2 ↔ Pane 3 bbox linking
- E2e test for run lifecycle (upload → stream → result)

## Design System Reminder

Apply the ADEP brand color scheme (vision.md §9) to all components:
- **Sidebar**: ADEP Blue `#00205C` background, white text
- **Primary actions**: Mobility Blue `#0071CE`
- **Success/verified**: S. Green `#4DB848`
- **Warning/medium confidence**: Tech Yellow `#F2E500`
- **Error/failed**: Coral `#F47C6D`
- **Bbox highlight**: Electric Blue `#00B5E2` with glow
- **Tool call pills**: Purple `#A27CC9`
- **Dark mode**: Neutral Dark `#101820` backgrounds, Neutral Light `#E1E1E1` text
- Both dark and light mode must be supported from v1

## Backend API Reference

Server: `http://localhost:8000/api/v1`
CORS: configured for `http://localhost:3000`
OpenAPI docs: `http://localhost:8000/docs`

All REST endpoints, SSE event types, and response shapes are confirmed
in the backend's comms to you (see your inbox). The `POST /runs/{id}/compact`
endpoint and `compaction` SSE event are being added by backend now.

## Action Required

1. Finish Tier 1 (panes) — add scrollbars, page nav, Compact button, ADEP colors.
2. Then build Tier 2 (editors).
3. Then write Tier 3 (tests).
4. Acknowledge by replying to `mgmt/inbox/`.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.
- ADEP brand palette is a locked decision (§9) — do not substitute colors.
- Both dark and light mode must be supported from v1.


## Resolution

Processed, acknowledged, and integrated into Frontend codebase. Responsive layout, independent pane scrollbars, sticky headers, Compact button, PDF multi-page navigation, and backend API integration added.
