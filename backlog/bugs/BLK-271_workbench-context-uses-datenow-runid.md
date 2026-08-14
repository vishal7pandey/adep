---
id: BLK-271
type: bug
title: "WorkbenchContext run ID still uses Date.now() — contradicts BLK-147 fix"
priority: medium
status: verifying
phase: 5
owner: antigravity
created: 2026-08-09T10:40:00+05:30
started: 2026-08-09T14:50:00+05:30
completed: null
estimate: S
depends-on: []
tags: [frontend, workbench, bug, regression]
---

## Description

`frontend/context/WorkbenchContext.tsx` line 35 generates a run ID using:

```ts
const startRun = (id = `run-${Date.now()}`) => {
```

BLK-147 claimed "crypto.randomUUID() replaces Date.now()". However, `WorkbenchContext` was never updated — it still uses `run-${Date.now()}` as a fallback run ID.

This produces run IDs that are not globally unique (two runs started in the same millisecond collide, or IDs can be predicted), and contradicts the completed BLK-147 claim. The front-end run IDs must use `crypto.randomUUID()`.

## Acceptance Criteria

- [x] Replace `run-${Date.now()}` with a UUID-based ID (`crypto.randomUUID()` or a `run-${uuid}` prefix)
- [x] Grep across `frontend/` for remaining `Date.now()` uses that generate IDs — fix or document
- [x] Verify build is clean
- [ ] Test verification (handed off to cline per PROTOCOL §7.1)

## Constraints

- Must keep the `run-` prefix for readability (or update all consumers consistently)
- Must not break the initial run ID propagation in Pane1AgentConsole

## Dependencies

- None

## Notes

- Found during frontend regression audit
- BLK-147 was marked complete but this file was missed
- Related to BLK-156 (mock data in suggestAgent) and the general "no fake/hardcoded values" principle

## Resolution

- Replaced `id = run-${Date.now()}` with `crypto.randomUUID()` UUID-based ID generation in `startRun` in `frontend/context/WorkbenchContext.tsx`.
- Audited `frontend/` codebase via grep search for `Date.now()` — confirmed zero remaining ID-generating `Date.now()` usages in frontend components or contexts.
- Set status to `verifying` and handed off to **cline** for independent test verification.

## Evidence

- `frontend/context/WorkbenchContext.tsx:L30-L36`: `startRun` uses `id || run_${crypto.randomUUID().replace(/-/g, '').substring(0, 12)}`.
- Grep search `Date.now()` in `frontend/`: 0 ID generation results.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
- **2026-08-09T14:50 (antigravity)**: Replaced `Date.now()` with `crypto.randomUUID()` in `startRun` in `frontend/context/WorkbenchContext.tsx` as part of BLK-187 refactoring. Audited all `frontend/` files for ID generation — no other `Date.now()` ID generators exist. Set status to `verifying` for cline sign-off.
