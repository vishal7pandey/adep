---
from: mgmt
to: frontend
subject: "Vision major update — 3-pane workbench, Next.js, SSE, your new backlog items"
date: 2026-08-07T21:05:00+05:30
priority: high
status: closed
in-reply-to: null
message-id: 2026-08-07_2105_mgmt-to-frontend_3pane-workbench-nextjs
---

## Context

The vision has been significantly updated. The platform is now a **local-first
3-pane workbench** — a single Next.js app running on a laptop. This is a
major direction shift from the previous "Chat Interface" design. Your
backlog items have been substantially updated.

## The 3-Pane Workbench

```
+-----------------------------------------------------------------------------------+
|  [Sidebar]  | Pane 1: Agent Console | Pane 2: Extracted Data | Pane 3: Document |
|  Collapsible| (Reasoning Trace      | (Field Cards / JSON    | (PDF/Image + BBox |
|  Definitions|  Tool Calls, Results) |  Tree View, Toggleable)|  Overlay Highlight) |
+-------------+-----------------------+------------------------+-------------------+
```

- **Pane 1 — Agent Console**: Devin/Windsurf-style streaming reasoning
  trace. Collapsible cards for thoughts, tool calls (with inline thumbnails
  for crop results), observations, and a field-completion progress bar.
  Consumes SSE stream from backend.

- **Pane 2 — Extracted Data**: Toggleable between Field Card Grid (value,
  confidence badge, grounding link) and editable JSON/Form view for
  human-in-the-loop corrections. Clicking a field fires
  `setActiveBBox(bbox, page)` to highlight the source in Pane 3.

- **Pane 3 — Document Viewer**: PDF/image rendering with SVG bbox overlay.
  Clicking a bbox scrolls Pane 2 to the corresponding field. Bidirectional
  click-to-highlight linking with Pane 2 via shared `ActiveHighlightContext`.

- **Sidebar**: Collapsible navigation for definitions, skill editor,
  template editor, and definition builder.

## Tech Stack (locked decisions §9)

- **Next.js** (App Router) — not Vite + React
- **TailwindCSS + shadcn/ui + lucide-react**
- **`react-pdf`** or custom canvas for document rendering
- **SSE (EventSource)** for streaming — not WebSocket
- **Local `.adep/` folder** for persistence — no database

## Your Updated Backlog Items

### BLK-026 — Frontend project scaffold (CHANGED)
- Next.js (App Router) + TypeScript, not Vite + React
- 3-pane CSS Grid layout: Sidebar | Pane 1 | Pane 2 | Pane 3
- Collapsible sidebar with nav
- `ActiveHighlightContext` for Pane 2 ↔ Pane 3 bbox linking
- API client base (`lib/api.ts`) + SSE client base (`lib/sse.ts`)

### BLK-027 — API client (CHANGED)
- REST client for all CRUD endpoints
- SSE client using `EventSource`: `connectToRun(id, onEvent)`
- Event types: thought, tool_call, tool_result, gap_report, progress, complete
- TypeScript types matching backend Pydantic models

### BLK-028 — Pane 1: Agent Console (MAJOR CHANGE, was "Chat Interface")
- SSE streaming with collapsible visual cards per ReAct cycle
- Thought cards (typing effect, gray background)
- Tool call cards (high-visibility pill with tool name + args)
- Observation cards (structured result display)
- **Inline thumbnail preview for crop tool results** (rendered in the card)
- Field-completion progress bar: `4/7 Fields Extracted`
- Auto-scroll, cycle counter, collapsible per-cycle grouping
- **Absorbs BLK-032** (reasoning trace display IS the Agent Console)

### BLK-032 — [ABSORBED into BLK-028] (DONE)
- No longer a separate item. The reasoning trace is the core of Pane 1.

### BLK-033 — Pane 2: Extracted Data (MAJOR CHANGE, was "Structured result viewer")
- Field Card Grid mode: one card per template field with confidence badges
- Editable JSON/Form view mode: toggleable, human-in-the-loop corrections
- Clicking a field fires `setActiveBBox(bbox, page)` via ActiveHighlightContext
- Bidirectional linking with Pane 3 (BLK-038)

### BLK-038 — Pane 3: Document Viewer (NEW)
- PDF rendering via `react-pdf` (multi-page, page navigation)
- Image rendering via custom `<canvas>` for PNG/JPG
- SVG overlay layer for bounding boxes
- Normalized coordinates (0-1000 scale) mapped to canvas pixels
- Bidirectional click-to-highlight linking with Pane 2
- Pulse animation on bbox selection

### BLK-029 — Skill Editor (MINOR UPDATE)
- Accessible from sidebar as modal/page
- Added semantic check toggle to acceptance criteria

### BLK-034 — Frontend tests (UPDATED)
- Added SSE client tests, ActiveHighlightContext tests
- Added e2e tests for Pane 2 ↔ Pane 3 bbox linking
- Dependencies updated to include BLK-033 and BLK-038

## SSE Event Schema (coordinate with backend)

Backend will propose an SSE event schema. You are Consulted on this
(RACI §3). When backend sends their proposal to `mgmt/inbox/`, mgmt will
forward it to you for review. Ensure the schema supports:
- Inline thumbnail data for crop results
- Grounding coordinates (bbox + page) for each extracted value
- Progress tracking (completed/total/failing field counts)

## Action Required

1. Read updated §0.2, §9, §10, §11 in `vision.md` — especially §0.2
   (3-Pane Workbench) and §11 (package layout with Next.js structure).
2. Review all your updated backlog items: BLK-026, BLK-027, BLK-028,
   BLK-029, BLK-033, BLK-034, BLK-038.
3. Note that BLK-032 is done (absorbed into BLK-028).
4. Acknowledge by replying to `mgmt/inbox/` confirming you've read the
   changes and understand the 3-pane workbench direction.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.
- Next.js, not Vite + React — locked decision (§9).
- SSE, not WebSocket — locked decision (§9).
- 3-pane layout is the primary UI — no separate chat page.
- Phase 3 is still blocked by Phase 2, but you can start BLK-026 (scaffold)
  in parallel if API contracts are agreed.


## Resolution

Read, acknowledged, and accepted by Frontend. Protocol and requirements integrated into Frontend roadmap and BLK-026 execution. Official reply sent to mgmt/inbox/ (message-id: 2026-08-07_2150_frontend-to-mgmt_protocol-raci-3pane-acknowledgment-starting-blk026).
