---
id: BLK-054
type: bugfix
title: "UI Polish & Bugfix Sweep — workbench, definition builder, skill/template editors"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T23:50:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-026, BLK-028, BLK-029, BLK-030, BLK-031, BLK-033, BLK-038]
tags: [frontend, ui, design, bugfix, polish, audit, adep]
---

## Description

Audit of the workbench, definition builder, skill editor, and template
schema builder reveals multiple functional bugs, spec deviations, visual
inconsistencies, and ADEP brand violations. This is a catch-all polish
sweep that must be completed before Phase 3 sign-off.

## Functional Bugs (Critical)

### 1. Field completion progress is wrong [BLK-028]
- **Bug:** Pane 1 shows "0 / 6 Fields (0%)" while Pane 2 already
  displays 5 extracted fields (`vendor_name`, `invoice_number`,
  `invoice_date`, `tax_amount`, `total_amount`) with high confidence.
- **Fix:** Progress must reflect actual extracted field count.
  5/6 fields = 83%, not 0%. Progress bar must be green, not empty.
- **Severity:** Critical — broken core status indicator.

### 2. "No active trace stream" contradicts extracted data [BLK-028]
- **Bug:** Pane 1 says "No active trace stream" / idle, but Pane 2
  already has extraction results.
- **Fix:** If extraction data exists, the run has already executed.
  Pane 1 should either show the completed trace, the final result
  summary, or a "Run completed" status. Idle empty-state only when
  no run has been started.

### 3. Pause/Stop controls visible while status claims idle [BLK-046]
- **Bug:** Pause, Stop, Rollback, Compact buttons are present while
  the pane says idle / no trace.
- **Fix:** Controls must be state-aware. Show only when `status` is
  `running` or `paused`. When run is complete/idle, show
  "Start Run" / "Re-run" instead.

### 4. Resume button missing [BLK-046]
- **Bug:** Only Pause is shown; no Resume button.
- **Fix:** When paused, Pause must swap to Resume. When running, show
  Pause. Always show Stop (visible, Coral, disabled when not running).

## Layout & Visual Mistakes (High)

### 5. Sidebar color is wrong [BLK-026]
- **Bug:** Sidebar is a bright royal blue, not ADEP Blue `#00205C`.
- **Fix:** Use `#00205C` background, white text, Mobility Blue `#0071CE`
  for active item highlight.

### 6. Active sidebar item uses wrong highlight [BLK-026]
- **Bug:** Active nav item is a brighter saturated blue, not the
  Mobility Blue + subtle left-border/accent pattern.
- **Fix:** Active state: left border 3px Mobility Blue, background
  `rgba(0, 113, 206, 0.15)`, white text.

### 7. Dark mode toggle is broken [BLK-026]
- **Bug:** The bottom-left dark mode control shows a giant letter "N"
  on top of the moon icon. Meaningless and visually broken.
- **Fix:** Remove the "N". Use only a Lucide `Moon` / `Sun` toggle
  button with label "Dark Mode".

### 8. Pane 1 header is crowded [BLK-028]
- **Bug:** Agent name, 3 tabs, 4 control buttons, definition label,
  upload button, progress bar all compete for space.
- **Fix:**
  - Move controls (Pause/Stop/Rollback/Compact) into a dedicated
    sticky toolbar below the header.
  - Keep tabs as a small segmented control, not full-size buttons.
  - Progress bar below the toolbar, not inline.
  - Definition selector and Upload File should be in Pane 1 body,
    not the header.

### 9. Tab styling is inconsistent [BLK-028, BLK-033]
- **Bug:** Pane 1 tabs (Summary/Detailed/Expert) use underlines.
  Pane 2 tabs (Field Cards/JSON View) use pill buttons. Two different
  patterns in the same app.
- **Fix:** Standardize on a single tab style across the app. Use
  subtle pills with active state in Mobility Blue background + white
  text, inactive in gray outline.

### 10. Pane 2 field cards lack visual hierarchy [BLK-033]
- **Bug:** All field values sit on a flat white background with a
  thin border. The `vendor_name` value appears to have a dark
  background while others are light — inconsistent.
- **Fix:** Use a clean card design: light gray (#F9FAFB) value box,
  field name as muted label above, confidence badge and actions to
  the right. Selected/hovered field uses Electric Blue glow on the
  bbox in Pane 3.

### 11. Confidence badges use wrong green [BLK-033]
- **Bug:** Green badges look slightly dark/forest, not S. Green
  `#4DB848`.
- **Fix:** Use `#4DB848` for verified/high confidence. Use Tech Yellow
  `#F2E500` with dark text for medium. Use Coral `#F47C6D` for failed/low.

### 12. "Grounding" link is unclear [BLK-033]
- **Bug:** "Grounding" text with a tiny arrow icon. Not obvious it
  jumps to the bbox in Pane 3.
- **Fix:** Replace with `Locate` or `Show source` button with
  `MapPin` icon. On click, Pane 3 scrolls/zooms to the bbox and
  highlights it with Electric Blue pulse.

### 13. Pane 3 toolbar is cramped [BLK-038]
- **Bug:** Page nav arrows, page counter, and zoom controls are
  squashed together.
- **Fix:** Separate into groups:
  - Left: page navigation with `<` `Page 1 of 2` `>`
  - Right: zoom controls (`-` `50%` `+`, rotate, fit-to-width)
  - Add a visible divider or background strip for the sticky toolbar.

### 14. Zoom percentage hard to read [BLK-038]
- **Bug:** Zoom `50%` is tiny and adjacent to the page nav.
- **Fix:** Larger, fixed-width box for zoom value, clearly separated
  from page controls.

### 15. Bbox overlay on invoice is barely visible [BLK-038]
- **Bug:** The blue boxes around the table are light and easy to miss.
- **Fix:** Use Electric Blue `#00B5E2` with 2px stroke and subtle
  glow. Active/selected bbox: pulse animation with stronger glow.

### 16. Table data display has OCR artifact [BLK-038]
- **Bug:** Description cell shows "AI Extraction Engine Service Token Pack"
  and the amount cell shows "$125.00 - $1,250.00" with a hyphen.
- **Fix:** This is likely an extraction/OCR error in the sample, but
  the UI should not render it as plain text without flagging. If a
  value contains suspicious characters (like hyphen in number), show
  a warning icon or red underline. (May be data issue, not UI issue.)

## UX/Interaction Mistakes (High)

### 17. Agent Definition Builder shows registry, not wizard [BLK-031]
- **Bug:** Screen shows a list of existing definition cards with
  read-only metadata. This is the **Registry** view, not the builder.
  Where is the wizard for composing a new definition?
- **Fix:** Implement the wizard BLK-031 specifies:
  1. Name + description
  2. Skill card grid (with rich previews, tools, semantic checks)
  3. Template card grid (with field count + preview)
  4. Tool multi-select chips
  5. System prompt override textarea
  6. Max iterations input
  7. Review + save
  The **list of existing definitions** should be a separate
  `/definitions` registry page or a pre-step in the builder, not the
  builder itself.

### 18. Definition Builder card design does not match spec [BLK-031]
- **Bug:** Existing definition cards are just gray boxes with small
  text. No skill/template thumbnails, no tool chips, no field count.
- **Fix:** Per BLK-031, skill/template/definition cards must show
  visual previews. Existing definition cards should show: definition
  name, skill name + tool chips, template name + field count, max
  cycles, description. Clicking "Build Definition" opens the wizard.

### 19. Skill Editor is a registry card, not an editor [BLK-029]
- **Bug:** Screen titled "Skill Editor & Registry" shows one read-only
  skill card with tools and a semantic prompt. No editable form.
- **Fix:** Separate Registry (`/skills` list view) from Editor
  (`/skills/{id}/edit` full-page form). Editor must have all fields:
  name, description, system prompt, tool preferences, probe order
  (sortable), invariants (dynamic list), failure actions (dynamic
  list), semantic checks toggle, semantic prompt.

### 20. Tool chips use wrong color [BLK-029]
- **Bug:** Tool chips `paddle_ocr`, `crop_image`, `outcome_validator`
  use a muted purple/gray.
- **Fix:** Use ADEP purple `#A27CC9` for tool call chips, with white
  text and proper padding.

### 21. Template Schema Builder is a static table, not a builder [BLK-030]
- **Bug:** Screen shows a read-only table of fields. No add/edit,
  no drag-and-drop reorder, no nested sub-fields, no confidence
  threshold controls.
- **Fix:** Implement the schema builder from BLK-030:
  - Editable form for each field (expandable card)
  - Drag-and-drop reorder
  - Type badges (string/date/number/list/object)
  - Required toggle
  - Confidence threshold slider or number input
  - "Add Field" button
  - Nested sub-fields for list/object types
  - Description textarea

### 22. Threshold column does not use color [BLK-030]
- **Bug:** Confidence thresholds are plain text. 80%, 85%, 70%, etc.
  No visual cue when a field is required vs optional.
- **Fix:** Use color-coded badges: green ≥80%, yellow 60–79%, red <60%.
  Use a toggle pill for Required (Yes/No).

### 23. Buttons are inconsistent across screens [BLK-026]
- **Bug:** "Build Definition" is a primary blue button. "New Skill"
  and "New Template" also primary blue. But "Upload File" in Pane 1
  is an outline. "Compact" is an outline. No consistent pattern for
  primary vs secondary vs destructive.
- **Fix:**
  - Primary: solid Mobility Blue, white text (Create, Save, Start Run)
  - Secondary: outline Mobility Blue (Upload, Compact)
  - Destructive: solid Coral (Stop, Reject)
  - Tertiary: ghost (Cancel, Back)

### 24. Missing "Expert Mode" toggle location [BLK-045]
- **Bug:** Pane 1 has Summary/Detailed/Expert tabs, but these are
  not the same as the 3-tier progressive disclosure spec.
- **Fix:** Replace with:
  - Level 1 (default): status + progress + latest thought
  - Level 2 (expand per cycle): click a cycle to expand tool call
  - Level 3 (expert mode): toggle in header or sidebar, shows raw
    JSON, token breakdown, attempted set, compaction summary

## Brand/Design Violations (Medium)

### 25. Typography lacks hierarchy [BLK-026]
- **Bug:** Screen titles, section labels, and body text all feel
  similar in weight/size. Hard to scan.
- **Fix:** Use clear hierarchy: page title 20px/600, section label
  14px/600 uppercase/muted, body 14px/400.

### 26. ADEP brand colors are not applied [BLK-026]
- **Bug:** App uses a generic blue/shadcn default palette, not ADEP.
- **Fix:** Apply ADEP palette CSS variables:
  - Sidebar: `#00205C`
  - Primary: `#0071CE`
  - Success: `#4DB848`
  - Warning: `#F2E500` with dark text
  - Error: `#F47C6D`
  - Bbox highlight: `#00B5E2`
  - Tool chips: `#A27CC9`

### 27. Empty states are visually unbalanced [BLK-028]
- **Bug:** "No active trace stream" icon and text are floating in
  the middle with too much whitespace above and too little context.
- **Fix:** Center the empty state, add a clear CTA ("Select a
  definition and upload a document to start"), and style the helper
  text with muted color.

### 28. No visible status for running/paused/completed [BLK-028]
- **Bug:** No status chip or color indicating run state.
- **Fix:** Add a status pill in Pane 1 header:
  - Running: `Loader2` spinner + S. Green
  - Paused: Pause icon + Tech Yellow
  - Complete: Check + S. Green
  - Partial: Alert triangle + Coral
  - Idle: Dot + neutral gray

## Accessibility & Polish (Medium)

### 29. Missing focus states [BLK-026]
- **Bug:** Buttons, inputs, and cards likely have minimal focus rings.
- **Fix:** Add 2px Electric Blue focus ring with 2px offset for all
  interactive elements.

### 30. Too many borders and shadows [BLK-026]
- **Bug:** Cards have both borders and shadows, creating visual noise.
- **Fix:** Use subtle borders OR shadows, not both. Prefer clean
  1px borders with 0–1px soft shadow on hover only.

### 31. Pane 1, 2, 3 need independent scrollbars [BLK-028, 033, 038]
- **Bug:** Screenshots show individual panes but scrollbars are not
  clearly visible. Each pane must have its own `overflow-y-auto`
  with a styled custom scrollbar.
- **Fix:** Ensure each pane scrolls independently with sticky headers.

### 32. Missing sticky headers in panes [BLK-028, 033, 038]
- **Bug:** Pane 2 and Pane 3 content may scroll under the tab bar,
  causing context loss.
- **Fix:** Header/toolbar must be `sticky top-0` with opaque
  background in both dark and light mode.

## Acceptance Criteria (for BLK-054)

- [ ] Fix all functional bugs (1–4)
- [ ] Fix all visual/brand mistakes (5–16)
- [ ] Implement correct UX for Definition Builder, Skill Editor, Template Builder (17–22)
- [ ] Button hierarchy consistent across all screens (23)
- [ ] ADEP brand colors applied everywhere (26)
- [ ] Progress/status indicators accurate and color-coded (1, 28)
- [ ] Independent scrollbars + sticky headers in all 3 panes (31–32)
- [ ] Typography hierarchy and reduced visual noise (25, 30)
- [ ] Accessibility: focus states, sufficient contrast (29)
- [ ] Regression test: workbench, editors, dark/light mode

## Notes

- This is a **polish sweep**, not a rewrite. Many features are
  partially correct but need refinement.
- Severity ranked: Critical (4) → High (18) → Medium (10)
- Must be completed before Phase 3 sign-off.
- Frontend team should treat this as the highest-priority Phase 3
  item once the functional pane bugs (1–4) are fixed.
