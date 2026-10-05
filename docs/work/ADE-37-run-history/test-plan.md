# ADE-37 — Test plan: run history store

Status: implementing · Risk: low · Jira: ADE-37

Test framework and conventions found: pytest, `tmp_path` for a real temp SQLite file (no monkeypatching
needed since `db_path` is an explicit parameter), `pytest.mark.asyncio` (already a dependency, used
elsewhere in `src/tests/`) for the concurrency test; command `uv run pytest src/tests/ -v -m "not
integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_history.py::test_init_db_creates_tables_and_is_idempotent | tables exist with the right columns | calling init_db twice is a no-op | n/a | verified |
| AC2 | unit | ::test_full_run_lifecycle_records_events_in_order, ::test_get_run_and_events_on_nonexistent_run_id | start -> 3 events -> complete; get_run/get_run_events reflect it | n/a | a nonexistent run_id returns None/[] | verified |
| AC3 | unit | ::test_error_run_sets_status_and_message | n/a | n/a | error_run sets status=error, error message, completed_at | verified |
| AC4 | unit (asyncio) | ::test_async_wrappers_match_sync_results | async wrapper result equals sync call's result for the same inputs | n/a | n/a | verified |
| AC5 | integration (asyncio) | ::test_concurrent_async_writes_do_not_lose_data | 10 concurrent run starts + events all present afterward, none cross-contaminated | n/a | n/a | verified |
| AC6 | unit | ::test_module_defines_no_shared_lock | no module-level attribute is a Lock/RLock instance | n/a | n/a | verified |
| AC7 | unit | (all above) | every test uses tmp_path, never the real `.adep/` path | n/a | n/a | verified |

## Regression risk

None — new module, nothing else imports it yet.

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

Red first: all 7 tests failed at collection (`ImportError: cannot import name 'history' from
'src.engine'`) before the module existed. After implementation: all 7 passed on the first run, no test
bugs found this time.

Four mutations applied to the real `src/engine/history.py` (each confirmed to have changed the file via
`diff`), run, then restored (confirmed byte-identical with `diff -q`):

| Mutation | Test(s) run | Result |
|---|---|---|
| M1: `complete_run`'s SQL drops `status='completed'` | `-k lifecycle` | fails (`run["status"]` stays `"running"`) |
| M2: `get_run_events`'s `ORDER BY id ASC` flipped to `DESC` | `-k lifecycle` | fails (events come back in reverse order) |
| M3: `error_run`'s SQL drops setting `completed_at` | `-k error_run` | fails (`completed_at` stays `None`) |
| M4: `get_run_events` drops its `WHERE run_id=?` filter (returns every run's events) | `-k "concurrent or lifecycle"` | the concurrency test fails (10 events returned for one run_id instead of 1) |

Full suite after restoring: `src/tests/test_engine_history.py` 7 passed; `pytest src/tests/ -m "not
integration"` 1820 passed, 9 failed (the same pre-existing ADE-23/ADE-24 failures, unchanged), 19
deselected. `ruff check`/`format --check`: clean.
