---
from: mgmt
to: backend
subject: "Stabilization review — 8 bugs + 2 tech-debt items found (BLK-088 to BLK-100)"
date: 2026-08-08T02:40:00+05:30
priority: high
status: new
message-id: 2026-08-08_0240_mgmt-to-backend-stabilization-review
---

## Summary

Full code review of the backend completed. Found **8 bugs and 2
tech-debt items**. These are stabilization fixes — no new features.
Fix these before starting BLK-087 (prebuilt catalogue).

## Bugs (fix in priority order)

### BLK-088 — Run engine skill/template registry incomplete (HIGH)

`src/api/run_engine.py` lines 33-42: Only `invoice` is registered.
The 3 other implemented skills (`trade_finance`,
`bill_of_quantities`, `utility_bill`) are missing. Any run using
those skills fails with `ValueError`.

**Fix:** Add all 4 skills + templates to the registries.

### BLK-091 — API field name mismatch: skill_ref vs skill_id (HIGH)

Backend uses `skill_ref`/`template_ref`. Frontend uses
`skill_id`/`template_id`. Definitions created from the frontend have
empty skill/template refs. Runs fail.

**Fix:** Pick one convention. I recommend `skill_id`/`template_id`
(matches frontend). Update `CreateDefinitionRequest`,
`UpdateDefinitionRequest`, `run_engine.py`, and
`AgentDefinition` model.

### BLK-093 — Start run field mismatch: document_path vs document_url (HIGH)

Backend expects `document_path`. Frontend sends `document_url`.
Runs fail with empty document path.

**Fix:** Align field name. Use `document_path` everywhere.

### BLK-090 — SSE stream replays, not live (HIGH)

`POST /runs` blocks until completion. SSE is a replay. Pause/resume/
stop are no-ops. This blocks the entire frontend Agent Console UX.

**Fix:** Either (A) background task + live emitter, or (B) document
the limitation and have the frontend adapt. Recommend A for v1.1.

### BLK-092 — Store not seeded with prebuilt content (HIGH)

Fresh install has empty `.adep/` directories. `GET /skills`,
`GET /templates`, `GET /definitions` all return `[]`. Frontend falls
back to mock data, masking the problem.

**Fix:** Add `seed_store()` called on first boot. Seed all 4
existing skills, templates, and at least 1 prebuilt definition.

### BLK-095 — RunStatus.PAUSED not defined (MEDIUM)

`reflect_node` sets `status = "paused"` (string literal) but
`RunStatus` has no `PAUSED` constant. `should_continue` doesn't
check for it → infinite loop. `map_status_to_frontend` maps it to
`"failed"`.

**Fix:** Add `PAUSED = "paused"` to `RunStatus`. Update
`should_continue` and `map_status_to_frontend`.

### BLK-094 — Max cycles override broken (MEDIUM)

`run_engine.py` line 169: `state["total_cycles"] = 0` — resets a
value that's already 0. The actual override is never applied.

**Fix:** Pass `max_cycles_per_document` to the graph or use
LangGraph's `recursion_limit`.

### BLK-096 — build_initial_state missing 5 keys (MEDIUM)

`document_state`, `consecutive_non_improving`, `token_usage`,
`total_tokens`, `total_cost_usd` are declared in `AgentState` but
not initialized. Works by accident via `.get()` defaults.

**Fix:** Add all 5 keys to the return dict in `build_initial_state`.

## Tech Debt

### BLK-089 — Duplicate _get_run_or_404 in runs.py (LOW)

Defined twice (line 26 and line 327). Identical implementations.
Remove the second.

### BLK-099 — field_attempts incremented on success (MEDIUM)

`_process_tool_result` increments `field_attempts` on successful
extractions. Should only increment on failure (already handled in
observe_node). Give-up caps trigger prematurely.

**Fix:** Remove lines 876-877 from `_process_tool_result`.

### BLK-100 — _INJECTION_PATTERS typo (LOW)

Missing `N` — should be `_INJECTION_PATTERNS`. Rename constant
and update reference.

## Recommended Fix Order

1. BLK-088 (registry) — unblocks all non-invoice runs
2. BLK-091 (field names) — unblocks frontend ↔ backend communication
3. BLK-093 (document field) — unblocks starting runs from frontend
4. BLK-092 (seeding) — unblocks fresh install usability
5. BLK-095 (RunStatus.PAUSED) — prevents infinite loop
6. BLK-096 (missing state keys) — prevents subtle state bugs
7. BLK-094 (max cycles) — correct config application
8. BLK-099 (field_attempts) — correct give-up behavior
9. BLK-089 (duplicate function) — cleanup
10. BLK-100 (typo) — cleanup

Items 1-4 are **critical** — they block end-to-end functionality.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
