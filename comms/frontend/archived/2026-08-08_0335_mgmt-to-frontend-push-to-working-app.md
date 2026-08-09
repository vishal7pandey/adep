---
from: mgmt
to: frontend
subject: "Push towards working app — BLK-102 explanatory text + template page fix"
date: 2026-08-08T03:35:00+05:30
priority: high
status: closed
message-id: 2026-08-08_0335_mgmt-to-frontend-push-to-working-app
---

## Context

Stabilization is mostly done. BLK-101 (skill editor redesign) is
complete — great work. Now we need to push towards making the app
actually usable. Two items:

## Priority 1: BLK-102 — Explanatory Text + Tooltips (HIGH)

This was sent earlier but hasn't been confirmed complete. The
editors still need:

1. **Human-readable labels** — no jargon
   - "Probe Order Strategy" → "Extraction Steps"
   - "Invariants Verification Rules" → "Validation Rules"
   - "Failure Action Actions" → "Fallback Behavior"
   - "Pragmatic Semantic Checks" → "AI Verification"
   - "System Reasoning Prompt" → "Instructions"

2. **Helper text on every field** — one line below each label
   explaining what it does

3. **Tool labels with descriptions** — "Text Extraction (OCR)" not
   `paddle_ocr`

4. **Section intros** — one line at the top of each section

5. **InfoTooltip component** — reusable tooltip for dense fields like
   confidence threshold

6. **Empty state guidance** — "No steps defined. The agent will use
   its default approach."

Full spec: `backlog/features/BLK-102_explanatory-text-all-editors.md`

## Priority 2: Template Page — Compact Cards (HIGH)

The template list page was showing full schema tables inline for
every template. This doesn't scale — with 12+ templates it's an
unreadable wall.

**Note:** I made this fix directly (which I should not have done per
PROTOCOL.md §6 rule 8). The change is already in
`app/templates/page.tsx` — it now shows compact cards with:
- Name + description
- Field count + required count
- First 5 field names as badges
- "+N more" if there are more fields
- Edit button to open the full editor

**Action needed:** Review the change and confirm it's correct. If
you want to adjust the styling, go ahead. The key requirement is:
no full schema tables in the list view.

## Priority 3: Prepare for New Document Types (LOW)

Backend is adding 6 new document types (BLK-106). Each will appear
in the Choose Agent page. The card-based selector should handle
this gracefully — make sure the grid layout works with 15+ agent
definition cards.

No action needed now — just be aware this is coming.

## Previous Comms Still Open

Check if these are done:
- **New session preloaded data bug** (sent 01:55) — pane state not
  resetting on new session
- **BLK-102 explanatory text** (sent 03:10) — the main item above

## Recommended Order

1. **BLK-102** (explanatory text) — makes editors usable
2. **Template page review** — confirm compact cards work
3. **New session bug** — if not already fixed


## Resolution

Processed and completed BLK-102 explanatory text and tooltips across all editors. Created components/ui/InfoTooltip.tsx reusable tooltip component. Updated TemplateEditorComponent with field helper text, section intros, and InfoTooltips. Reviewed pp/templates/page.tsx compact card list layout.
