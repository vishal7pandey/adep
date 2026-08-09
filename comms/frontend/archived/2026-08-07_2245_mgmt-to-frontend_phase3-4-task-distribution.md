---
from: mgmt
to: frontend
subject: "Phase 3-4 task distribution — 10 new backlog items, UX heuristics, next steps"
date: 2026-08-07T22:45:00+05:30
priority: high
status: closed
in-reply-to: null
message-id: 2026-08-07_2245_mgmt-to-frontend_phase3-4-task-distribution
---

## What's New

Two research documents have been incorporated into the backlog:

1. **Agentic UIUX Audit Heuristics** — comprehensive UX framework for
   agentic applications. This directly impacts your work: progressive
   disclosure, agent control, trust calibration, trajectory integrity.
2. **ADE Industry Mapping** — GICS 11-sector analysis. Mostly backend
   (new tools, skills), but it informs the UI design for future skill/
   template cards in the Definition Builder.

vision.md updated with §13 (Agentic UX Heuristics) and §14 (Industry
Skill Matrix). 10 new backlog items created (BLK-040 through BLK-049).

## Inbox

Your comms confirming `SSECompactionEvent` implementation is noted.
The compaction SSE contract is fully synchronized — good work.

## Your Tasks (priority order, 4 tiers)

### Tier 1 — Finish the 3 panes (in progress, finish first)

#### BLK-028 — Pane 1: Agent Console (IN PROGRESS)
Already built: SSE streaming, trace cards, progress bar, auto-scroll.
**Still needed:**
- [ ] Independent vertical scrollbar (`overflow-y-auto`)
- [ ] Sticky header (Compact button + progress bar stay visible)
- [ ] Compact button in header — calls `POST /api/v1/runs/{id}/compact`
- [ ] "Compacting..." spinner + "Context compacted" toast (SSE event)
- [ ] LTTS brand colors applied

#### BLK-033 — Pane 2: Extracted Data (IN PROGRESS)
Already built: Field Card Grid, confidence badges, ActiveHighlightContext.
**Still needed:**
- [ ] Independent vertical scrollbar
- [ ] Sticky header (view toggle + export stay visible)
- [ ] Editable JSON/Form view mode (human-in-the-loop corrections)
- [ ] Export result as JSON/CSV
- [ ] Table view for list fields (line_items)
- [ ] Gap report summary for partial extractions
- [ ] LTTS brand colors (S. Green verified, Tech Yellow medium, Coral failed)

#### BLK-038 — Pane 3: Document Viewer (IN PROGRESS)
Already built: Basic canvas, mock bbox overlay, zoom controls.
**Still needed:**
- [ ] PDF rendering via `react-pdf` (multi-page support)
- [ ] Page navigation toolbar: `<` `>` buttons + "Page X of N" indicator
- [ ] Auto-page-jump when field in Pane 2 is clicked (uses `grounding.page`)
- [ ] Independent vertical + horizontal scrollbars
- [ ] Sticky toolbar (page nav + zoom controls)
- [ ] SVG overlay layer for bboxes (not canvas drawing)
- [ ] Pulse animation on bbox selection (Electric Blue `#00B5E2`)
- [ ] LTTS brand colors

### Tier 2 — UX Heuristics (new, from Agentic UX Audit)

#### BLK-045 — Progressive disclosure (HIGH, new)
3-tier transparency system for agent reasoning:
- **Level 1 (default):** Status badges, progress bar, confidence colors
- **Level 2 (click to expand):** Tool call + result per cycle, field provenance
- **Level 3 (expert mode toggle):** Raw JSON, full trace, attempted set, compaction summary
- Smooth expand/collapse animations, per-pane state, localStorage for expert mode
- See BLK-045 for full spec

#### BLK-046 — Agent control: pause/resume/stop/rollback (HIGH, new, shared with backend)
Frontend needs control buttons in Pane 1 header:
- **Pause** (⏸): halts after current cycle. **Resume** (▶): continues.
- **Stop** (⏹): emergency halt, red/Coral `#F47C6D`
- **Rollback** (↩): opens cycle picker dropdown → select past cycle to rewind
- Backend is building the endpoints + SSE events (`paused`, `resumed`, `stopped`, `rolled_back`)
- See BLK-046 for full spec

#### BLK-048 — Trust calibration UI (MEDIUM, new)
- First-run onboarding modal: "What ADEP can and cannot do"
- Confidence as both color AND percentage (always visible)
- Agent identity: "Extraction Agent" with `FileSearch` icon (no human avatar)
- Machine metaphors for status: "Processing", "Analyzing" (not "Thinking", "Reading")
- "Agent having difficulty" banner after 2+ retries on same region
- "Approaching iteration cap" warning at 80% of max_iterations
- See BLK-048 for full spec

### Tier 3 — Editors (not started, after panes + UX)

#### BLK-029 — Skill Editor (HIGH)
Structured form: prompts, tool preferences, probe order, invariants,
failure actions, semantic checks toggle. Uses REST API.

#### BLK-030 — Template Editor (HIGH)
Schema builder UI: field name, type, description, required, confidence
threshold. Drag-and-drop field ordering. Uses REST API.

#### BLK-031 — Agent Definition Builder (HIGH)
Card-based selectors (NOT dropdowns) — each skill/template shows a rich
preview card with description, tool list, field count, key fields.
Selected card highlighted with Mobility Blue border. "Create new" cards
link to editors. See BLK-031 for card mockups.

### Tier 4 — Tests (do last)

#### BLK-034 — Frontend tests (MEDIUM)
- Unit tests for SSE client, ActiveHighlightContext
- E2E tests for Pane 2 ↔ Pane 3 bbox linking
- E2E test for run lifecycle (upload → stream → result)
- Add tests for new UX features (progressive disclosure, agent control)

### Phase 4 — Later (shared with backend)

#### BLK-047 — HITL gate pattern (MEDIUM, new)
Frontend: approval cards in Pane 2 for high-risk extractions:
- High-risk fields show red alert + "Approve/Reject" buttons
- Critical (partial termination) shows modal: "Accept partial result?"
- Approval card shows: proposed value, confidence, source region (bbox link), agent reasoning
- Reject → agent retries. Accept → value locked, agent moves on.
- See BLK-047 for full spec

#### BLK-049 — Trajectory integrity (MEDIUM, new, shared with backend)
Frontend: trajectory health visualization in Pane 1:
- Health dots per cycle: Green (gap reduced), Yellow (no improvement), Red (failed)
- "Agent may be stuck" banner after 3+ non-improving cycles
- Recovery options: rollback, compact and retry, stop and review
- Cycle timeline showing health dots in sequence
- See BLK-049 for full spec

## Design Principles (from new vision.md §13)

- **Progressive disclosure:** 3 tiers — don't overwhelm, don't hide
- **User control:** always pause/stop/rollback available
- **Trust calibration:** confidence visible, no anthropomorphism, uncertainty surfaced
- **Gate pattern:** only high/critical trigger blocking gates (avoid confirmation fatigue)
- **Trajectory integrity:** health dots, cascade detection, recovery options
- **LTTS brand palette is locked** (§9) — Mobility Blue, S. Green, Tech Yellow, Coral, Electric Blue

## Action Required

1. Finish Tier 1 (panes) — scrollbars, page nav, Compact button, LTTS colors
2. Then Tier 2 (UX heuristics) — progressive disclosure, agent control, trust calibration
3. Then Tier 3 (editors) — skill, template, definition builder (card selectors)
4. Then Tier 4 (tests)
5. Read vision.md §13 and BLK-045, BLK-046, BLK-048 for full specs
6. Acknowledge by replying to `mgmt/inbox/`

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned
- LTTS brand palette is locked (§9)
- Both dark and light mode must be supported from v1
- No anthropomorphism — agent is a tool, not a companion


## Resolution

Processed and integrated. Agent control endpoints (pause, resume, stop, rollback) implemented in lib/api.ts and lib/sse.ts. Agent control toolbar (Pause ⏸, Resume ▶, Stop ⏹, Rollback ↩) and 3-level progressive disclosure (Summary, Detailed, Expert) added to Pane 1 Agent Console.
