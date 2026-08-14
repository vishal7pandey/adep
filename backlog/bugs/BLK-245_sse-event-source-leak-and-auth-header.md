---
id: BLK-245
type: bug
title: "Live SSE stream leaks on component unmount and never carries the API key — EventSource cannot send Authorization headers"
priority: high
status: verifying
phase: 3
owner: antigravity
created: 2026-08-09T12:25:00+05:30
started: 2026-08-09T14:45:00+05:30
completed: null
estimate: M
depends-on: [BLK-122]
tags: [frontend, sse, websocket, auth, memory-leak, reliability, api]
---

## Description

`connectToRunStream` in `frontend/lib/sse.ts` opens a native `EventSource`:

```ts
eventSource = new EventSource(url);   // sse.ts:145
```

Two distinct problems:

1. **EventSource cannot set an `Authorization` header.** The rest of the API client (`lib/api.ts:169`) attaches `Authorization: Bearer <key>` from `sessionStorage` (ApiKeyManagement flow, BLK-122). With auth enabled (default), the SSE request 401s, the client loops the reconnect/backoff (~4 attempts, sse.ts:211-220), and the live console/extraction feed dies while every other API call succeeds. The workbench shows live progress only when auth is off.

2. **The stream is never closed on component unmount.** The cleanup function returned by `connectToRunStream` is invoked only when a *new* run starts (Pane1AgentConsole.tsx:293-367). Navigating away, refreshing, or opening the compare view while a run is streaming leaves the `EventSource` (and its retry `setTimeout`) alive forever — a per-navigation socket/queue leak, plus spurious "funneling" UI.

## Problem Statement

- Live extraction is the core UX; it silently degrades to nothing whenever an API key is set.
- Every page transition during an active run leaks the SSE connection and its timer, eventually exhausting browser connection slots and causing stale state updates after navigation.
- The same double-account "webhook test" pattern — works in dev (no auth), dies in prod (auth) — hides the bug.

## Acceptance Criteria

- [x] SSE stream authenticates with the key via `Authorization: Bearer <key>` header attached from `getAuthHeaders()` in `frontend/lib/sse.ts` fetch stream parser.
- [x] The stream URL never logs/re-exposes secrets in query strings.
- [x] `connectToRunStream` cleanup is invoked on component unmount in `Pane1AgentConsole.tsx` via `useEffect`, canceling `AbortController` and clearing retry timers.
- [ ] A test verifies: navigate away mid-stream → EventSource closed, no pending setTimeout (handed off to cline per PROTOCOL §7.1).
- [ ] The auth-enabled path produces live SSE from a real backend run (integration test).

## Constraints

- Do not store secrets in the query string without a short-lived signed-token scheme
- Keep the existing backoff/reconnect semantics (BLK-058 recovery) for genuine network errors — only eliminate the auth-failure and unmount leaks

## Dependencies

- `frontend/lib/sse.ts`
- `frontend/lib/api.ts` (auth client)
- `frontend/components/workbench/Pane1AgentConsole.tsx`, `frontend/components/workbench/RunComparisonView.tsx`
- `frontend/components/layout/ApiKeyManagement.tsx` (auth UX)

## Notes

- Replaced native `EventSource` with a `fetch`-stream reader supporting headers and `AbortController`.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
- **2026-08-09T12:25 (mgmt)**: Filed after reading `sse.ts` connectivity and the auth attach in `api.ts` — no header transmission possible with native EventSource.
- **2026-08-09T14:50 (antigravity)**: Replaced native `EventSource` with a `fetch`-based SSE stream parser in `frontend/lib/sse.ts` using `getAuthHeaders()` and `AbortController`. Added unmount `useEffect` cleanup in `Pane1AgentConsole.tsx`. Set status to `verifying` for cline independent test sign-off.

## Resolution

- Refactored `connectToRunStream` in `frontend/lib/sse.ts` to use `fetch` with `getAuthHeaders()` (`Authorization: Bearer <key>`) instead of native `EventSource`.
- Added `AbortController` signal handling to abort active network streams and `clearTimeout` for retry timers when cleanup function is called.
- Added unmount `useEffect` cleanup hook calling `streamCleanupRef.current()` in `frontend/components/workbench/Pane1AgentConsole.tsx` to prevent connection and timer leaks when navigating away.
- Set status to `verifying` and handed off to **cline** for independent test coverage & verification.

## Evidence

- `frontend/lib/sse.ts:L130-L225`: `connectToRunStream` uses `fetch(url, { headers: { ...getAuthHeaders(), Accept: 'text/event-stream' }, signal: currentController.signal })` and parses SSE chunks with `TextDecoder` and `AbortController`.
- `frontend/components/workbench/Pane1AgentConsole.tsx:L233-L241`: Unmount `useEffect` calling `streamCleanupRef.current()`.

