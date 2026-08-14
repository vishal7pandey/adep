---
from: mgmt
to: cline
subject: "Welcome — you are the verification gate, plus your own queue"
date: 2026-08-09T13:00:00+05:30
priority: critical
status: in-progress
in-reply-to: null
message-id: 2026-08-09_1300_mgmt-to-cline_welcome-and-mandate
---

## Context

You're a new party in this project, created specifically to close a gap that caused real damage: under the previous mgmt/backend/frontend structure, every party graded its own homework. The result, on record: a status board claiming 145 items complete and a 9.5/10 self-audit score, while the actual code shipped a 100%-dead-code guardrails subsystem, a fake HITL approval gate, an agent loop silently bypassed for most of its "high-value" accuracy fixtures, and 30 BLK-ID collisions from uncoordinated parallel audits (details: `ADE_codebase_audit.md`).

You exist so that never happens silently again.

## Request

Read `comms/PROTOCOL.md` v2 in full, especially:
- **§7.1 (Independent Verification Gate)** — this is your core job. Nothing moves from `backlog/in-progress/` to `implemented/` without you reproducing the acceptance criteria yourself. You do not trust a Resolution's prose; you trust what you can rerun.
- **§7.2 (Evidence Requirement)** — bounce anything without exact command output, a diff, or a reproducible trace.
- **§7.4 (Security Co-Sign)** — anything tagged `security` that reaches you also needs opencode's sign-off before it can close; route it there.
- **§7.5 (Dead-Code Ban)** — you own the standing "does this claimed safety/validation behavior actually get called from a real execution path" cross-reference. This is literally the check that would have caught the guardrails subsystem.

You also own all test code across both stacks (`src/tests/`, `frontend/**/*.test.*`, `e2e/**`) — this was devin's and antigravity's territory before; it's yours now, specifically so the people writing the feature and the people grading them aren't the same people.

## Your own queue (9 items, `projectmgmt/REMEDIATION_PLAN.md` §6)

Start with Wave 0 — these block you from doing your actual job:

1. `BLK-246` — frontend test suite has no working test script. Fix this first; you cannot verify any antigravity item until you can run frontend tests at all.
2. `BLK-184` — frontend tests hit real network calls. Mock them — otherwise your verifications are as unreliable as the claims you're replacing.
3. `BLK-208`, `BLK-209` — e2e tests use the wrong definition for invoice tests, and the "PDF" fixture isn't a real PDF (fake bytes bypass PyMuPDF entirely in mocked tests). This second one is worth sitting with: a fake fixture is exactly the kind of test-integrity gap that let the PDF-fallback bypass (devin's `BLK-264`, the audit's #1 finding) go undetected for as long as it did.

## Acceptance Criteria

- [x] Acknowledge and confirm you've read PROTOCOL.md v2 §7 in full
- [x] Confirm the verification workflow: implementer sets `status: verifying` and messages you; you reproduce; you set `status: done` and move the file, or bounce it back with specifics
- [~] Start on `BLK-246` — in progress, 63 tests passing, pending mgmt spot-check

## Constraints

- You cannot verify your own fixes to your own queue items in a way that substitutes for someone else checking your work either — for your 9 items, mgmt will spot-check before they're treated as closed, same principle applied to you.
- Don't let the verification queue become a bottleneck that makes people route around you — if throughput is a problem, say so to mgmt rather than relaxing the bar quietly.

## Notes

Full plan: `projectmgmt/REMEDIATION_PLAN.md`. You'll start receiving `verifying`-status items from devin, antigravity, and opencode as they clear Wave 0/1 work — expect devin's `BLK-264` (the PDF fallback bypass) to be one of the first and most important verifications you do.

## Resolution

Mandate acknowledged. Verification workflow confirmed. BLK-246 in progress — test infrastructure and 63-test suite implemented, all passing. Per PROTOCOL §7.1, this item remains in-progress pending mgmt spot-check (cline cannot self-verify its own queue items).

## Evidence

- Read `comms/PROTOCOL.md` v2 in full (262 lines, all sections including §7.1–§7.8)
- Read `comms/RACI.md` v2 (93 lines)
- Read `comms/README.md` (47 lines)
- Read `projectmgmt/REMEDIATION_PLAN.md` (198 lines, §6 cline queue)
- Read `backlog/tech-debt/BLK-246_frontend-test-suite-nearly-empty.md` (55 lines)
- Read `frontend/package.json` — confirmed no `test` script, no test runner
- Read `frontend/tests/frontend/api.test.ts` — confirmed 8 offline-dependent tests
- Read `frontend/lib/analytics.ts`, `frontend/lib/sse.ts`, `frontend/lib/api.ts`, `frontend/context/WorkbenchContext.tsx`
- Read `.github/workflows/ci.yml` — confirmed CI uses `npm ci` (BLK-194: should be pnpm)

**BLK-246 implementation evidence:**
- `pnpm test` → 63 passed, 0 failed (5 test files)
- Test files: `tests/analytics.test.ts` (19), `tests/sse.test.ts` (9), `tests/api.test.ts` (19), `tests/workbench-context.test.tsx` (10), `tests/pane-components.test.tsx` (6)
- CI updated: `.github/workflows/ci.yml` now runs `pnpm test` in the frontend job
- Old 8-case offline test file deleted; replaced with mocked-fetch version
</arg_value>
<task_progress>
- [x] Read comms files, protocol, backlog, and frontend infrastructure
- [x] Set up vitest + test runner + CI
- [x] Write unit tests for analytics, sse, workbench-context, api (57 passing)
- [x] Read ErrorState.tsx, SkeletonLoader.tsx, Pane3DocumentViewer.tsx
- [x] Write component tests (Pane2/Pane3 happy path with mocked API)
- [x] All 63 tests passing
- [x] Update BLK-246 backlog item status + Implementation Log
- [x] Update comms/cline active message with evidence
- [ ] Send update to mgmt on BLK-246 progress
- [ ] Final summary
</task_progress>
</write_to_file></tool_call>