---
id: BLK-258
type: bug
title: "API client has no request timeout or abort — uploads/SSE/suggest can hang forever; unmounted components can't cancel"
priority: medium
status: backlog
phase: 3
owner: antigravity
created: 2026-08-09T13:30:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, api, timeout, abort, reliability, tech-debt]
---

## Description

`frontend/lib/api.ts` (`apiFetch`, ~lines 160-175) attaches `Authorization` but never sets an `AbortSignal` or timeout. Every request — upload, `suggestAgent`, template/skill generation, analytics fetches — can hang indefinitely if the backend stalls. Components cannot cancel in-flight work on unmount, and there's no 5xx-specific retry on the frontend (the audit found several "no retry" gaps).

Related: `Pane1AgentConsole.tsx` sets `isUploading` (~line 230) but never renders it — uploads show no progress/spinner, and `days`… the UI provides no feedback during multi-second uploads (BLK-131's upload-first flow depends on this UX).

## Problem Statement

- A stalled backend produces a permanently-spinning page (no timeout → no failure path → no user error).
- Unmount during an in-flight request → later `setState` on an unmounted component (the React 18 "no-op but noisy" pattern), and SSE topic the lintgate).
- Users cannot distinguish "uploading slowly" from "hung".

## Acceptance Criteria

- [ ] `apiFetch` and `connectToRunStream` accept/configure a timeout (e.g. 60s for uploads, 15s for metadata GETs) and expose `AbortSignal` so callers can cancel
- [ ] Components with in-flight requests abort on unmount
- [ ] Uploading state is rendered (spinner/progress) using `isUploading`
- [ ] A test: mock fetch never resolves → timeout/reject with a clear error; unmount cancels

## Constraints

- No behavioral regression for long-running tasks (must allow generous-but-bounded timeout)
- Keep SSE streaming semantics unaffected

## Dependencies

- `frontend/lib/api.ts`
- `frontend/components/workbench/Pane1AgentConsole.tsx`
- `frontend/lib/sse.ts`
- Related BLK-229 (SSE leak), BLK-230 (tests)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:30 (mgmt)**: Filed after reading apiFetch and Pane1's upload state.