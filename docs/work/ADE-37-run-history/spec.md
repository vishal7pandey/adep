# ADE-37 — Engine: run history store (SQLite-backed, no global lock)

Status: spec-approved · Risk: low · Jira: ADE-37
Created: 2026-10-05 · Slug: run-history

Part of the ADE-30 vertical slice (`docs/work/ADE-30-engine-vertical-slice/spec.md`). No dependency on
the other stories.

## Problem

The new engine's loop (ADE-39) streams a sequence of events per run (thoughts, tool calls, tool results,
validation outcomes) and needs a durable record of them — for replay, debugging, and eventually ADE-31's
head-to-head evaluation. Nothing in the new engine tracks this yet (ADE-34/35/36 are all pure, in-memory
modules with no persistence).

## Users and context

The new engine's loop (ADE-39), which records each step as it streams. Grounded in reading ade2's
`src/ade2/history.py` in full and ade's existing `src/api/routes/runs.py` / `src/documents/store.py`
(confirms ade's existing run tracking is file-based via `DocumentStore`, a different system this story
does not touch or replace — this is a new, separate trace store for the new engine's own runs, which are
not reachable from the live API yet per ADE-30 AC3).

**The defect, read directly from ade2's `history.py`:** every function (`start_run`, `record_event`,
`complete_run`, `error_run`, `list_runs`, `get_run`, `get_run_events`) wraps its synchronous `sqlite3`
call in one module-level `threading.Lock`. The async wrappers only offload the already-locked call via
`asyncio.to_thread` — so the event loop isn't blocked directly, but every concurrent run's DB writes are
still serialized against each other through that one lock. ADE-12 flags this explicitly as not to port.

## Goals and non-goals

**Goals**
- The same durable record ade2's design provides: a `runs` table (one row per run, status/answer/cost)
  and an `events` table (one row per streamed step), with sync functions plus `asyncio.to_thread` async
  wrappers for FastAPI's event loop — same shape as ade2, minus the lock.
- Prove, not just assert, that concurrent writes are correct without a shared lock.

**Non-goals**
- Replacing or touching ade's existing `DocumentStore`/`src/api/routes/runs.py` — unrelated system, not
  in scope.
- A connection pool or `aiosqlite` — SQLite's own file-level locking plus a short-lived
  connection-per-call (already how ade2 opens connections, just without wrapping them in a shared
  `threading.Lock`) is enough for this slice; revisit only if ADE-31's evaluation load actually shows
  contention.

## Requirements

- R1. Two tables, same columns as ade2's: `runs` (run_id PK, document_id, filename, skill_id, mode,
  page_count, status, answer, num_turns, total_cost_usd, error, created_at, completed_at) and `events`
  (autoincrement id, run_id FK, event_type, step, data, timestamp).
- R2. Sync functions `init_db`, `start_run`, `record_event`, `complete_run`, `error_run`, `list_runs`,
  `get_run`, `get_run_events` — each opens its own connection, does its work, closes it. No shared lock
  object anywhere in the module.
- R3. `async_*` wrappers for every sync function, via `asyncio.to_thread`, for use from the new engine's
  (eventually async) loop.
- R4. Concurrent calls from multiple async tasks must not corrupt or drop data — proven by a test, not
  assumed from "SQLite handles its own file locking."

## Acceptance criteria

- AC1. (R1) `init_db()` on a fresh temp file creates both tables with the documented columns; calling it
  again on the same file is a no-op (idempotent, `CREATE TABLE IF NOT EXISTS`).
- AC2. (R2) `start_run` → `record_event` (x3) → `complete_run` on one `run_id` leaves `get_run(run_id)`
  with `status="completed"`, the right `answer`/`num_turns`/`total_cost_usd`, and `get_run_events(run_id)`
  returning exactly 3 events in insertion order.
- AC3. (R2) `error_run` on a run leaves `status="error"` with the given message in `error`; `completed_at`
  is set.
- AC4. (R3) Each `async_*` wrapper produces the identical result its sync counterpart would for the same
  inputs (call both, compare).
- AC5. (R4) `asyncio.gather` over 10 concurrent `async_start_run` + `async_record_event` calls for 10
  distinct `run_id`s leaves all 10 runs present, each with its own event recorded — no lost writes, no
  cross-run data mixing, and no exception from the concurrent access.
- AC6. No test in this story's suite asserts on, requires, or reintroduces a module-level
  `threading.Lock` or any other shared mutex.
- AC7. Hermetic: every test uses a temp SQLite file (`tmp_path`), never the real history DB path.

## Edge cases and failure modes

- `get_run`/`get_run_events` on a nonexistent `run_id`: return `None` / `[]` respectively, not an error.
- `record_event` on a `run_id` that was never started (no row in `runs`): still inserts into `events`
  (no foreign-key enforcement assumed; SQLite doesn't enforce FKs by default) — document this rather
  than silently relying on it.

## Non-functional requirements

- Observability: `logger = logging.getLogger(__name__)`; `start_run`/`complete_run`/`error_run` log at
  INFO/ERROR as ade2's did.

## Assumptions

- The DB file path is a module-level constant computed from `src.config` or a similar existing
  settings/paths module if one exists and is easy to reuse; otherwise a sibling path next to wherever
  ade's own `.adep/` runtime data lives (read `src/documents/store.py` for the existing convention before
  inventing a new one).

## Risks and dependencies

- Risk: low — new, isolated module; the only real risk is the concurrency claim, which AC5 specifically
  tests rather than assumes.
- Depends on: nothing. Used by: ADE-39 (the engine loop's event-recording calls).
