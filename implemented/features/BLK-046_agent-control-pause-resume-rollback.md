---
id: BLK-046
type: feature
title: "Agent control — pause, resume, stop, and state rollback"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T22:35:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-023, BLK-028]
tags: [frontend, backend, ux, control, hitl, rollback, audit, heuristics]
---

## Description

Implement user control mechanisms for the agent: pause execution, resume,
emergency stop, and state rollback to a previous cycle. This is the
"emergency exit" heuristic — users must always be able to halt and
rewind the agent.

## Motivation

The UX audit framework identifies "User control and freedom" as the most
critical heuristic in autonomous design. The audit must test for:
- "Emergency exits" or time-travel debugging
- Ability to halt autonomous execution instantly
- Roll back system state to a pre-execution environment
- Agents must never act without the theoretical possibility of intervention

## Design

### Control Buttons (Pane 1 header)
- **Pause** (⏸): Halts agent after current cycle completes. SSE stream stays open.
- **Resume** (▶): Continues from paused state.
- **Stop** (⏹): Emergency halt — agent stops immediately, partial results preserved.
- **Rollback** (↩): Opens cycle picker — select a past cycle to rewind to.

### Rollback Flow
1. User clicks Rollback → dropdown shows list of completed cycles
2. User selects cycle N → backend restores LangGraph checkpoint for cycle N
3. Agent resumes from cycle N with state at that point
4. Trace entries after cycle N are pruned (but preserved in checkpoint log)
5. `attempted` set is preserved (retry-loop prevention still active)

### SSE Events
- `paused`: `{"type": "paused", "cycle": N}`
- `resumed`: `{"type": "resumed", "cycle": N}`
- `stopped`: `{"type": "stopped", "cycle": N, "partial_result": {...}}`
- `rolled_back`: `{"type": "rolled_back", "from_cycle": N, "to_cycle": M}`

## Acceptance Criteria

- [ ] Pause button in Pane 1 header (disabled when not running)
- [ ] Resume button appears when paused (replaces Pause)
- [ ] Stop button always visible during run (red/Coral `#F47C6D`)
- [ ] Rollback button opens cycle picker dropdown
- [ ] Backend: `POST /api/v1/runs/{id}/pause` endpoint
- [ ] Backend: `POST /api/v1/runs/{id}/resume` endpoint
- [ ] Backend: `POST /api/v1/runs/{id}/stop` endpoint
- [ ] Backend: `POST /api/v1/runs/{id}/rollback` with body `{"to_cycle": N}`
- [ ] LangGraph checkpoint restoration for rollback
- [ ] `attempted` set preserved across rollback (retry-loop prevention)
- [ ] SSE events for all control actions
- [ ] Frontend: control buttons use LTTS colors (Pause=Mobility Blue, Stop=Coral)
- [ ] Test: pause → resume → extraction completes successfully
- [ ] Test: stop → partial result preserved and displayed
- [ ] Test: rollback to cycle 3 → agent resumes and takes different path

## Constraints

- Pause is graceful (after current cycle), Stop is immediate [SF]
- Rollback preserves `attempted` set — non-negotiable [§12.3]
- Full trace persists in checkpoint — rollback only affects active state
- v1: rollback uses LangGraph checkpoint (in-memory). Durable persistence is v2.

## Dependencies

- BLK-023 (SSE streaming — new event types)
- BLK-028 (Pane 1 — control buttons in header)

## Notes

- Agentic UIUX Audit: §User control and freedom, §The Interruption Test
- Nielsen heuristic: "User control and freedom"
- ISO 9241-110: "Controllability"
- The Gate Pattern (BLK-047) is complementary — gates prevent bad actions, rollback fixes them
