---
id: BLK-219
type: bug
title: "Frontend AiTemplateComposer error message references wrong backlog item — says BLK-070 instead of BLK-067"
priority: low
status: backlog
phase: 2
owner: antigravity
created: 2026-08-09T13:15:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, bug, error-message, ux]
---

## Description

In `frontend/components/templates/AiTemplateComposer.tsx:202`, the error message for a 404 response says:

```tsx
<p className="mt-1 text-[10px]">The backend AI Template Composer endpoint may not be deployed yet (BLK-070).</p>
```

BLK-070 is the **Surrogate Verifier**, not the AI Template Composer. The correct backlog item is **BLK-067** (AI Template Composer).

## Problem Statement

- The error message references the wrong backlog item, confusing anyone who tries to trace the issue
- The message itself is misleading — the endpoint exists and works (see BLK-199 correction); a 404 would indicate a different problem (e.g., wrong API base URL, auth issue, route not registered)

## Acceptance Criteria

- [ ] Change `BLK-070` to `BLK-067` in the error message
- [ ] Consider updating the message entirely since the endpoint does exist — a 404 is more likely a configuration issue than a deployment issue

## Constraints

- None — single line fix

## Dependencies

- `frontend/components/templates/AiTemplateComposer.tsx:202`

## Notes

- Found during full-repo audit; minor but indicative of copy-paste without verification

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
