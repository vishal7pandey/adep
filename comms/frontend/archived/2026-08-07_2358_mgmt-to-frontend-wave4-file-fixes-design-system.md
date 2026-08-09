---
from: mgmt
to: frontend
subject: "Wave 4 — specific file-by-file UI fixes, design system, component library"
date: 2026-08-07T23:58:00+05:30
priority: high
status: closed
in-reply-to: 2026-08-07_2355_mgmt-to-frontend-ui-polish-critical
message-id: 2026-08-07_2358_mgmt-to-frontend-wave4-file-fixes-design-system
---

## Context

BLK-054 covers the 32 mistakes. This message breaks that into specific
files and assigns the order of work. Stop new features. Focus on these
fixes.

## File-by-File Fix List

### 1. `components/workbench/WorkbenchLayout.tsx` [BLK-026, BLK-054]

**Problems:**
- Sidebar wrong color (bright blue)
- Active nav item wrong highlight
- Dark mode toggle broken (giant "N")
- Panes may not have independent scroll areas

**Fixes:**
- [ ] Sidebar background: `#00205C` (ADEP Blue)
- [ ] Active nav item: left border 3px `#0071CE`, background
      `rgba(0,113,206,0.15)`, white text
- [ ] Inactive nav: white text at 80% opacity, hover at 100%
- [ ] Dark mode toggle: remove "N", use Lucide `Moon`/`Sun`, label
      "Dark Mode"
- [ ] Add padding and consistent spacing in sidebar
- [ ] Ensure 3 panes each have `h-full overflow-y-auto` with sticky
      headers inside

### 2. `components/workbench/Pane1AgentConsole.tsx` [BLK-028, BLK-046, BLK-054]

**Critical bugs:**
- [ ] Progress bar reads 0/6 when 5/6 fields extracted
- [ ] Empty state shown when run data exists
- [ ] Pause/Stop/Rollback shown when idle
- [ ] Resume button missing

**Layout fixes:**
- [ ] Split header into 3 rows:
  - Row 1: status pill + agent name
  - Row 2: control toolbar (Pause/Resume, Stop, Rollback, Compact)
  - Row 3: definition selector + upload + progress bar
- [ ] Progress bar uses correct count from `ExtractionRun.fields`
- [ ] Add run status pill: idle, running (spinner), paused,
      complete, partial, error
- [ ] State-aware controls:
  - `idle`: show "Start Run" button, hide Pause/Stop/Rollback
  - `running`: show Pause, Stop, Rollback, Compact
  - `paused`: show Resume, Stop, Rollback
  - `complete`: show "Re-run", hide Stop
- [ ] Rollback opens a dropdown with cycle list after click
- [ ] Compact button: outline Mobility Blue, spinner when compacting
- [ ] Tabs Summary/Detailed/Expert converted to progressive
      disclosure: Summary (default), Detailed (expand cycles), Expert
      (toggle raw JSON/attempted/token breakdown)
- [ ] Empty state: better icon, clearer CTA, centered

### 3. `components/workbench/Pane2ExtractedData.tsx` [BLK-033, BLK-054]

**Fixes:**
- [ ] Field Cards tab and JSON View tab style unified with Pane 1
      (pill tabs)
- [ ] Sticky header: tabs + export buttons
- [ ] Each field card:
  - Field name as small muted label
  - Value in light gray `#F9FAFB` box
  - Confidence badge right-aligned
  - "Show source" button with `MapPin` icon
  - Edit icon for human-in-the-loop
- [ ] Confidence badge colors: `#4DB848` ≥80%, `#F2E500` 60-79%
      (dark text), `#F47C6D` <60%
- [ ] Selected field: card has Electric Blue border, Pane 3 bbox
      pulses
- [ ] Table view for list fields
- [ ] Gap report summary shown when partial
- [ ] Export JSON/CSV buttons in sticky header

### 4. `components/workbench/Pane3DocumentViewer.tsx` [BLK-038, BLK-054]

**Fixes:**
- [ ] Sticky toolbar split into 2 groups:
  - Left: `< Page 1 of 2 >` with proper button sizes
  - Right: `- 50% +` zoom, rotate, fit-to-width
- [ ] Toolbar background: light/dark subtle strip, not transparent
- [ ] PDF rendering via `react-pdf`
- [ ] Page navigation auto-jumps when field clicked in Pane 2
      (uses `grounding.page`)
- [ ] SVG overlay for bboxes (not canvas)
- [ ] Bbox default: Electric Blue `#00B5E2`, 2px stroke, subtle glow
- [ ] Active bbox: pulse animation, stronger glow
- [ ] Independent vertical + horizontal scrollbars
- [ ] Zoomed document scrolls, not page

### 5. `components/agent-definitions/AgentDefinitionBuilder.tsx` [BLK-031, BLK-054]

**Current:** read-only registry of cards.
**Fix:** proper 7-step wizard:
1. Name + description
2. Skill card grid (rich previews: tools, semantic badge)
3. Template card grid (field count, preview fields)
4. Tool multi-select chips
5. System prompt override textarea
6. Max iterations number input
7. Review summary + save

**Also keep:** separate registry list view at `/definitions` (read-only
grid of existing definition cards).

### 6. `components/skills/SkillEditor.tsx` + `SkillsRegistry.tsx` [BLK-029, BLK-054]

**Current:** one read-only skill card.
**Fix:**
- `SkillsRegistry.tsx`: list of skill cards with name,
  description, tool chips, "Edit" button
- `SkillEditor.tsx`: full-page form with sections:
  - Basics: name, description, system prompt
  - Tools: multi-select chips
  - Probe Order: sortable list
  - Invariants: dynamic list (type + params)
  - Failure Actions: dynamic list (condition + action)
  - Semantic Checks: toggle + prompt textarea
- Tool chips use `#A27CC9`

### 7. `components/templates/TemplateEditor.tsx` + `TemplatesRegistry.tsx` [BLK-030, BLK-054]

**Current:** read-only table.
**Fix:**
- `TemplatesRegistry.tsx`: list of template cards
- `TemplateEditor.tsx`: full-page builder:
  - Field cards (expandable)
  - Drag-and-drop reorder
  - Type badge per field
  - Required toggle
  - Confidence threshold slider or number input
  - Add Field / Add Sub-Field buttons
  - Description textarea
- Threshold badges color-coded by value

### 8. `lib/sse.ts` [BLK-046, BLK-050, BLK-054]

**Fixes:**
- [ ] Add `SSEPausedEvent`, `SSEResumedEvent`, `SSEStoppedEvent`,
      `SSERolledBackEvent`
- [ ] Add `SSETokenUsageEvent`, `SSEBudgetWarningEvent`,
      `SSEBudgetExceededEvent`
- [ ] Add callbacks: `onPaused`, `onResumed`, `onStopped`, `onRolledBack`
- [ ] Add callbacks: `onTokenUsage`, `onBudgetWarning`, `onBudgetExceeded`

### 9. `lib/api.ts` [BLK-046, BLK-050, BLK-054]

**Fixes:**
- [ ] Add `pauseRun`, `resumeRun`, `stopRun`, `rollbackRun`
- [ ] Add `getBudget`, `getAdminStats`, `getAdminConsumption`,
      `getAdminRuns`, `getAdminExpensiveRuns`, `getAdminSettings`,
      `updateAdminSettings`

### 10. `app/globals.css` or `tailwind.config.ts` [BLK-026, BLK-054]

**Fixes:**
- [ ] Add ADEP CSS variables:
  ```css
  --adep-blue: #00205C;
  --mobility-blue: #0071CE;
  --s-green: #4DB848;
  --tech-yellow: #F2E500;
  --coral: #F47C6D;
  --electric-blue: #00B5E2;
  --adep-purple: #A27CC9;
  --neutral-dark: #101820;
  --neutral-light: #E1E1E1;
  ```
- [ ] Button variants: primary, secondary, destructive, tertiary
- [ ] Focus ring: 2px `var(--electric-blue)`, 2px offset
- [ ] Custom scrollbar styling for panes

## New Component Library Requirement

To prevent future inconsistency, create a small internal component
library in `components/ui/`:

| Component | Use |
|-----------|-----|
| `AdeButton` | All buttons — enforces variants + colors |
| `AdeCard` | Cards — consistent border/shadow/padding |
| `AdeBadge` | Confidence, status, tool chips |
| `AdePillTabs` | All tab groups |
| `AdeProgressBar` | Field completion, budget bars |
| `AdeEmptyState` | Empty pane states |
| `AdeTooltip` | Tooltips with grounding info |

**This is not a separate task yet** — do it opportunistically while
fixing BLK-054. If it grows beyond a few files, we’ll split it into its
own backlog item.

## Order of Work

1. **Day 1:** Fix critical bugs 1–4 in Pane 1 (progress, controls, state)
2. **Day 1:** Fix sidebar color + dark mode toggle
3. **Day 2:** Pane 2 field cards + confidence badges
4. **Day 2:** Pane 3 toolbar + bbox styling
5. **Day 3:** Convert Skill Editor + Template Builder to editable forms
6. **Day 4:** Convert Definition Builder to wizard
7. **Day 5:** Component library extraction + dark/light regression

## Definition of Done for BLK-054

- [ ] All 4 critical bugs fixed and verified
- [ ] ADEP brand colors applied to every screen
- [ ] All 3 panes have independent scroll + sticky headers
- [ ] Editors are editable, not read-only
- [ ] Button hierarchy consistent
- [ ] Focus states visible
- [ ] Dark/light mode tested on all 4 screens

## Action Required

1. Acknowledge this file-by-file plan
2. Start with Pane 1 critical bugs (Day 1)
3. Report back after Day 1 fixes with new screenshots
4. Do **not** start BLK-045, BLK-048, BLK-052, or BLK-053 until
   BLK-054 is done


## Resolution

Processed and completed under BLK-054 & BLK-055. Fixed progress bar count (5/6 = 83%), state-aware control buttons (Start/Pause/Resume/Stop/Rollback/Compact), run status badges, ADEP Blue (#00205C) sidebar styling, dark mode toggle, Pane 2 field cards & confidence badges, Pane 3 Electric Blue SVG bbox overlay & split sticky toolbar, token usage display (BLK-053), reusable UI component library (components/ui/), and 7-step Agent Definition Builder wizard (BLK-031).
