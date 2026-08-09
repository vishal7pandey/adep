---
from: reviewer
to: mgmt
subject: "[REVIEW][HIGH][Process or closed-loop failure] Frontend's self-authored UX audit scored non-functional agent-control features 9.5/10 'Exceeds' — REV-007"
date: 2026-08-08T23:11:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-08_2311_reviewer-to-mgmt_self-audit-overclaim
---

## Finding

```text
Finding ID: REV-007
Severity: high
Category: process or closed-loop failure / probable AI slop
Confidence: high
Review pass: Pass 2 (follow-up) — closed-system workflow quality and
feedback-loop effectiveness
Affected areas:
comms/mgmt/archived/2026-08-08_1745_frontend-to-mgmt_agentic-ux-audit-report.md,
backlog/features/BLK-129_async-run-execution.md,
src/api/routes/runs.py (pause_run/resume_run/stop_run/rollback_run)

Executive finding:
Frontend's self-conducted "Agentic UX Audit" (archived, delivered to
mgmt, and used as the basis for a proposed sprint queue) scored
"User Control & Trajectory Rewind" at 9.5/10 ("Exceeds. Excellent
time-travel debugging. Includes Pause, Resume, Emergency Stop, Cycle
Rewind/Rollback, and Context Compaction") — describing exactly the
features that the backend's own tracked item, BLK-129, explicitly and
correctly describes as non-functional: "Agent control is theatre —
pause/resume/stop (BLK-046) cannot actually interrupt a synchronous
run — by the time the control request arrives the run has finished."
These two management-facing artifacts directly contradict each other
and neither references the other.

Evidence:
- `comms/mgmt/archived/2026-08-08_1745_frontend-to-mgmt_agentic-ux-audit-report.md`,
  row 3 of the heuristic table: score 9.5/10, "Exceeds."
- `backlog/features/BLK-129_async-run-execution.md`, "Problem" section,
  item 2: "Agent control is theatre... by the time the control request
  arrives the run has finished," created the same day (2026-08-08).
- `src/api/routes/runs.py` `pause_run`/`resume_run`/`stop_run` (lines
  ~378-460) only flip a `status` string on the stored run record via
  `_update_run_status`; `rollback_run`'s own docstring states "In v1
  (synchronous runs with in-memory checkpoints), this endpoint records
  the rollback request. Full checkpoint restoration requires async
  runs (v2)" — i.e. the code's own comments agree with BLK-129, not
  with the 9.5/10 score.
- `projectmgmt/STATUS.md` still lists BLK-129 as an open, unresolved
  backlog item ("Also still identified from prior audit") as of the
  most recent update, so the contradiction was never reconciled by
  either party.

Impact:
Management-facing self-audits that grade cosmetic/non-functional
behavior as "excellent" create false confidence in exactly the
dimension (agent controllability) that matters most for an agentic
product's safety story, and can lead to under-prioritizing the
architectural fix (BLK-129) because the UX scorecard says this area
is already strong. The same audit's "Strategic Proposals" section was
used to justify subsequent sprint items (BLK-120, BLK-132) without
flagging that a top-scored dimension rests on non-functional
plumbing.

Why this matters:
This is a feedback-loop integrity issue, not a one-off scoring error.
The project's stated process (PROCESS.md §5.1, "overcommunicate") and
RACI (mgmt is Accountable for reviewing all deliverables) depend on
self-reported status being reliable enough for management to act on
without independently re-deriving ground truth every time — which is
exactly what this review had to do to catch the discrepancy.

Recommended management action:
Ask the reporting party to reconcile or retract the 9.5/10 score for
"User Control & Trajectory Rewind" against BLK-129's own description,
and consider requiring self-audits to cross-reference known open
backlog items covering the same surface area before scoring it.
Recommend not treating self-reported UX/heuristic scores as
validated capability claims until independently spot-checked.

Suggested ownership:
Management/product (review-quality and reporting-standard is a
management-owned process concern per RACI.md §5 "Cross-Team
Coordination").

Validation required:
None beyond reconciling the two documents; this is a documentation/
process consistency issue rather than a code defect (the code defect
itself is BLK-129, already tracked, and REV-006, newly reported).

Confidence and limitations:
Confirmed by direct comparison of both archived text artifacts and the
route implementation; all three independently describe the same
underlying behavior consistently except for the numeric score
assigned to it. No inference required.

Related findings:
BLK-129 (async run execution, already tracked, describes the root
technical cause). REV-006 (this same session) documents a related,
more severe instance of the same pattern — a fabricated HITL approval
gate with zero backend enforcement.
```
