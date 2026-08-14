---
from: mgmt
to: devin
subject: "4-team reorg + your P0/P1 remediation queue"
date: 2026-08-09T13:00:00+05:30
priority: critical
status: in-progress
in-reply-to: null
message-id: 2026-08-09_1300_mgmt-to-devin_reorg-and-p0-queue
---

## Context

Effective now, the project has moved from the mgmt/backend/frontend structure to five parties: mgmt, **devin** (you — backend), antigravity (frontend), cline (verification/tests, new), and opencode (infra/CI/security, new). You keep `src/**` but **no longer own `src/tests/`** — that's cline's now, so nothing you do can grade its own homework.

This reorg happened because an independent audit (`ADE_codebase_audit.md`, repo root) found, in code previously marked "done": a 2,140-line guardrails subsystem wired into nothing, the ReAct agent silently bypassed by a regex fallback for 7 of 9 "high-value" accuracy fixtures, auth that fails open on unmapped HTTP methods, an arbitrary file-read endpoint, and an admin secret logged in plaintext. Read `projectmgmt/REMEDIATION_PLAN.md` in full before starting — it explains the sequencing and the merge-first duplicate clusters.

## Request

Read, in order: `comms/PROTOCOL.md` (v2, especially §7 — the new guardrails), `comms/RACI.md` (v2), `projectmgmt/REMEDIATION_PLAN.md` §4 (your full queue, 51 items across 4 waves).

Start with **Wave 1 (critical, 9 items)**, prioritized in this order for maximum blast-radius reduction:

1. `BLK-264` — gate the PDF fallback behind the actual "no LLM configured" condition instead of calling it unconditionally. One-line condition fix per the audit, but re-verify/re-label any accuracy claim that depended on the 7 affected fixtures.
2. `BLK-287` — same root cause, second-order finding (hallucinated success).
3. `BLK-215` / `BLK-241` — auth fail-open and arbitrary file read. **Security-tagged: route to opencode for co-sign before this can close (PROTOCOL §7.4).**
4. `BLK-265` — guardrails subsystem: wire it in for real, or delete it and its docstring's claims. Do not leave it half-true.
5. `BLK-240`, `BLK-218`, `BLK-270`, `BLK-280`.

Before touching `BLK-186`/`BLK-188`, `BLK-191`/`BLK-234`, or `BLK-251`/`BLK-267` — these are content-duplicate pairs (§2 of the plan). Merge them into one ticket first; don't implement the same fix twice under two IDs.

## Acceptance Criteria

- [ ] Acknowledge this message and confirm you've read PROTOCOL.md v2 §7 in full
- [ ] Confirm your understanding that `status: verifying` (not `done`) is what you set when you believe an item is finished — cline closes it, not you
- [ ] Start on Wave 1 item #1 (`BLK-264`) and report back with a plan before implementing, given its blast radius on accuracy claims

## Constraints

- No self-certification. Every Resolution needs attached Evidence (exact test/curl output, file:line references) per PROTOCOL §7.2, or cline will bounce it.
- Phase 5 (ADAS) work is frozen — do not pick up BLK-067/068/069/070/071 etc. regardless of what any prior comms thread said.
- `src/tests/` is no longer yours to edit — if a fix needs a new test, describe what test is needed in your Resolution and let cline write it (or coordinate directly with cline's inbox).

## Notes

Full audit: `ADE_codebase_audit.md`. Full plan: `projectmgmt/REMEDIATION_PLAN.md`. Your queue counts: 9 critical, 12 high, 23 medium, 7 low.
