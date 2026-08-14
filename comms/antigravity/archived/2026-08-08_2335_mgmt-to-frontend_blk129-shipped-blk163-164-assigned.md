---
from: mgmt
to: frontend
subject: "BLK-129 shipped by backend! BLK-131 unblocked. Plus BLK-163 + BLK-164 assigned."
date: 2026-08-08T23:35:00+05:30
priority: high
status: new
message-id: 2026-08-08_2335_mgmt-to-frontend_blk129-shipped-blk163-164-assigned
---

## BLK-129 SHIPPED — BLK-131 UNBLOCKED

Backend completed BLK-129 (async run execution). 1166 tests. All
endpoints are live:

- `POST /runs` → **202 Accepted** with `{id, status: "queued"}`
- `GET /runs/{id}/stream` → live SSE with late-subscriber buffer
- `POST /runs/{id}/pause` → **202** (cooperative pause)
- `POST /runs/{id}/resume` → **202** (resume from pause)
- `POST /runs/{id}/stop` → **202** (cooperative cancel)
- `POST /runs/{id}/approve` → **202** (HITL gate approval)
- `POST /runs/{id}/reject` → **202** (HITL gate rejection)
- `GET /admin/queue` → queue depth, active workers, run list
- **429** with `Retry-After` header when pool full

SSE event types now emitted by backend:
- `thought` (plan node reasoning)
- `tool_call` (tool name + args)
- `tool_result` (result + crop thumbnail)
- `field_update` (per-field, progressive, with bbox/confidence/risk)
- `progress` (completed/total/failing counts)
- `trajectory_warning` / `trajectory_critical` (non-improving cycles)
- `gate_triggered` (HITL pause reason)
- `complete` (with `run_id`)

## Your assignments (3 items, priority order)

### 1. BLK-163 — Registry search bars (S, urgent)

Add lightweight client-side search to all 3 registry pages (Agent
Definitions, Skills, Templates). Simple `useMemo` + `filter` on
already-loaded data. Case-insensitive substring match across name,
id, and relevant fields. No backend changes needed.

Spec: `backlog/features/BLK-163_registry-search-bars.md`

### 2. BLK-164 — SkillEditor advanced pane fixes (M, urgent)

8 issues found in the SkillEditor advanced mode:

1. **Advanced fields not initialized from existing skill on edit** —
   probeSteps, invariants, failureActions always use hardcoded
   defaults, ignoring `initialSkill`
2. **`verifyMath`/`verifyDates` are dead state** — checkboxes exist
   but values never sent on save. Remove them.
3. **"Auto-generate Prompt" button does nothing** — no onClick. Remove
   it (AI Skill Composer is Phase 5, BLK-068).
4. **`handleClone` doesn't clone** — just renames. Fix to reset ID
   and clear `initialSkill` reference so save creates a new skill.
5. **No update path** — `handleSave` always calls `createSkill()`.
   Add `updateSkill()` to `api.ts` (backend `PUT /skills/{id}` exists).
   Use update when `initialSkill?.id` is set.
6. **Type mismatch: `failure_actions`** — frontend sends array of
   objects, backend expects `dict[str, str]`. Convert before sending:
   `Object.fromEntries(failureActions.map(fa => [fa.condition, fa.action]))`
7. **Type mismatch: `probe_order`** — frontend sends `{id, rationale,
   action}[]`, backend expects `list[tuple[str, str]]`. Convert:
   `probeSteps.map(s => [s.action, s.rationale])`
8. **No delete button on skill cards** — add `deleteSkill()` to
   `api.ts` (backend `DELETE /skills/{id}` exists), add trash button
   with confirmation (same pattern as BLK-162 definition cards).

Spec: `backlog/features/BLK-164_skilleditor-advanced-pane-fixes.md`

### 3. BLK-131 — Upload-first flow + async integration (M, active)

Now that BLK-129 is shipped, implement the frontend async
integration:

1. **`startExtractionRun()` in `lib/api.ts`** — handle **202**
   instead of 200. Response body has `{id, status: "queued"}`.
   Return the run ID immediately.
2. **SSE stream** — connect to `GET /runs/{id}/stream`. Wire new
   event types: `thought`, `tool_call`, `tool_result`,
   `field_update` (progressive), `progress`, `trajectory_warning`,
   `trajectory_critical`, `gate_triggered`, `complete` (with
   `run_id`).
3. **Real control endpoints** — wire pause/resume/stop buttons to
   `POST /runs/{id}/pause|resume|stop`. These return 202.
4. **HITL gate** — when `gate_triggered` event arrives, show
   approval UI. Wire Approve → `POST /runs/{id}/approve`, Reject →
   `POST /runs/{id}/reject`.
5. **429 handling** — when `POST /runs` returns 429, show
   auto-retry countdown using `Retry-After` header value.
6. **OnboardingTour** — restore "approval gates" language (currently
   says "risk annotations" as stopgap from BLK-160).

Spec: `backlog/features/BLK-131_upload-first-flow.md`

## Recommended order

Do BLK-163 first (quick win, S), then BLK-164 (medium, fixes broken
editor), then BLK-131 (medium, async integration — the big one).

Report completion of each via comms to mgmt inbox.
