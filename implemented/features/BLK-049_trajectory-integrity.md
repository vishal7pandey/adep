---
id: BLK-049
type: feature
title: "Trajectory integrity — error cascade visualization and recovery"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T22:35:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-028, BLK-046]
tags: [frontend, backend, ux, trajectory, error-cascade, recovery, audit, heuristics]
---

## Description

Implement trajectory integrity features from the UX audit framework:
visualize intermediate steps, detect cascading errors, and support
state rollback to the last successful node when a cascade is identified.

## Motivation

The UX audit framework identifies trajectory instability as a unique
failure class: a minor error early in a task compounds through
subsequent stages. Reliability of completing an 8-step trajectory can
collapse to <25% even if individual step success is 60%.

ADEP's ReAct loop is inherently multi-step. The UI must help users
detect when the agent is going off-track and intervene before the
cascade becomes unrecoverable.

## Design

### 1. Trajectory Visualization (Pane 1)
- Each cycle in the trace shows a "health indicator":
  - ✅ Green dot: tool succeeded, gap reduced
  - ⚠️ Yellow dot: tool succeeded but gap not reduced (agent may be stuck)
  - ❌ Red dot: tool failed
- Consecutive yellow/red dots (3+) trigger "Agent may be stuck" banner
- Cycle timeline shows progress: `Cycle 1 ✅ → Cycle 2 ✅ → Cycle 3 ⚠️ → Cycle 4 ⚠️ → Cycle 5 ⚠️ → ⚠️ Stuck?`

### 2. Error Cascade Detection (backend)
- Track consecutive cycles where gap_report didn't improve
- If 3+ consecutive non-improving cycles: emit SSE `trajectory_warning` event
- If 5+ consecutive: emit `trajectory_critical` — agent is likely in a loop
- Compaction node can help (summarize and reset) but shouldn't mask the pattern

### 3. Recovery Actions
- When trajectory warning fires: Pane 1 shows "Agent may be stuck" banner with:
  - "Rollback to cycle N" (last green cycle) → uses BLK-046 rollback
  - "Compact and retry" → triggers manual compaction
  - "Stop and review" → stops agent, shows partial results
- When trajectory critical fires: agent auto-pauses, user must choose recovery action

## Acceptance Criteria

- [ ] Health indicator dot on each cycle card in Pane 1 (green/yellow/red)
- [ ] Consecutive non-improving cycle counter (backend tracks in state)
- [ ] SSE `trajectory_warning` event after 3 consecutive non-improving cycles
- [ ] SSE `trajectory_critical` event after 5 consecutive non-improving cycles
- [ ] "Agent may be stuck" banner with 3 recovery options (rollback, compact, stop)
- [ ] Auto-pause on trajectory_critical (agent stops, waits for user)
- [ ] Cycle timeline visualization showing health dots in sequence
- [ ] Backend: `consecutive_non_improving` counter in AgentState
- [ ] Test: 3 non-improving cycles triggers warning event
- [ ] Test: rollback to last green cycle, agent takes different approach
- [ ] Test: compaction breaks the loop (agent gets fresh summary, tries new approach)

## Constraints

- Health indicators are visual only — they don't change agent behavior [SF]
- Auto-pause on critical is the only automatic intervention; warnings are advisory
- The `attempted` set prevents literal retry loops; this catches subtler cascades
- Non-improving = gap_report.gaps count didn't decrease (or new gaps appeared)

## Dependencies

- BLK-028 (Pane 1 — cycle display, banner)
- BLK-046 (Agent control — rollback for recovery)

## Notes

- Agentic UX Audit: §Evaluating Trajectory Integrity and Cascading Failure Modes
- §Recursive Context Contamination — compaction helps reset contaminated context
- §The Failure Cascade Test — audit protocol for trajectory testing
