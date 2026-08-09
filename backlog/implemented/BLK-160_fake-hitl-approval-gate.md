---
id: BLK-160
title: HITL approval gate is decorative — no backend enforcement (REV-006)
status: open
priority: critical
estimate: L
assigned_to: both
created: 2026-08-08T22:40:00+05:30
tags: [security, safety, critical, reviewer, hitl, frontend, backend]
---

## Problem

The HITL "Approval Gate" card in `Pane1AgentConsole.tsx` displays
Approve/Reject buttons for high-risk tool calls (`azure_vlm`,
`vlm_escalation`, `db_write`, `external_api`), but clicking either
button has **zero backend effect**. The tool has already executed
and returned its result before the card is even rendered.

This is a **fabricated safety control**, not a missing feature. The
UI implies human oversight that does not exist.

## Evidence (from REV-006)

- `Pane1AgentConsole.tsx:61-73` — `handleApproveTool` and
  `handleRejectTool` only call `setApprovedCycles`/`setRejectedCycles`
  (local React state). No API call.
- `Pane1AgentConsole.tsx:686-724` — gate card renders alongside
  `cycle.toolResult` — the result is already known when the "reject"
  prompt appears.
- `src/api/routes/runs.py` — no `/approve` endpoint exists.
- `src/api/sse.py` — no `gate_triggered` event exists.
- `src/api/run_engine.py:397` — `classify_extraction_risk()` is called
  only after `execute_run()` completes, purely to attach a label.
- `BLK-047` spec required: SSE `gate_triggered` event,
  `POST /api/v1/runs/{id}/approve` endpoint, backend pause-at-gate.
  None exist. Spec moved to `implemented/` without Resolution section.

## Impact

Operators will believe the platform can intercept high-impact agent
actions pending human sign-off. Critical for regulated document types
(medical claims, KYC, trade finance). "Reject Action — Action Blocked"
blocks nothing.

## Resolution

**Immediate stopgap (frontend):**
Remove Approve/Reject buttons. Relabel card as informational risk
annotation only: "This tool call was classified as high-risk. Risk
level: [tier]. (Automated gating requires async run execution —
see BLK-129.)"

**Full fix (backend, blocked on BLK-129):**
Implement original BLK-047 spec:
- SSE `gate_triggered` event before high-risk tool execution
- `POST /api/v1/runs/{id}/approve` endpoint
- `POST /api/v1/runs/{id}/reject` endpoint
- Backend pauses execution at gate, waits for human response
- Reject: agent retries with different tool/approach
- Requires BLK-129 (async run execution) first — cannot gate inside
  a synchronous, already-completed request

## Tests

- Stopgap: Verify Approve/Reject buttons are gone, card is
  informational only
- Full fix: Clicking Reject on a live run prevents the tool's result
  from being used and triggers a retry — end to end
