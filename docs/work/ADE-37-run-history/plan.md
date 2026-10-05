# ADE-37 — Plan: run history store

Status: plan-approved · Risk: low · Jira: ADE-37
Created: 2026-10-05 · Slug: run-history · Spec: spec.md

## Summary

One new module, `src/engine/history.py`, ported from ade2's `src/ade2/history.py` (read in full) with the
module-level `threading.Lock` removed and every function taking an explicit `db_path` (defaulting to a
module constant under `.adep/`, matching ade's existing `store_db_path = ".adep/store.db"` convention in
`src/config.py`) so tests pass a `tmp_path` file directly instead of monkeypatching a global. **Size:** S.

## Current state

- `src/engine/` has `skills.py`, `budget.py`, `validation.py` (ADE-34/35/36); this story adds a sibling
  module, no changes to any of them.
- `src/config.py::Settings.store_db_path` is ade's *existing*, unrelated `DocumentStore` DB path
  (`.adep/store.db`) — this story does not touch it; the new engine's history DB is a sibling file
  (`.adep/engine_history.db`), kept deliberately separate since it is a different system.
- Commands: `uv run pytest src/tests/ -v -m "not integration"`, `uv run ruff check src/`,
  `uv run ruff format src/`.

## Approach

1. Same two tables as ade2 (`runs`, `events`), same columns.
2. Every function takes `db_path: Path | None = None` (defaults to the module constant
   `DEFAULT_DB_PATH`); opens its own `sqlite3.connect(db_path)`, does its work, closes it. No shared
   lock — SQLite's own file-level locking under concurrent writers is what's actually being relied on
   (as ade2 already relied on, minus the pretense that an in-process lock was adding anything beyond
   serializing unnecessarily).
3. `async_*` wrappers via `asyncio.to_thread`, same shape as ade2, each forwarding `db_path`.
4. `init_db(db_path)` is **not** auto-called at import time (ade2 calls `init_db()` at module load,
   which would touch disk just from `import ade2.history` — undesirable for a module other code might
   import without wanting a DB file created). Callers (ADE-39, and this story's own tests) call
   `init_db` explicitly.

**Alternatives rejected**
- Keeping the lock "just to be safe": defeats the point of this story, which exists specifically because
  ADE-12 flags the lock as the thing not to carry over. AC5's concurrency test is the actual safety net.
- `aiosqlite` or a connection pool: more machinery than this slice needs; revisit if ADE-31 shows real
  contention.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing tests first (red) | `src/tests/test_engine_history.py` | AC1-AC7 | tests fail (no module yet) |
| T2 | `src/engine/history.py` | `src/engine/history.py` | AC1-AC7 | tests pass |

## Data, API and migration impact

None — new, inert module; nothing calls it yet, and `init_db` is not auto-run at import.

## Security and failure modes

None beyond what's in the spec. A `record_event` for a `run_id` with no `runs` row still inserts (SQLite
doesn't enforce FKs by default here) — documented, not treated as an error.

## Rollout and rollback

Merge; revert to undo. No migration, no runtime behavior change.

## Risks and open points

None beyond what's in the spec (the concurrency claim is tested, not assumed).
