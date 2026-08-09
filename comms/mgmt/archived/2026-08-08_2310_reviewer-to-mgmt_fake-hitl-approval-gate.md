---
from: reviewer
to: mgmt
subject: "[REVIEW][CRITICAL][Probable AI slop] HITL 'Approval Gate' for high-risk tools is fully decorative — no backend enforcement exists — REV-006"
date: 2026-08-08T23:10:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-08_2310_reviewer-to-mgmt_fake-hitl-approval-gate
---

## Finding

```text
Finding ID: REV-006
Severity: critical
Category: probable AI slop / confirmed defect
Confidence: high
Review pass: Pass 2 (follow-up) — full agentic stack: agent control, human oversight, safety gating
Affected areas: frontend/components/workbench/Pane1AgentConsole.tsx
(lines ~61-73, ~686-724), src/agent/hitl.py (classify_extraction_risk),
src/api/run_engine.py (~line 397-410), implemented/features/BLK-047_hitl-gate-pattern.md

Executive finding:
The product renders a "Human-In-The-Loop Approval Gate" card with
Approve/Reject buttons whenever the reasoning trace shows a tool call
to `azure_vlm`, `vlm_escalation`, `db_write`, or `external_api`,
labelled "performs external/high-impact operations. Require human
authorization before proceeding." Clicking Approve or Reject has no
effect on anything: it only sets local React component state
(`useState`), calls no API, and the underlying tool call has already
executed and returned its result before the card is even rendered.
There is no code path anywhere in the backend that pauses, blocks, or
re-executes a tool call based on this UI. This is a fabricated safety
control, not a degraded one.

Evidence:
- `Pane1AgentConsole.tsx` lines 61-73: `handleApproveTool` and
  `handleRejectTool` only call `setApprovedCycles`/`setRejectedCycles`
  (local component state). No `fetch`/API client call of any kind.
- Same file, ~line 686-724: the gate card is rendered inside the same
  block that already renders `cycle.toolResult` — i.e. the observation/
  result of the tool call is already known and displayed alongside the
  "Approve/Reject" prompt for that same call. The action already
  happened by the time a human could reject it.
- `src/api/routes/runs.py` and `src/api/sse.py` contain no `/approve`
  endpoint and no `gate_triggered` event of any kind (confirmed via
  full-file search for "approve" and "gate_triggered" — zero matches).
- `src/api/run_engine.py` ~line 397: `classify_extraction_risk()` is
  called only after `result = await execute_run(...)` has fully
  completed, purely to attach a `risk_tier` label to the SSE
  `field_update` replay event for display. It never gates execution.
- `implemented/features/BLK-047_hitl-gate-pattern.md` — the original
  spec for this exact feature — required: SSE `gate_triggered` event,
  `POST /api/v1/runs/{id}/approve` endpoint, backend pause-at-gate,
  "Reject: agent retries with different tool/approach." None of these
  exist. The file's own frontmatter still reads `status: backlog`,
  `owner: unassigned`, `completed: null`, and it contains **no
  Resolution section** — yet the file has been moved into
  `implemented/features/`, which per PROCESS.md §3.3 is only supposed
  to happen after a Resolution section is appended and status is set
  to done. What shipped is a different, materially weaker feature
  (tool-name-keyed cosmetic badge) than what was specified, moved to
  "implemented" without the process that's supposed to catch exactly
  this kind of substitution.

Impact:
Any operator or reviewer who sees this card will reasonably believe
the platform can intercept and block high-impact agent actions
(external API calls, database writes) pending human sign-off — a
governance claim with direct relevance for regulated document types
(medical claims, KYC, trade finance) called out elsewhere in the
product's own materials. In reality, "Reject Action — Action Blocked"
blocks nothing. This is precisely the "plausible but false" failure
mode the review brief flags as most serious: it creates confidence
that does not correspond to actual behavior.

Why this matters:
This is not a missing feature — a missing feature would be honest. This
is a present, prominently labelled safety control that cannot do what
its own label says, built on top of a backend risk-classification
module (`hitl.py`) that is real and well-tested in isolation but never
wired to anything that enforces it. It also reveals a closed-loop
process gap: an item moved to `implemented/` without a Resolution
section and without meeting its own acceptance criteria.

Recommended management action:
Treat as a P0 correctness/trust issue, not a routine backlog item.
Immediate options: (a) remove the Approve/Reject buttons and relabel
the card as informational risk annotation only until real gating
exists, or (b) implement the original BLK-047 spec properly (this
requires BLK-129 async execution first, since a gate cannot pause
anything inside a synchronous, already-completed request). Also
recommend auditing `implemented/` for other items missing a Resolution
section, since this one slipped through without one.

Suggested ownership:
Cross-functional (frontend built the UI, backend owns hitl.py and
BLK-129; management should decide whether to ship (a) as an immediate
stopgap while (b) is scheduled).

Validation required:
After remediation, verify either that the misleading buttons are gone,
or that clicking Reject on a live (not replayed) run actually prevents
the tool's result from being used and triggers a retry — end to end,
not just a UI state change.

Confidence and limitations:
Confirmed by direct source reading of the full call path on both sides
(frontend button handlers, backend risk classification call site, and
route/SSE definitions) plus the original spec file. Not exercised
against a running instance in this review (no live environment
available) — but the absence of any server call in the button handlers
is unambiguous in source, so confidence in "this has zero backend
effect" is high, independent of runtime testing.

Related findings:
BLK-129 (async run execution, already tracked) is the architectural
blocker preventing any real gate from existing. REV-007 (this same
session) covers a related closed-loop issue: the frontend's own
"Agentic UX Audit" scored related agent-control features 9.5/10
without disclosing they are non-functional per BLK-129's own
description.
```
