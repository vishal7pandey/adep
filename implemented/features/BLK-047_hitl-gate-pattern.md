---
id: BLK-047
type: feature
title: "Human-in-the-Loop gate pattern — risk-tiered approval for agent actions"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T22:35:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-028, BLK-046]
tags: [frontend, backend, ux, hitl, gate-pattern, approval, risk, audit, heuristics]
---

## Description

Implement the "Gate Pattern" for agent actions: the agent fully prepares
an action but pauses for human review before execution. Actions are
classified by risk tier, with gating proportional to consequence.

## Motivation

The UX audit framework identifies the Gate Pattern as fundamental for
agentic systems. If an agent has authority to take consequential actions,
the UI must intercept and present the proposed action for human sign-off.

For ADEP v1, the agent's "actions" are tool calls on documents. While
these are not externally destructive (no email sending, no DB writes),
the gate pattern still applies to:
- Low-confidence extractions that would be auto-accepted
- Semantic check failures that trigger manual review
- Partial results where the agent wants to "give up" on a field

## Risk Tier Classification (ADEP-specific)

| Tier | ADEP Action | Gating |
|------|------------|--------|
| Low | OCR/VLM on a region, geometry ops | No gate — auto-execute |
| Medium | Extraction with confidence 0.5-0.79 | Conditional gate — flag for review, auto-accept if user doesn't review within timeout |
| High | Extraction with confidence < 0.5, semantic fail | Pre-execution review — agent pauses, user must approve or reject the field value |
| Critical | Agent wants to terminate with partial result | Explicit sign-off — user confirms "accept partial" or "retry" |

## Acceptance Criteria

- [ ] Risk tier field added to SSE `field_update` events: `risk_tier: "low" | "medium" | "high" | "critical"`
- [ ] Pane 2: medium-risk fields show yellow warning badge + "Review" button
- [ ] Pane 2: high-risk fields show red alert badge + "Approve/Reject" buttons
- [ ] Pane 2: critical (partial termination) shows modal: "Agent wants to stop — accept partial result?"
- [ ] Backend: agent pauses at gate (SSE `gate_triggered` event)
- [ ] Backend: `POST /api/v1/runs/{id}/approve` with body `{"field": "...", "action": "accept" | "reject"}`
- [ ] Approval card shows: proposed value, confidence, source region (bbox link to Pane 3), agent's reasoning
- [ ] Reject: agent retries with different tool/approach
- [ ] Accept: value locked, agent moves on
- [ ] Timeout: medium-risk auto-accepts after 60s; high-risk auto-rejects (deny by default)
- [ ] Confirmation fatigue prevention: only high/critical trigger gates; low/medium proceed autonomously
- [ ] Test: low-confidence extraction triggers gate, user approves, agent continues
- [ ] Test: partial termination requires explicit sign-off

## Constraints

- Only high and critical tiers trigger blocking gates (avoid confirmation fatigue) [SF]
- Medium tier is non-blocking (flagged for review but doesn't pause agent)
- Deny by default on timeout for high-risk (safety-first)
- Gate UI must show actionable elicitation (not just "Ready to proceed?")

## Dependencies

- BLK-028 (Pane 1 — gate notifications)
- BLK-046 (Agent control — pause/resume infrastructure)

## Notes

- Agentic UIUX Audit: §The Gate Pattern and Risk Classification, §Confirmation Fatigue
- Nielsen heuristic: "Error prevention"
- ISO 9241-110: "Controllability"
- v1: gates apply to extraction results, not tool calls (tool calls are all low-risk)
