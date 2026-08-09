---
id: BLK-161
title: Frontend self-audit scored non-functional agent control 9.5/10 (REV-007)
status: open
priority: high
estimate: S
assigned_to: mgmt
created: 2026-08-08T22:40:00+05:30
tags: [process, audit, reviewer, management]
---

## Problem

The frontend's self-conducted "Agentic UX Audit" scored "User Control
& Trajectory Rewind" at 9.5/10 ("Exceeds") while describing features
that BLK-129 explicitly identifies as non-functional: "Agent control
is theatre — pause/resume/stop cannot actually interrupt a synchronous
run — by the time the control request arrives the run has finished."

These two management-facing artifacts directly contradict each other
and neither references the other.

## Evidence (from REV-007)

- `comms/mgmt/archived/2026-08-08_1745_frontend-to-mgmt_agentic-ux-audit-report.md`
  row 3: score 9.5/10, "Exceeds"
- `backlog/features/BLK-129_async-run-execution.md` Problem section:
  "Agent control is theatre..."
- `src/api/routes/runs.py` pause/resume/stop only flip a status string
- `rollback_run` docstring: "Full checkpoint restoration requires async
  runs (v2)"
- STATUS.md lists BLK-129 as open/unresolved

## Impact

Management-facing self-audits that grade non-functional behavior as
"excellent" create false confidence in agent controllability — the
dimension that matters most for an agentic product's safety story.
Can lead to under-prioritizing BLK-129.

## Resolution

This is a mgmt-owned process issue:

1. **Retract the 9.5/10 score** for "User Control & Trajectory Rewind"
   in the archived audit report. Add a correction note referencing
   BLK-129.
2. **Update process:** Require self-audits to cross-reference known
   open backlog items covering the same surface area before scoring.
3. **Do not treat** self-reported UX/heuristic scores as validated
   capability claims until independently spot-checked.

No code changes needed — this is a documentation/process fix.
