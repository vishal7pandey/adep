---
id: BLK-078
type: feature
title: "Progressive workbench — panes appear as user advances through workflow"
priority: high
status: backlog
phase: 3
owner: frontend
created: 2026-08-08T01:00:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-026, BLK-028, BLK-033, BLK-038, BLK-077]
tags: [frontend, workbench, layout, progressive-disclosure, ux]
---

## Description

The workbench should not show all 3 panes at once on a new session.
Panes appear progressively as the user advances through the extraction
workflow. This reduces cognitive load and matches the natural workflow:

1. **Chat phase** — only Pane 1 (Agent Console) is visible. No document
   loaded. The user sees a blank chat / agent console with the document
   upload control.
2. **Document phase** — when the user uploads a document, Pane 3
   (Document Viewer) slides in next to Pane 1. The user can inspect the
   document before starting extraction.
3. **Extraction phase** — when the user clicks "Start Run", Pane 2
   (Extracted Data) appears with an "in progress" indicator. As fields
   are extracted, the indicator is replaced with actual field cards.

## Visual States

### Phase 1: Chat (no document)

```
┌─────────────────────────────────────────┐
│              Pane 1                     │
│         (Agent Console)                 │
│                                         │
│  [Upload Document] button               │
│  [Definition selector]                  │
│                                         │
│  Blank trace area:                      │
│  "Upload a document to begin"           │
│                                         │
└─────────────────────────────────────────┘
```

- Pane 1 takes full width
- No Panes 2 or 3 rendered
- Upload control is prominent
- "Start Run" button is disabled until document is uploaded

### Phase 2: Document uploaded (pre-extraction)

```
┌──────────────────────┬──────────────────┐
│      Pane 1          │    Pane 3        │
│   (Agent Console)    │ (Document Viewer)│
│                      │                  │
│  Document: foo.pdf   │  [document       │
│  [Start Run] enabled │   rendering]     │
│                      │                  │
└──────────────────────┴──────────────────┘
```

- 2-column grid (50/50 split)
- Pane 3 shows the uploaded document
- Pane 1 shows document name and enables "Start Run"
- Pane 2 is NOT rendered

### Phase 3: Extraction running

```
┌──────────┬──────────┬──────────────────┐
│  Pane 1  │  Pane 3  │     Pane 2       │
│ (Console)│ (Viewer) │  (Output)        │
│          │          │                  │
│  Trace   │  [doc]   │  ┌────────────┐  │
│  cycles  │          │  │ ⏳ In       │  │
│  flowing │          │  │   Progress  │  │
│          │          │  │             │  │
│          │          │  │ Extracting  │  │
│          │          │  │ fields...   │  │
│          │          │  └────────────┘  │
└──────────┴──────────┴──────────────────┘
```

- 3-column grid (equal thirds)
- Pane 2 shows "in progress" state with spinner / animated indicator
- As `field_update` SSE events arrive, field cards replace the indicator
- Progress bar in Pane 1 shows completion %

### Phase 3b: Extraction completed

- Pane 2 shows full field card grid / JSON view
- "In progress" indicator is gone
- User can export, edit, re-run

## Implementation Notes

### State Management

Create a `WorkbenchContext` that tracks:

```typescript
type WorkbenchPhase = 'chat' | 'document' | 'extraction';

interface WorkbenchState {
  phase: WorkbenchPhase;
  documentId: string | null;
  documentUrl: string | null;
  documentFileName: string | null;
  runId: string | null;
  runStatus: 'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'stopped';
  extractedFields: ExtractedField[];
}
```

### Transitions

| Trigger | From → To | Action |
|---------|-----------|--------|
| Upload document | chat → document | `setDocument(id, url, name)` |
| Click "Start Run" | document → extraction | `startRun(runId)` |
| Run completes | extraction → extraction | `completeRun(fields)` (status changes, panes stay) |
| Click "New Session" | any → chat | `reset()` |
| Select session from sidebar | any → extraction (or document) | Load run state from API |

### Pane 2 In-Progress State

When `runStatus === 'running'` and `extractedFields.length === 0`:
- Show a centered card with animated spinner
- Text: "Extracting fields from document..."
- Subtext: "Agent is analyzing the document and extracting structured data."

When `runStatus === 'running'` and `extractedFields.length > 0`:
- Show field cards that have arrived so far
- Show a "more fields coming..." placeholder at the bottom

When `runStatus === 'completed'`:
- Show full field card grid (existing behavior)

### WorkbenchLayout Changes

Replace the static 3-column grid with conditional rendering:

```tsx
// Phase 1: chat — Pane 1 only, full width
// Phase 2: document — Pane 1 + Pane 3, 50/50
// Phase 3: extraction — Pane 1 + Pane 3 + Pane 2, equal thirds
```

Use CSS transitions for smooth pane appearance (slide-in, fade-in).

### Pane 1 Changes

- When `phase === 'chat'`: show empty state with "Upload a document to begin"
- When `phase === 'document'`: show document name, enable Start Run
- When `phase === 'extraction'`: show trace cycles as they arrive
- "Start Run" button disabled until document is uploaded
- Upload control always visible in Pane 1

### Sidebar Integration

- "New Session" button calls `reset()` → phase returns to 'chat'
- Selecting a session from sidebar loads that run → phase set based on
  run status (completed → extraction, running → extraction, idle →
  document if document exists)

## Acceptance Criteria

- [ ] New session shows only Pane 1 (full width)
- [ ] Uploading a document opens Pane 3 (Document Viewer)
- [ ] Pane 3 is NOT visible before document upload
- [ ] Clicking "Start Run" opens Pane 2 (Extracted Data)
- [ ] Pane 2 shows "in progress" indicator when extraction is running
- [ ] Pane 2 shows field cards as they arrive via SSE
- [ ] Pane 2 shows full results when extraction completes
- [ ] "New Session" resets to chat phase (only Pane 1)
- [ ] Selecting a past session from sidebar loads correct phase
- [ ] Pane transitions are smooth (fade/slide, not jarring)
- [ ] "Start Run" is disabled until document is uploaded
- [ ] Works in both dark and light mode
- [ ] Collapsed sidebar still shows session status icons

## Dependencies

- BLK-026 (Next.js scaffold)
- BLK-028 (Pane 1: Agent Console)
- BLK-033 (Pane 2: Extracted Data)
- BLK-038 (Pane 3: Document Viewer)
- BLK-077 (Sidebar Session Manager)

## Constraints

- Do NOT show empty panes with placeholder data — only show a pane when
  there is real content for it
- Pane 2 "in progress" state must be visually distinct from "completed"
- Transitions should be 200-300ms, not jarring
- Mobile/responsive: panes stack vertically on small screens (BLK-056)
