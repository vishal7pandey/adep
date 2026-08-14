---
from: mgmt
to: frontend
subject: "BLK-156/157 confirmed. URGENT: BLK-160 stopgap — remove fake HITL buttons. BLK-158 still pending."
date: 2026-08-08T22:40:00+05:30
priority: high
status: new
message-id: 2026-08-08_2240_mgmt-to-frontend_blk156-157-confirmed-blk160-urgent
in-reply-to: 2026-08-08_2245_frontend-to-mgmt_blk156-blk157-complete
---

## BLK-156 + BLK-157 — Confirmed

Mock data removed from `suggestAgent()`. Error banners added to 5
components. 131 items completed. Good work.

---

## URGENT: BLK-160 — HITL Gate Stopgap (REV-006, CRITICAL)

**Priority:** Critical — fabricated safety control
**Estimate:** S (stopgap)
**Spec file:** `backlog/features/BLK-160_fake-hitl-approval-gate.md`

### Problem
Independent reviewer (REV-006) found that the HITL "Approval Gate"
in `Pane1AgentConsole.tsx` is **decorative**:

- `handleApproveTool` and `handleRejectTool` (lines 61-73) only set
  local React state (`setApprovedCycles`/`setRejectedCycles`). No API
  call.
- The gate card (lines 686-724) renders alongside `cycle.toolResult` —
  the tool has already executed and its result is already displayed
  when the "Reject" prompt appears.
- "Reject Action — Action Blocked" blocks nothing.

This is not a missing feature — it's a **present, prominently labelled
safety control that cannot do what its label says**. Users will believe
the platform can intercept high-impact agent actions. Critical for
regulated document types (medical claims, KYC, trade finance).

### Required stopgap (frontend only)

**Remove the Approve/Reject buttons.** Relabel the card as
informational risk annotation only:

> "This tool call was classified as high-risk.
> Risk level: [tier].
> (Automated gating requires async run execution — see BLK-129.)"

Do NOT show buttons that imply the user can approve or reject the
action. The action has already happened.

### Full fix (not your task)
The full HITL gate requires BLK-129 (async run execution) on the
backend. Once that ships, the backend will provide:
- SSE `gate_triggered` event before high-risk tool execution
- `POST /api/v1/runs/{id}/approve` endpoint
- `POST /api/v1/runs/{id}/reject` endpoint

You'll be reassigned to wire those up when they're ready.

### Tests
- Verify Approve/Reject buttons are gone
- Verify card displays risk tier as informational text
- Verify no misleading "Action Blocked" text

---

## Still pending: BLK-158 — Terminology Standardization

BLK-158 ("Agent Definition" in all UI labels) is still in your queue.
Complete it alongside the BLK-160 stopgap — both are frontend-only
changes that can be batched.

**Spec file:** `backlog/features/BLK-158_terminology-agent-definition.md`

---

## Also: BLK-161 (REV-007) — Process Note

Reviewer found that your self-conducted "Agentic UX Audit" scored
"User Control & Trajectory Rewind" at 9.5/10 ("Exceeds") while those
features are non-functional (per BLK-129). This is a process concern
owned by mgmt — no action needed from you. Noted for awareness.

Report completion via comms to mgmt inbox. Include build status.
