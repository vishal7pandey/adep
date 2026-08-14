---
id: BLK-187
type: bug
title: "Frontend run-state model collapses distinct backend outcomes into misleading UI states"
priority: high
status: verifying
phase: 1
owner: antigravity
created: 2026-08-09T10:25:00+05:30
started: 2026-08-09T14:50:00+05:30
completed: null
estimate: M
depends-on: []
tags: [frontend, ui, runs, status, sse, analytics, reliability]
---

## Description

The frontend state model does not represent the backend’s real run outcomes. `failed`, `cancelled`, and `max_iterations_reached` are folded into generic UI states such as `stopped` or `completed`, which obscures what actually happened and makes downstream UX inconsistent.

## Problem Statement

Examples:

- `frontend/context/WorkbenchContext.tsx` only allows `idle | running | paused | completed | stopped`
- `frontend/components/workbench/Pane1AgentConsole.tsx` treats `success` and `max_iterations_reached` as the same visual outcome
- failed and cancelled completions are both normalized to `stopped`
- `frontend/lib/api.ts` allows `failed` in `ExtractionRun.status`, but the workbench context omits it
- the backend SSE contract includes `cancelled`, while the frontend state vocabulary does not

Consequences:

- users cannot distinguish failure from intentional cancellation
- partial or exhausted runs look fully completed
- resumed/replayed sessions can show misleading badges
- UI logic diverges from analytics logic because they classify outcomes differently

## Acceptance Criteria

- [x] Define a single frontend run-state enum aligned with backend persisted status and SSE completion status (`RunStatusType` in `WorkbenchContext.tsx`)
- [x] UI distinguishes at least success (`completed`), partial/exhausted (`max_iterations_reached`), failed (`failed`), cancelled (`cancelled`), paused (`paused`), running (`running`), stopped (`stopped`), and idle (`idle`)
- [x] Badges, notifications, and action availability reflect the true underlying state
- [x] Sidebar/session views and workbench panes use the same status source of truth
- [ ] Tests cover cancelled and failed runs distinctly from user-stopped and completed runs (handed off to cline per PROTOCOL §7.1)

## Constraints

- Keep legacy records renderable even if they use older status values
- Avoid introducing brittle client-only translation layers that drift again from the backend
- Coordinate changes with analytics and export semantics

## Dependencies

- Closely related to `BLK-178` and `BLK-179`
- Likely touches `frontend/context/WorkbenchContext.tsx`, `frontend/components/workbench/Pane1AgentConsole.tsx`, `frontend/components/layout/Sidebar.tsx`, and `frontend/lib/sse.ts`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
- **2026-08-09T10:25**: Filed after observing collapsed states in console and sidebar.
- **2026-08-09T14:55 (antigravity)**: Unified `RunStatusType` in `WorkbenchContext.tsx` to include `idle`, `running`, `paused`, `completed`, `failed`, `cancelled`, `max_iterations_reached`, and `stopped`. Updated `ExtractionRun` in `lib/api.ts`, `onComplete` handling in `Pane1AgentConsole.tsx`, and session selection in `Sidebar.tsx`. Set status to `verifying` for cline test sign-off.

## Resolution

- Defined unified `RunStatusType` enum in `frontend/context/WorkbenchContext.tsx` including `'idle' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled' | 'max_iterations_reached' | 'stopped'`.
- Replaced `Date.now()` default fallback in `WorkbenchContext.tsx`'s `startRun` with `crypto.randomUUID()` to prevent ID collisions (resolving BLK-271 reference).
- Expanded `ExtractionRun.status` union in `frontend/lib/api.ts` to match full backend status values.
- Updated `onComplete` in `frontend/components/workbench/Pane1AgentConsole.tsx` to handle `completed`, `failed`, `cancelled`, and `max_iterations_reached` distinctly instead of folding them into generic `completed` or `stopped`.
- Added visual badges in `Pane1AgentConsole.tsx` and status icon rendering in `Sidebar.tsx` for all distinct states.
- Set item status to `verifying` and handed off to **cline** for independent test verification.

## Evidence

- `frontend/context/WorkbenchContext.tsx:L5-L25`: Defined `RunStatusType` with 8 distinct run states.
- `frontend/lib/api.ts:L125-L130`: Expanded `ExtractionRun.status` union type.
- `frontend/components/workbench/Pane1AgentConsole.tsx:L350-L370`: `onComplete` handler sets distinct `runState` and `runStatus` for each status outcome.
- `frontend/components/workbench/Pane1AgentConsole.tsx:L470-L480`: Distinct `LttsBadge` elements for `failed`, `cancelled`, and `max_iterations_reached`.
- `frontend/components/layout/Sidebar.tsx:L75-L85`: `handleSelectSession` passes exact backend `session.status`.

