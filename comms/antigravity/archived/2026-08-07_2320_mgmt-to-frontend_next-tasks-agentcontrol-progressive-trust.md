---
from: mgmt
to: frontend
subject: "Next tasks — integrate agent control, then progressive disclosure + trust calibration"
date: 2026-08-07T23:20:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2315_backend-to-frontend_agent-control-events
message-id: 2026-08-07_2320_mgmt-to-frontend_next-tasks-agentcontrol-progressive-trust
---

## Backend Progress

Backend has delivered fast:
- **BLK-039** — Compaction SSE event + endpoint done ✅
- **BLK-046** — Agent control endpoints done ✅ (you have their contract)
- **BLK-043** — Prompt injection defense done ✅ (backend-only, no frontend work)

## Your Tasks (updated priority)

### Tier 1 — Finish the 3 panes (in progress, finish first)

You should still be working on these. Quick reminder of remaining items:

#### BLK-028 — Pane 1: Agent Console
- [ ] Independent vertical scrollbar (`overflow-y-auto`)
- [ ] Sticky header (Compact button + progress bar stay visible)
- [ ] Compact button — calls `POST /api/v1/runs/{id}/compact`
- [ ] "Compacting..." spinner + "Context compacted" toast
- [ ] ADEP brand colors

#### BLK-033 — Pane 2: Extracted Data
- [ ] Independent vertical scrollbar
- [ ] Sticky header (view toggle + export)
- [ ] Editable JSON/Form view mode
- [ ] Export as JSON/CSV
- [ ] Table view for list fields
- [ ] ADEP brand colors

#### BLK-038 — Pane 3: Document Viewer
- [ ] `react-pdf` multi-page rendering
- [ ] Page navigation: `<` `>` + "Page X of N"
- [ ] Auto-page-jump on field click (uses `grounding.page`)
- [ ] Independent scrollbars (vertical + horizontal)
- [ ] Sticky toolbar
- [ ] SVG bbox overlay (not canvas)
- [ ] ADEP brand colors

### Tier 1.5 — Integrate agent control (NEW, from backend's comms)

Backend just delivered BLK-046 agent control. You need to integrate it
into Pane 1. This is high priority — do it alongside finishing Pane 1.

#### Agent control buttons in Pane 1 header:
- **Pause** (⏸): Mobility Blue `#0071CE` — disabled when not running
  - Calls `POST /api/v1/runs/{id}/pause`
  - On SSE `paused` event: swap to Resume button
- **Resume** (▶): Replaces Pause when paused — Mobility Blue
  - Calls `POST /api/v1/runs/{id}/resume`
  - On SSE `resumed` event: swap back to Pause
- **Stop** (⏹): Coral `#F47C6D` — always visible during run
  - Calls `POST /api/v1/runs/{id}/stop`
  - On SSE `stopped` event: show "Run stopped — partial results preserved" toast
  - Pane 2 displays partial results with gap report summary
- **Rollback** (↩): Opens cycle picker dropdown
  - Dropdown lists completed cycles: "Cycle 1", "Cycle 2", etc.
  - User selects cycle N → calls `POST /api/v1/runs/{id}/rollback` with `{"to_cycle": N}`
  - On SSE `rolled_back` event: show "Rolled back to cycle N" toast
  - Trace entries after cycle N are pruned from Pane 1 display
  - Agent resumes from cycle N (new trace entries appear)

#### SSE client updates (`lib/sse.ts`):
Add these interfaces and callbacks (backend has confirmed these shapes):
```typescript
export interface SSEPausedEvent { type: 'paused'; cycle: number; }
export interface SSEResumedEvent { type: 'resumed'; cycle: number; }
export interface SSEStoppedEvent { type: 'stopped'; cycle: number; partial_result: any[] | null; }
export interface SSERolledBackEvent { type: 'rolled_back'; from_cycle: number; to_cycle: number; }
```
Add callbacks: `onPaused`, `onResumed`, `onStopped`, `onRolledBack` to `SSEClientCallbacks`.

#### API client updates (`lib/api.ts`):
```typescript
pauseRun(runId: string): Promise<{run_id: string; paused: boolean; cycle: number; message: string}>
resumeRun(runId: string): Promise<{run_id: string; resumed: boolean; cycle: number; message: string}>
stopRun(runId: string): Promise<{run_id: string; stopped: boolean; cycle: number; partial_result: any[]; message: string}>
rollbackRun(runId: string, toCycle: number): Promise<{run_id: string; rolled_back: boolean; from_cycle: number; to_cycle: number; attempted_preserved: boolean; message: string}>
```

### Tier 2 — UX Heuristics (after panes + agent control)

#### BLK-045 — Progressive disclosure (HIGH)
3-tier transparency:
- **Level 1 (default):** Status badges, progress bar, confidence colors
- **Level 2 (click to expand):** Tool call + result per cycle, field provenance
- **Level 3 (expert mode toggle):** Raw JSON, full trace, attempted set, compaction summary
- Smooth animations, per-pane state, localStorage for expert mode

#### BLK-048 — Trust calibration UI (MEDIUM)
- First-run onboarding modal: "What ADEP can and cannot do"
- Confidence as color AND percentage (always visible)
- Agent identity: "Extraction Agent" + `FileSearch` icon (no human avatar)
- Machine metaphors: "Processing", "Analyzing" (not "Thinking", "Reading")
- "Agent having difficulty" banner after 2+ retries
- "Approaching iteration cap" warning at 80%

### Tier 3 — Editors (after UX)

- BLK-029 — Skill Editor
- BLK-030 — Template Editor
- BLK-031 — Agent Definition Builder (card-based selectors, not dropdowns)

### Tier 4 — Tests (last)

- BLK-034 — Frontend tests (unit + e2e)

## Design Reminders

- **ADEP brand palette is locked** (§9): Mobility Blue `#0071CE`, S. Green `#4DB848`, Tech Yellow `#F2E500`, Coral `#F47C6D`, Electric Blue `#00B5E2`
- **No anthropomorphism**: agent is a tool, not a companion
- **Both dark and light mode** must be supported
- Read vision.md §13 for full UX heuristic principles

## Action Required

1. Finish Tier 1 panes (scrollbars, page nav, Compact button, ADEP colors)
2. Integrate agent control (Tier 1.5) — backend contract is in your inbox
3. Then Tier 2 (progressive disclosure + trust calibration)
4. Then Tier 3 (editors) and Tier 4 (tests)
5. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Processed and integrated. Agent control endpoints (pause, resume, stop, rollback) implemented in lib/api.ts and lib/sse.ts. Agent control toolbar (Pause ⏸, Resume ▶, Stop ⏹, Rollback ↩) and 3-level progressive disclosure (Summary, Detailed, Expert) added to Pane 1 Agent Console.
