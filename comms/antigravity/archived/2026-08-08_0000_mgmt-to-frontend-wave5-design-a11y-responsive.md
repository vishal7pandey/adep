---
from: mgmt
to: frontend
subject: "Wave 5 — design system, responsive, accessibility, error boundaries"
date: 2026-08-08T00:00:00+05:30
priority: medium
status: closed
in-reply-to: 2026-08-07_2358_mgmt-to-frontend-wave4-file-fixes-design-system
message-id: 2026-08-08_0000_mgmt-to-frontend-wave5-design-a11y-responsive
---

## Context

UI fixes (BLK-054) and design system work are the highest priority.
These next 4 items are for after BLK-054 and BLK-055 are done.
They ensure the frontend is production-ready.

## Wave 5 Tasks (Phase 3/4, after BLK-054 + BLK-055)

### BLK-055 — Frontend Design System / Component Library (HIGH, Phase 3)

**What:** Build reusable `components/ui/` components enforcing ADEP
design tokens.

**Components:**
- `AdeButton` (primary, secondary, destructive, tertiary, icon)
- `AdeCard` (padding, border, shadow, hover, selected)
- `AdeBadge` (verified, medium, failed, info, tool, neutral)
- `AdePillTabs` (all tab groups)
- `AdeProgressBar` (field completion, budget)
- `AdeEmptyState` (idle/empty panes)
- `AdeTooltip` (confidence, grounding, token info)
- `AdeDialog` (modals)
- `AdeInput`, `AdeSelect`, `AdeToggle`, `AdeSlider`, `AdeAccordion`, `AdeScrollArea`

**Order:** Start this immediately after the Day 2 fixes in BLK-054.
Replace ad-hoc components as you fix the rest of the UI. Use the
component library going forward.

### BLK-056 — Responsive & Mobile Layout (MEDIUM, Phase 4)

**What:** Make workbench and admin usable on tablet and phone.

**Breakpoints:**
- Desktop (≥1280px): 3-pane grid
- Tablet (768–1279px): 2-pane + document drawer
- Phone (<768px): single pane + bottom tab bar

**Admin panel:**
- Stat cards: 4 → 2 → 1
- Chart scales down
- Tables convert to cards on phone

**Do not start until BLK-054 + BLK-055 are done.**

### BLK-057 — Accessibility (a11y) Audit & WCAG 2.1 AA (MEDIUM, Phase 4)

**What:** Make the app accessible to keyboard and screen-reader users.

**Key work:**
- Keyboard navigation for all controls
- Visible focus rings (2px Electric Blue)
- ARIA labels on icon buttons
- Heading hierarchy (h1 → h2 → h3)
- ARIA live regions for SSE updates
- Color contrast ≥ 4.5:1
- `prefers-reduced-motion` support
- Landmark regions (`main`, `nav`, `aside`)

**Tools:** axe DevTools, Lighthouse, manual screen-reader test.

**Do not start until BLK-054 + BLK-055 are done.**

### BLK-058 — Error Boundaries & Crash Reporting (MEDIUM, Phase 4)

**What:** Prevent silent crashes and show user-facing error states.

**Key work:**
- Global error boundary
- Pane-level error boundaries
- Structured `APIError` handling
- SSE auto-retry with exponential backoff
- Inline form validation errors
- 404 and generic error pages
- No external crash service in v1

**Do not start until editors are implemented.**

## Updated Pipeline

| Wave | Items | Phase | Status |
|------|-------|-------|--------|
| 1 | BLK-054 UI fixes | 3 | **In progress, top priority** |
| 2 | BLK-055 Design system | 3 | Start after Day 2 of BLK-054 |
| 3 | BLK-028, BLK-033, BLK-038 finishes | 3 | Subsumed into BLK-054 |
| 4 | BLK-045, BLK-048, BLK-053 (UX heuristics) | 3 | After BLK-054/055 |
| 5 | BLK-029, BLK-030, BLK-031 (editors) | 3 | After BLK-054/055 |
| 6 | BLK-034 (tests) | 3 | After editors done |
| 7 | BLK-056, BLK-057, BLK-058 | 4 | After Phase 3 sign-off |
| 8 | BLK-052 (admin panel) | 4 | After token tracking backend |

## Action Required

1. Finish BLK-054 critical bugs first
2. Start BLK-055 in parallel with the rest of BLK-054
3. Keep BLK-056, BLK-057, BLK-058 on the radar but don't start yet
4. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Processed and completed under BLK-054 & BLK-055. Fixed progress bar count (5/6 = 83%), state-aware control buttons (Start/Pause/Resume/Stop/Rollback/Compact), run status badges, ADEP Blue (#00205C) sidebar styling, dark mode toggle, Pane 2 field cards & confidence badges, Pane 3 Electric Blue SVG bbox overlay & split sticky toolbar, token usage display (BLK-053), reusable UI component library (components/ui/), and 7-step Agent Definition Builder wizard (BLK-031).
