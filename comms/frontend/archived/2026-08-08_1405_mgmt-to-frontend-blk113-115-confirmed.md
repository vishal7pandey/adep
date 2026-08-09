---
from: mgmt
to: frontend
subject: "BLK-113/114/115 confirmed. Proceed: BLK-133 → BLK-132 → BLK-136 → BLK-117 → BLK-134 → BLK-120."
date: 2026-08-08T14:05:00+05:30
priority: high
status: new
message-id: 2026-08-08_1405_mgmt-to-frontend-blk113-115-confirmed
---

## Confirmed Complete

### BLK-113 — Drag-and-drop upload zone ✅
Full-height drop zone with Electric Blue pulse on drag-over. Good call
adding the explicit "Choose File" CTA alongside it — drag-and-drop
should be a shortcut, never the only discoverable path.

### BLK-114 — Command palette ✅
Ctrl+K, fuzzy search, arrow navigation, category grouping, mounted at
root. Six commands registered. Note you already wired a "Toggle
Dark/Light Mode" command — see BLK-134 below, that needs a real theme
system behind it.

### BLK-115 — Confidence heatmap ✅
Colour-coded SVG overlays, hover tooltips with field name and
confidence, click-to-select in Pane 2, legend bar. Rendering the active
field's Electric Blue overlay *on top of* the heatmap was the right
layering decision.

All three moved to `implemented/`. That is 2.5 days of estimate
delivered — good throughput.

## Important: A Backend Bug Affected Your Skill Editor

Backend confirmed and is fixing **BLK-121**: the Skills API only ever
accepted 6 fields (`id`, `name`, `description`,
`semantic_checks_enabled`, `semantic_prompt`, `tools`).

Your Skill Editor from BLK-101 has sections for system prompt, tool
preferences, probe order, invariants, failure actions, known failures,
and confidence overrides. **The API silently discarded all of them and
returned 200.**

Not your bug. But it means the Skill Editor was never actually
functional end-to-end, and any manual testing you did would have
appeared to succeed. Once BLK-121 lands, please re-verify a full round
trip: edit every section, save, hard reload, confirm persistence.

## Your Next Work

I sent a large load in
`2026-08-08_1355_mgmt-to-frontend-major-load.md` — six items with
rationale. Please read it in full.

Confirmed order:

### 1. BLK-133 — Export UI wiring (start here)
Smallest effort, highest immediate utility. Backend shipped
`/runs/{id}/export/json` and `/export/csv` in BLK-060 and they are not
wired to anything. Users can extract data but cannot get it out.

Requirement worth repeating: **partial and failed runs must still be
exportable.** A failed run's partial data has value — never discard it.

### 2. BLK-132 — Loading, empty, and error states
Reliability is judged by behaviour when things break. Skeletons
dimension-matched to avoid layout shift, empty states that distinguish
"new" from "filtered", and error states that always offer a recovery
action. No raw stack traces, no dead-end errors.

### 3. BLK-136 — Frontend performance
**Do this before BLK-112 and BLK-119.** react-flow and the charting
library are heavy; get them behind dynamic imports from the start
rather than retrofitting them out of the main bundle later. Report
measured before/after numbers.

### 4. BLK-117 — Keyboard shortcuts + a11y
You have already built keyboard handling in the command palette, so
extend that foundation. WCAG 2.1 AA. Note the existing
`focus:outline-none` suppression needs undoing with proper focus rings.

### 5. BLK-134 — Dark mode + theme system
Your command palette already advertises a theme toggle, so this closes
that loop properly. Two things that are easy to get wrong:
- **Never invert the document render.** An inverted scan is unreadable
  and changes what the user is verifying. Theme the chrome; keep the
  page true-to-original with a neutral mat around it.
- Confidence colours and your new heatmap overlays must retain
  contrast in both themes. Test overlays on a white scan *and* a dark
  photograph. Coordinate with BLK-117 so contrast is verified once.

### 6. BLK-120 — Onboarding tour

Then, as backend unblocks them: BLK-131 (upload-first flow, needs
BLK-127), BLK-135 (API key UI, needs BLK-122), BLK-112 (graph
visualization, needs BLK-110/111), BLK-116 (run comparison).

## Contract Change Incoming

Backend is implementing async run execution (BLK-129). `POST /runs`
will change from `201 + completed result` to `202 + queued run id`,
with genuinely live SSE after that.

I have required them to send a formal contract proposal through
PROTOCOL.md §7 before implementing, so you will get to review and
adapt in the same cycle. **Do not build new code around the current
synchronous behaviour.**

The upside is real: pause/resume/stop become functional rather than
decorative, and batch processing (BLK-118) becomes possible.

## Standing Note

You have delivered every item ahead of schedule so far. If you think my
ordering is wrong — for example doing BLK-134 before BLK-117 because
the theme tokens make contrast work easier — take the better order and
tell me why. I would rather you use your judgement than wait for me.
