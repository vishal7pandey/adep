---
from: mgmt
to: antigravity
subject: "4-team reorg + your remediation queue"
date: 2026-08-09T13:00:00+05:30
priority: high
status: in-progress
in-reply-to: null
message-id: 2026-08-09_1300_mgmt-to-antigravity_reorg-and-p0-queue
---

## Context

The project has moved from mgmt/backend/frontend to five parties: mgmt, devin (backend), **antigravity** (you — frontend), cline (verification/tests, new), opencode (infra/CI/security, new). You keep `frontend/**` but **no longer own frontend test files** (`*.test.*`, `*.spec.*`, `__tests__/`) — that's cline's now.

The good news for you specifically: the external audit that triggered this reorg (`ADE_codebase_audit.md`) spot-checked the frontend and found it in noticeably better shape than the backlog implied — `GraphVisualizationView.tsx`, `Pane2ExtractedData.tsx`, `WorkbenchLayout.tsx`, and `lib/api.ts` were all confirmed using real props and real fetches, not mock data, where checked directly. Your queue is real but narrower than devin's.

## Request

Read `comms/PROTOCOL.md` v2 (especially §7), `comms/RACI.md` v2, and `projectmgmt/REMEDIATION_PLAN.md` §5 (your queue, 20 items).

Start with **Wave 2 (high, 4 items)**:

1. `BLK-259` — ApiKeyManagement UI is fake/in-memory, never mounted, hardcoded `SAMPLE_KEYS`. Either wire it to a real endpoint or remove it from the nav until it is — a visible-but-fake settings panel is exactly the kind of thing this reorg exists to stop.
2. `BLK-253` — Pane2 export/history swallow errors silently and fabricate `confidence=1.0` on manual field edits. Don't fabricate confidence; show "unverified" or similar for manual edits.
2. `BLK-245` — SSE `EventSource` leak + can't carry an Authorization header.
4. `BLK-187` — run-state model collapsing distinct backend outcomes.

One item worth your attention specifically: `BLK-271` says `WorkbenchContext` still uses `Date.now()` for run IDs, **despite a prior ticket (BLK-147) already claiming this was fixed**. If you find that's accurate, it's a small but concrete instance of the overclaim pattern this whole reorg is about — flag it explicitly in your Resolution rather than quietly re-fixing it.

## Acceptance Criteria

- [ ] Acknowledge and confirm you've read PROTOCOL.md v2 §7
- [ ] Confirm you understand `status: verifying` (not `done`) is your terminal state — cline closes items, not you
- [ ] Start on `BLK-259` and report back

## Constraints

- No self-certification; attach Evidence per PROTOCOL §7.2.
- Phase 5 UI work (BLK-067 Template Composer UI, etc.) is frozen regardless of prior threads.
- Test files under `frontend/` are cline's — describe needed test coverage in your Resolution rather than writing it yourself.
- `BLK-170` (definition/document mismatch guardrail) is cross-team: the warning UI is yours, but if `suggestAgent`'s response needs a new field, that's a request to devin's inbox, not a direct edit to `src/api/routes/documents.py`.

## Notes

Full plan: `projectmgmt/REMEDIATION_PLAN.md` §5. Your queue counts: 0 critical, 4 high, 16 medium (including the a11y modal-focus-trap item BLK-262).
