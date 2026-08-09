---
id: BLK-131
type: feature
title: "Upload-first flow — classify document, suggest agent, remove upfront agent choice"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: [BLK-127]
tags: [frontend, ux, onboarding, classification, upload-flow]
---

## Problem

The current flow forces the user to choose an agent definition
*before* uploading a document. With 11+ prebuilt agents, a new user
has no basis for that decision — they haven't even told the system
what they have yet.

Choosing wrong produces a confusing failure: mostly-empty fields with
low confidence and no indication that the *agent choice* was the
problem rather than the document.

## Requirements

### 1. Invert the Flow

**Before:** choose agent → upload → run
**After:** upload → system suggests agent → confirm → run

### 2. Suggestion UI

After upload completes, call
`POST /api/v1/documents/{id}/suggest-agent` (BLK-127) and show:

```
  This looks like an Invoice  (92% confident)

  Suggested agent:  Invoice Extractor
  [ Use this agent ]   [ Choose a different agent ]

  Other possibilities:
    Utility Bill        (5%)
    Thermal Receipt     (2%)
```

- One-click accept for the top suggestion
- Alternatives listed with their confidence, one click to switch
- "Choose a different agent" opens the full agent picker

### 3. Low-Confidence Handling

If no prediction clears the confidence threshold, do **not** guess.
Show the top candidates and require an explicit choice:

```
  We're not sure what this document is.
  Pick the closest match:
    [ Invoice ]  [ Purchase Order ]  [ Delivery Note ]
    [ Browse all agents ]
```

### 4. Multi-Type Documents

If `is_multi_type` is true, warn clearly:

```
  This document contains multiple document types.
  Pages 1-2 look like an Invoice, pages 3-4 like a Bill of Lading.
  Multi-document processing isn't supported yet — the agent will
  process the whole file as one document.
```

Be honest about the limitation rather than silently producing bad
results.

### 5. Preserve the Expert Path

Users who know what they want must not be slowed down:
- Keep the agent picker directly accessible from the sidebar
- If an agent is already selected when a document is uploaded, skip
  the suggestion step and use the selection
- Remember the last-used agent per document type

## Acceptance Criteria

- [ ] Upload no longer requires a prior agent selection
- [ ] Suggestion card shows top prediction with confidence
- [ ] One-click accept starts the run
- [ ] Alternatives listed with confidence and one-click switch
- [ ] Low-confidence case requires explicit choice, never auto-guesses
- [ ] Multi-type documents show an honest limitation warning
- [ ] Expert path preserved — pre-selected agent skips suggestion
- [ ] Last-used agent remembered per document type
- [ ] Graceful degradation if the suggest endpoint is unavailable
      (fall back to the agent picker)
- [ ] Loading state while classification runs

## Notes

Blocked on backend BLK-127 (`classify_document` + suggest endpoint).
Build against a mocked response first so the UI is ready when the
endpoint lands.

This is the single biggest reduction in time-to-first-value for new
users. Pair it with BLK-113 (drag-and-drop) — drop a file, get a
suggestion, click go.
