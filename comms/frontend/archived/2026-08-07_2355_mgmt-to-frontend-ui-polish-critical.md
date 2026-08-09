---
from: mgmt
to: frontend
subject: "URGENT: UI is not acceptable — 32 mistakes found, BLK-054 created"
date: 2026-08-07T23:55:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2335_mgmt-to-frontend-token-display-admin-panel
message-id: 2026-08-07_2355_mgmt-to-frontend-ui-polish-critical
---

## Status

Screenshots reviewed. The UI is not acceptable for Phase 3. There are
functional bugs, spec deviations, brand violations, and interaction
mistakes. **Stop new feature work** and fix these first.

A new bugfix item is created: **BLK-054 — UI Polish & Bugfix Sweep**.
It is high priority and **blocks Phase 3 sign-off**.

## Critical Bugs (stop everything and fix these first)

### 1. Field completion progress is wrong
- **Bug:** Pane 1 shows "0 / 6 Fields (0%)" but Pane 2 already shows
  5 extracted fields.
- **Fix:** 5/6 = 83%. Progress bar must be green and nearly full.
- **Where:** `Pane1AgentConsole.tsx`

### 2. "No active trace stream" while data exists
- **Bug:** Pane 1 says idle/no trace, but Pane 2 has results.
- **Fix:** If extraction data exists, show completed/final summary or
  the actual trace. Empty state only when no run started.
- **Where:** `Pane1AgentConsole.tsx`

### 3. Pause/Stop/Rollback visible while idle
- **Bug:** Run controls visible when run status is idle.
- **Fix:** Controls are state-aware. Hide when idle. Show Start Run
  instead.
- **Where:** `Pane1AgentConsole.tsx`

### 4. Resume button missing
- **Bug:** Only Pause shown. No Resume state swap.
- **Fix:** running → Pause. paused → Resume. idle → Start Run.
- **Where:** `Pane1AgentConsole.tsx`

## High Priority Visual Fixes

### 5. Sidebar color is wrong
- Current: bright royal blue
- Fix: LTTS Blue `#00205C` background, white text, Mobility Blue
  `#0071CE` active highlight with left border.

### 6. Dark mode toggle is broken
- Current: giant "N" over moon icon
- Fix: remove the "N". Use Lucide `Moon`/`Sun` with "Dark Mode" label.

### 7. Pane 1 header is overcrowded
- Current: tabs, buttons, progress, definition, upload all crushed.
- Fix: put controls in a sticky toolbar below header. Move definition
  selector and upload into Pane 1 body.

### 8. Tabs are inconsistent
- Current: Pane 1 uses underline tabs, Pane 2 uses pill buttons.
- Fix: standardize on one tab pattern across the app. Use pill tabs
  with active = Mobility Blue background + white text.

### 9. Field cards lack visual hierarchy
- Current: flat white boxes, inconsistent dark background on one field.
- Fix: clean card design: field name as muted label, value on light
  gray, confidence badge and actions right-aligned.

### 10. Confidence badges use wrong green
- Current: dark/forest green.
- Fix: S. Green `#4DB848`. Warning = Tech Yellow `#F2E500` with dark
  text. Failed = Coral `#F47C6D`.

### 11. "Grounding" link is unclear
- Current: tiny arrow next to text.
- Fix: `Show source` button with `MapPin` icon. Click → Pane 3 zooms
  to bbox with Electric Blue pulse.

### 12. Pane 3 toolbar cramped
- Current: page nav, zoom, and page counter squashed.
- Fix: page nav on left, zoom controls on right, divider background.

### 13. Bbox overlay too faint
- Current: light blue boxes.
- Fix: Electric Blue `#00B5E2`, 2px stroke, subtle glow. Active bbox
  pulses.

## High Priority UX / Spec Fixes

### 14. Definition Builder is a registry, not a wizard
- Current: shows read-only list of existing definition cards.
- Fix: implement the wizard from BLK-031 with 7 steps:
  Name → Skill card grid → Template card grid → Tool chips →
  System prompt → Max iterations → Review → Save.

### 15. Definition cards must have rich previews
- Current: plain gray boxes with small text.
- Fix: show skill name + tool chips, template name + field count,
  max cycles, description. Selected state = Mobility Blue border.

### 16. Skill Editor is a read-only card
- Current: one skill card with tools and a semantic prompt box.
- Fix: separate Registry (`/skills`) from Editor (`/skills/{id}/edit`).
  Editor is a full form: name, description, system prompt, tool
  preferences, probe order (sortable), invariants, failure actions,
  semantic checks toggle.

### 17. Tool chips wrong color
- Current: muted purple/gray.
- Fix: LTTS purple `#A27CC9` with white text.

### 18. Template Builder is a read-only table
- Current: table of fields with no edit, no drag-drop, no add.
- Fix: expandable field cards, drag-and-drop reorder, type badges,
  required toggle, confidence threshold slider, add field button,
  nested sub-fields.

### 19. Buttons inconsistent
- Current: primary/secondary/destructive pattern not clear.
- Fix:
  - Primary: solid Mobility Blue (Create, Save, Start)
  - Secondary: outline Mobility Blue (Upload, Compact)
  - Destructive: solid Coral (Stop, Reject)
  - Tertiary: ghost (Cancel, Back)

### 20. Progressive disclosure misimplemented
- Current: Summary/Detailed/Expert tabs.
- Fix: Level 1 default (status + progress + latest thought), Level 2
  click cycle to expand, Level 3 expert toggle in header shows raw
  JSON/token breakdown/attempted set.

## Brand/Design

### 21. Apply LTTS colors everywhere
- Sidebar: `#00205C`
- Primary: `#0071CE`
- Success: `#4DB848`
- Warning: `#F2E500` with dark text
- Error: `#F47C6D`
- Bbox: `#00B5E2`
- Tool chips: `#A27CC9`

### 22. Add run status pill
- Idle, Running (spinner + S. Green), Paused (Tech Yellow), Complete,
  Partial (Coral).

### 23. Independent scrollbars + sticky headers
- Each pane must scroll independently. Headers/toolbars sticky.

### 24. Reduce visual noise
- Use border OR shadow, not both. Less whitespace, better typography.

### 25. Add focus states
- 2px Electric Blue focus ring with 2px offset on all interactive
  elements.

## What to Stop and What to Do

### STOP:
- Skill Editor/Template Editor feature work until the read-only →
  editable conversion is done.
- Admin panel (BLK-052) until workbench is acceptable.
- New test writing (BLK-034) until the UI is stable.

### DO FIRST:
1. Fix critical bugs 1–4 (progress, idle state, controls)
2. Fix sidebar color + dark mode toggle
3. Fix Pane 1/Pane 2/Pane 3 visual hierarchy
4. Convert Definition Builder, Skill Editor, Template Builder from
   read-only views to proper builder UIs
5. Apply LTTS brand colors and focus states
6. Independent scrollbars + sticky headers
7. Regression test all screens in dark and light mode

## Full Spec

See `backlog/features/BLK-054_ui-polish-bugfix-sweep.md` for the
complete 32-item checklist with severity and file references.

## Action Required

1. Acknowledge receipt of this comms
2. Re-prioritize: stop new features, focus on BLK-054
3. Estimate time to fix the 4 critical bugs and the 10 high-priority
   visual/UX items
4. Report back on which items can be fixed this session
5. If any spec in BLK-031/029/030 is unclear, ask now

This is the highest-priority frontend work. Phase 3 sign-off is
blocked until BLK-054 is complete.


## Resolution

Processed and completed under BLK-054 & BLK-055. Fixed progress bar count (5/6 = 83%), state-aware control buttons (Start/Pause/Resume/Stop/Rollback/Compact), run status badges, LTTS Blue (#00205C) sidebar styling, dark mode toggle, Pane 2 field cards & confidence badges, Pane 3 Electric Blue SVG bbox overlay & split sticky toolbar, token usage display (BLK-053), reusable UI component library (components/ui/), and 7-step Agent Definition Builder wizard (BLK-031).
