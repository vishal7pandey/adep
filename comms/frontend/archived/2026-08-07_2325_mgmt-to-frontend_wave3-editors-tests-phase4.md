---
from: mgmt
to: frontend
subject: "Wave 3 tasks — editors (BLK-029, BLK-030, BLK-031), tests (BLK-034), Phase 4 preview"
date: 2026-08-07T23:25:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2320_mgmt-to-frontend_next-tasks-agentcontrol-progressive-trust
message-id: 2026-08-07_2325_mgmt-to-frontend_wave3-editors-tests-phase4
---

## Context

You should now be working on Tier 1 (finish panes) and Tier 1.5 (integrate
agent control). This message loads up Tier 3 (editors), Tier 4 (tests),
and gives you a preview of Phase 4 frontend work so you can plan ahead.

## Wave 3 Tasks (after panes + agent control + UX heuristics)

### Tier 3 — Editors

#### BLK-029 — Skill Editor (HIGH)

Structured form for creating, editing, and cloning skills.

**Form fields:**
- Skill name (text input)
- Description (textarea)
- System prompt (textarea — the LLM instruction prompt)
- Tool preferences (multi-select chips from tool registry: `ocr`, `vlm`,
  `crop`, `deskew`, `detect_layout`, `detect_tables`, `read_table`,
  `read_chart`, `cross_check`, `ground`)
- Probe order (drag-and-drop sortable list — each item has a rationale
  type + description, e.g. "Try OCR first → fallback to VLM if confidence low")
- Invariants (dynamic list — each row: field name + invariant type
  [date_compare, numeric_tolerance, coverage_loop, sum_check] + params)
- Failure actions (dynamic list — each row: condition + action
  [crop, deskew, denoise, threshold, vlm_escalation])
- Semantic checks toggle (on/off)
- Semantic prompt (textarea, shown only when toggle is on)

**UI design:**
- Full-page form (not modal — too many fields for a modal)
- Sidebar nav within the form: "Basics", "Tools", "Probe Order",
  "Invariants", "Failure Actions", "Semantic Checks"
- Save button in sticky footer
- "Clone" button in header (copies all fields, clears name)
- Uses REST API: `POST /api/v1/skills`, `PUT /api/v1/skills/{id}`
- ADEP brand colors throughout
- Form validation: name required, at least 1 tool required

#### BLK-030 — Template Editor (HIGH)

Schema builder UI for defining extraction outcome contracts.

**Form fields:**
- Template name (text input)
- Description (textarea)
- Fields (dynamic list — drag-and-drop reorderable):
  - Field name (text input, snake_case)
  - Field type (dropdown: `string`, `number`, `boolean`, `date`, `list`,
    `object`)
  - Description (text input — helps the agent understand what to extract)
  - Required (toggle)
  - Confidence threshold (number input, 0.0–1.0, default 0.7)
  - For `list` type: sub-fields (nested dynamic list)
  - For `object` type: sub-fields (nested dynamic list)

**UI design:**
- Full-page form with field list as the main content area
- Each field is a card with expand/collapse for details
- Drag handle on each card for reordering
- "Add Field" button at bottom of list
- "Add Sub-Field" button inside list/object type cards
- Save button in sticky footer
- "Clone" button in header
- Uses REST API: `POST /api/v1/templates`, `PUT /api/v1/templates/{id}`
- ADEP brand colors
- Form validation: name required, at least 1 field required, required
  fields must have confidence threshold

#### BLK-031 — Agent Definition Builder (HIGH)

Card-based selectors — NOT dropdowns. Already specced in BLK-031 with
card mockups. Key reminders:

- **Skill cards**: name, description, tool chips, semantic checks badge
- **Template cards**: name, description, field count, first 3-4 field names
- **Tool chips**: toggleable multi-select with name + 1-line description
- **Selected state**: Mobility Blue `#0071CE` border + light blue background
- **"Create new" cards**: link to Skill/Template Editor
- **Review step**: read-only summary card before saving
- **Wizard flow**: Name → Skill → Template → Tools → Prompt → Iterations → Review → Save

### Tier 4 — Tests

#### BLK-034 — Frontend tests (MEDIUM)

**Unit tests (Jest + React Testing Library):**
- [ ] SSE client (`lib/sse.ts`): event parsing, callback dispatch, reconnection
- [ ] API client (`lib/api.ts`): all REST methods, error handling
- [ ] ActiveHighlightContext: set/clear highlight, cross-pane linking
- [ ] ThemeContext: dark/light toggle, localStorage persistence
- [ ] Pane1AgentConsole: trace rendering, cycle grouping, auto-scroll
- [ ] Pane2ExtractedData: field card rendering, confidence badges, view toggle
- [ ] Pane3DocumentViewer: bbox overlay, page navigation, zoom controls
- [ ] Agent control buttons: pause/resume/stop/rollback state transitions
- [ ] Progressive disclosure: level 1/2/3 toggle, expert mode persistence
- [ ] Trust calibration: onboarding modal, confidence display, uncertainty banners

**E2E tests (Playwright or Cypress):**
- [ ] Full run lifecycle: upload document → select definition → start run →
  watch SSE stream → verify extracted data in Pane 2 → verify bbox in Pane 3
- [ ] Pane 2 ↔ Pane 3 bbox linking: click field in Pane 2 → bbox highlights
  in Pane 3, click bbox in Pane 3 → field scrolls into view in Pane 2
- [ ] Agent control: start run → pause → resume → stop → verify partial results
- [ ] Rollback: start run → rollback to cycle N → verify trace pruned
- [ ] Compact: start run → click Compact → verify toast notification
- [ ] Definition Builder: create new definition → select skill card →
  select template card → save → verify in definition list
- [ ] Skill Editor: create skill → fill form → save → verify in skill list
- [ ] Template Editor: create template → add fields → save → verify in list
- [ ] Dark/light mode toggle: switch theme → verify all panes render correctly

## Phase 4 Preview (for planning, not yet assigned)

These items will come after Phase 3 sign-off. Frontend has work in two:

**BLK-047 — HITL gate pattern (frontend side):**
- Approval cards in Pane 2 for high-risk extractions
- "Approve/Reject" buttons on high-confidence-failed fields
- Modal for critical (partial termination): "Accept partial result?"
- Approval card shows: proposed value, confidence, source bbox (link to
  Pane 3), agent reasoning
- Backend is building the endpoints + SSE `gate_triggered` event

**BLK-049 — Trajectory integrity (frontend side):**
- Health dots per cycle in Pane 1 (green/yellow/red)
- "Agent may be stuck" banner after 3+ non-improving cycles
- Recovery options: rollback, compact and retry, stop and review
- Cycle timeline visualization showing health dots in sequence
- Backend is building cascade detection + SSE events

## Full Frontend Pipeline (for your planning)

| Wave | Tier | Items | Status |
|------|------|-------|--------|
| 1 | Tier 1 | BLK-028, BLK-033, BLK-038 | In progress (finish panes) |
| 1 | Tier 1.5 | BLK-046 integration | Assigned (agent control buttons) |
| 2 | Tier 2 | BLK-045, BLK-048 | Assigned (progressive disclosure, trust calibration) |
| 3 | Tier 3 | BLK-029, BLK-030, BLK-031 | This message (editors) |
| 3 | Tier 4 | BLK-034 | This message (tests) |
| 4 | Phase 4 | BLK-047, BLK-049 | Preview (HITL gates, trajectory UI) |

## Action Required

1. Continue Tier 1 + 1.5 (panes + agent control)
2. Then Tier 2 (progressive disclosure + trust calibration)
3. Then Tier 3 (editors) — review specs now for planning
4. Then Tier 4 (tests) — review test list for planning
5. Acknowledge by replying to `mgmt/inbox/`

## Constraints

- ADEP brand palette locked (§9)
- Both dark and light mode from v1
- No anthropomorphism — agent is a tool
- Editors are full-page forms, not modals (too many fields)
- Definition Builder uses card selectors, not dropdowns (BLK-031)


## Resolution

Processed and completed under BLK-054 & BLK-055. Fixed progress bar count (5/6 = 83%), state-aware control buttons (Start/Pause/Resume/Stop/Rollback/Compact), run status badges, ADEP Blue (#00205C) sidebar styling, dark mode toggle, Pane 2 field cards & confidence badges, Pane 3 Electric Blue SVG bbox overlay & split sticky toolbar, token usage display (BLK-053), reusable UI component library (components/ui/), and 7-step Agent Definition Builder wizard (BLK-031).
