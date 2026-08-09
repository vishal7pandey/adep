---
id: BLK-132
type: feature
title: "Loading skeletons, empty states, and error recovery audit"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T13:50:00+05:30
estimate: M
depends-on: []
tags: [frontend, ux, loading-states, error-handling, polish]
---

## Problem

The app has no systematic treatment of the three non-happy-path
states. Every screen needs to answer:

- **Loading**: what does the user see while data is in flight?
- **Empty**: what do they see when there's legitimately nothing?
- **Error**: what do they see when it broke, and how do they recover?

Today these are inconsistent — some screens flash, some show nothing,
some show a bare error string with no recovery action.

## Requirements

### 1. Loading Skeletons

Replace spinners and blank flashes with content-shaped skeletons:

| Screen | Skeleton |
|--------|----------|
| Agent picker | Card grid skeleton, correct card dimensions |
| Skills / Templates list | Row skeletons matching list item height |
| Pane 2 (extracted data) | Field card skeletons |
| Pane 3 (document viewer) | Page-shaped placeholder with shimmer |
| Analytics (BLK-119) | Chart-shaped placeholders |

Skeletons must match the real content's dimensions so there is no
layout shift when data arrives.

### 2. Empty States

Every list and pane needs a purposeful empty state with a next action:

| Screen | Empty state |
|--------|-------------|
| No sessions | "No extractions yet" + "Upload a document" CTA |
| No agents | "No agents defined" + "Build an agent" CTA |
| No fields extracted | Explain *why* (gaps, low confidence) + link to trace |
| No documents | Drop-zone prompt (ties to BLK-113) |
| Search no results | "No matches for 'x'" + clear-search action |

Distinguish "empty because new" from "empty because filtered" —
they need different messages and different actions.

### 3. Error States with Recovery

Every error must state what failed and offer a way forward:

- **Network failure**: "Can't reach the server" + Retry button +
  last-successful timestamp
- **404**: "This run no longer exists" + back to sessions
- **401/403** (after BLK-122): "Session expired" + re-auth prompt
- **429**: "Rate limited — retrying in Ns" with a countdown, then
  automatic retry
- **500**: "Something broke on our end" + Retry + copy-error-details
  button (include request id for support)
- **Run failed**: show the gap report and partial results — a failed
  run still has value; never discard partial extraction

Never show a raw stack trace or bare JSON error to the user. Never
show an error with no action.

### 4. Optimistic Updates

For mutations where the outcome is near-certain, update the UI
immediately and reconcile on response:

- Renaming a session
- Toggling a skill's semantic-checks flag
- Reordering template fields
- Deleting a definition (with undo affordance)

On failure, revert with a clear toast explaining the revert. Do not
leave the UI in a state that lies about what was persisted.

### 5. Retry Policy

- Automatic retry with exponential backoff for idempotent GETs
  (3 attempts: 1s, 2s, 4s)
- Never auto-retry non-idempotent mutations — offer a manual Retry
  instead
- Show retry progress rather than an indefinite spinner

## Acceptance Criteria

- [ ] Skeleton components for all 5 screen classes, dimension-matched
- [ ] No layout shift when real content replaces a skeleton
- [ ] Purposeful empty state with a CTA on every list and pane
- [ ] "Empty because new" vs "empty because filtered" distinguished
- [ ] Error states for network, 404, 401/403, 429, 500, run-failure
- [ ] Every error offers a recovery action
- [ ] 429 shows a countdown and auto-retries
- [ ] Failed runs still display partial results and the gap report
- [ ] No raw stack traces or bare JSON surfaced to users
- [ ] Request id included in copyable error details
- [ ] Optimistic updates on the 4 listed mutations, with revert-on-failure
- [ ] Auto-retry with backoff for idempotent GETs only
- [ ] Tests: loading, empty, and error state rendering per screen

## Notes

This is unglamorous and it is what separates a demo from a product.
Users judge reliability by how the app behaves when things go wrong,
not when they go right.
