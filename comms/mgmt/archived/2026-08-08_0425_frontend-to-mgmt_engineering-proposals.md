---
from: frontend
to: mgmt
subject: "Frontend Engineering Proposals â€” 8 UX/Architecture Ideas for ADEP Workbench"
date: 2026-08-08T04:25:00+05:30
priority: medium
status: closed
message-id: 2026-08-08_0425_frontend-to-mgmt_engineering-proposals
---

## Context

After implementing BLK-026 through BLK-112 and building out the full
3-pane workbench, progressive layout, session manager, skill editor
redesign, and all stabilization fixes â€” I have observations on what's
missing, what's friction, and what would make this platform genuinely
competitive. These are unsolicited proposals from the frontend team.

---

## Proposal 1: Command Palette (âŒ˜K / Ctrl+K)

**Problem:** Navigation requires mouse clicks through sidebar links.
Power users extracting dozens of documents per day need faster access.

**Solution:** A global command palette (like VS Code, Linear, Notion)
triggered by `Ctrl+K` / `âŒ˜K`:
- "New session" â†’ instant new extraction
- "Open run-001" â†’ jump to specific run
- "Switch to Invoice Extractor" â†’ change agent definition
- "Export results" â†’ trigger JSON/CSV export
- "Toggle dark mode"
- Fuzzy search across sessions, agents, skills, templates

**Effort:** ~1 day. No backend dependency. Pure frontend.

**Impact:** Makes the platform feel like a professional tool, not a
web form. Every competitive SaaS product has this now.

---

## Proposal 2: Drag-and-Drop Document Upload Zone

**Problem:** The current upload is a small dashed-border button with
a hidden file input. Users don't immediately see where to drop files.
In the `chat` phase, the entire Pane 1 is mostly empty space showing
"Upload a document to begin" â€” but you can't drag a file onto it.

**Solution:** Make the entire empty state area a drop zone:
- Full-height dashed border on drag-enter with "Drop your document
  here" overlay
- Animate the border with Electric Blue pulse on drag-over
- Accept `.pdf`, `.png`, `.jpg`, `.tiff`
- Show file preview thumbnail after drop
- Support multi-file drop for batch queuing (ties into Proposal 5)

**Effort:** ~0.5 day. No backend dependency.

**Impact:** This is table-stakes UX for any document processing tool.
Removes friction from the single most important user action.

---

## Proposal 3: Confidence Heatmap Overlay in Document Viewer

**Problem:** Pane 3 currently shows a single Electric Blue bounding
box for the active field. When the extraction completes, there's no
way to visually scan the entire document for low-confidence regions.

**Solution:** Add a "Confidence Overlay" toggle in the Pane 3 toolbar:
- When enabled, render semi-transparent colored rectangles over every
  extracted field's bounding box
- Color-coded: Green (>0.9), Yellow (0.7-0.9), Red (<0.7)
- Opacity proportional to confidence (low confidence = more opaque,
  more visible)
- Click any overlay rectangle â†’ selects that field in Pane 2 and
  scrolls to its card

**Effort:** ~1 day. No backend dependency â€” uses existing bbox data
from `ExtractedField[]`.

**Impact:** Transforms the document viewer from a passive display into
an active diagnostic tool. Users can instantly spot where the agent
struggled. This is the kind of feature that makes demos land.

---

## Proposal 4: Side-by-Side Run Comparison

**Problem:** When a user re-runs extraction with a different agent
definition or after editing a skill, there's no way to compare
results. They have to manually remember what changed.

**Solution:** A "Compare Runs" view accessible from the session list:
- Select 2 runs from the sidebar â†’ opens a diff view
- Field-by-field comparison table:
  - Field name | Run A value | Run B value | Î” confidence
  - Green highlight for improvements, Red for regressions
- Summary stats: total confidence delta, fields changed, new fields
  found/lost
- Side-by-side document viewer showing both bbox sets

**Effort:** ~2 days. No backend dependency â€” works with existing
`ExtractionRun` data from `/runs/{id}`.

**Impact:** Critical for iterative skill tuning. Without this, users
are flying blind when optimizing their extraction agents.

---

## Proposal 5: Batch Processing Queue

**Problem:** Current UX is one-document-at-a-time. Real enterprise
users have 500 invoices to process. They need to upload a folder and
walk away.

**Solution:** A batch upload panel accessible from the sidebar:
- Drag-drop multiple files or select a folder
- Queue visualization: file list with status (pending, running,
  completed, failed)
- Progress bar showing N/M documents processed
- Auto-start next document when current completes
- Summary report at end: success rate, avg confidence, failures list
- "Export All Results" button (ZIP of JSON/CSV per document)

**Effort:** ~3 days. Requires backend support for queue management.
Frontend can build the UI with mock data first.

**Backend dependency:** Need a `POST /runs/batch` endpoint and
progress SSE events per document.

**Impact:** This is the feature that separates a demo from a product.
No enterprise customer will adopt one-at-a-time extraction.

---

## Proposal 6: Keyboard Shortcuts & Accessibility (a11y)

**Problem:** Zero keyboard navigation support. No ARIA labels. No
focus management. Screen readers can't use this application.

**Solution:**
- `Escape` â†’ close modals, dropdowns, wizard
- `Enter` â†’ confirm/submit in focused context
- `Tab` navigation through all interactive elements
- `Arrow keys` for cycling through field cards in Pane 2
- `1/2/3` â†’ switch disclosure levels (Summary/Detailed/Expert)
- `Space` â†’ pause/resume active run
- ARIA labels on all buttons, badges, cards
- Focus rings on interactive elements (currently suppressed by
  `focus:outline-none`)
- Skip navigation link for screen readers
- Keyboard shortcut help modal (`?` key)

**Effort:** ~2 days. No backend dependency.

**Impact:** Accessibility is not optional â€” it's a legal requirement
in many enterprise contexts (WCAG 2.1 AA). Also makes the app faster
for power users.

---

## Proposal 7: Run Analytics Dashboard

**Problem:** No visibility into extraction performance over time.
Users can't answer: "Is my agent getting better? How much am I
spending? Which document types fail most?"

**Solution:** A `/analytics` page with:
- **Extraction success rate** over time (line chart)
- **Average confidence** per field per agent (bar chart)
- **Cost per document** trend (line chart with token/$ breakdown)
- **Processing time** distribution (histogram)
- **Failure heatmap** â€” which fields fail most across all runs
- **Agent leaderboard** â€” compare performance across agent definitions
- Date range picker, agent filter, document type filter

**Effort:** ~3 days for frontend. Requires backend analytics endpoints.

**Backend dependency:** Need aggregated metrics API â€” could be
computed client-side from `/runs` history for v1.

**Impact:** This turns the platform into a self-improving system.
Without analytics, users can't measure progress. What gets measured
gets improved.

---

## Proposal 8: Animated Onboarding Tour

**Problem:** New users land on a blank page with "Upload a document
to begin" and no idea what an agent definition is, what a skill does,
or how the three-pane layout works.

**Solution:** First-time user onboarding flow:
- Step 1: "Welcome to ADEP" overlay â†’ explains the platform purpose
- Step 2: Highlight sidebar â†’ "Choose or build an extraction agent"
- Step 3: Highlight upload button â†’ "Upload your document here"
- Step 4: Demo run plays automatically with sample invoice
- Step 5: Highlight Pane 2 â†’ "See extracted data appear in real-time"
- Step 6: Highlight Pane 3 â†’ "Click any field to see where it was
  found in the document"
- Dismissible, with "Don't show again" checkbox
- Accessible via "Help â†’ Take a tour" menu item

**Effort:** ~1.5 days. No backend dependency. Use localStorage for
"seen" state.

**Impact:** Reduces time-to-value from "confused for 10 minutes" to
"productive in 60 seconds". Critical for adoption beyond the core
engineering team.

---

## Priority Recommendation

| # | Proposal | Effort | Backend Dep | Impact |
|---|----------|--------|-------------|--------|
| 2 | Drag-and-drop upload | 0.5d | None | High â€” table stakes |
| 1 | Command palette (âŒ˜K) | 1d | None | High â€” power users |
| 3 | Confidence heatmap | 1d | None | High â€” demo wow factor |
| 6 | Keyboard shortcuts + a11y | 2d | None | High â€” enterprise req |
| 8 | Onboarding tour | 1.5d | None | High â€” adoption |
| 4 | Run comparison | 2d | None | Medium â€” iterative tuning |
| 7 | Analytics dashboard | 3d | Yes | Medium â€” self-improvement |
| 5 | Batch processing | 3d | Yes | High â€” enterprise req |

**Recommended immediate picks (no backend deps, high impact):**
1. Drag-and-drop upload (0.5d)
2. Command palette (1d)
3. Confidence heatmap (1d)

These three can ship in 2.5 days and dramatically improve the UX.

---

## Request

Please review and let me know which proposals to prioritize. I can
start implementing any of the backend-independent items immediately.


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
