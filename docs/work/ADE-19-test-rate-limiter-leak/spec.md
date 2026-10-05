# ADE-19 — Rate limiter state leaks between tests

Status: spec-approved · Risk: low · Jira: ADE-19

## Repro

Environment: master @ 13195ad, Windows dev venv (Python 3.14) and a clean checkout on Python 3.11 (CI's).

1. `python -m pytest src/tests/ -m "not integration"` (about 3 minutes).
2. Observe 24-36 failures, almost all `assert 429 == <expected>`, in `test_agent_control.py`,
   `test_hitl.py`, `test_async_runs.py` and `test_session_mgmt.py` (the duplicate-run tests).

Automated repro: `src/tests/test_limiter_isolation.py::TestLimiterIsolation::test_b_next_test_starts_clean`
fails with `assert 1 == 0` before the fix (an earlier test left a bucket in the limiter).
The two duplicate-run tests themselves pass when run alone (`-k Duplicate`).

Reproducibility: intermittent by timing. The full suite takes longer than the 60 s refill window, so how
many tests are throttled depends on machine speed. The "4 failures" baseline on 2026-10-05 was a lucky run;
a rerun on the same tree gave 33 failures.

## Expected

Each test starts with a fresh rate limiter and is independent of the order and speed of the others.

## Actual

`get_limiter()` (`src/api/rate_limit.py`) is a process-wide singleton holding per-key token buckets. Every
`TestClient` request comes from the same client IP, and `rate_limit_enabled` defaults to True
(`src/config.py`), so the tier buckets (mutating 60/min, POST /runs 10/min) drain across tests and later
requests get 429.

## Root cause (with evidence)

- Where: no test isolation for the singleton; there was no `src/tests/conftest.py` at all.
- Why it fails: shared mutable state (the limiter's `_buckets`) that no fixture resets.
- Introduced by: SCRUM-63 (rate limiting on by default) on top of tests written when it defaulted to off.
- Evidence: failures are 429 responses (49 occurrences in one run); with `ADE_RATE_LIMIT_ENABLED=false` the
  count drops from 31-36 to 12; with the reset fixture the local non-integration run drops from 33 to 4.
  The stop-endpoint flake seen once (AC2) has the same signature.

## Blast radius

Test-only. Production behaviour (limiting on by default) is unchanged. Other tickets share the same cause:
ADE-22 (429 on clean checkout) is fixed by this change.

## Regression criterion (AC1)

AC1: `test_limiter_isolation.py::TestLimiterIsolation::test_b_next_test_starts_clean` fails on the old code
and passes with the autouse reset fixture; `test_session_mgmt.py::TestDuplicateRun` passes in the full
non-integration run.

AC2: `test_agent_control.py::TestStopEndpoint::test_stop_running_run` passes 20 out of 20 runs.

AC3: the full non-integration suite has no 429 failures; the only remaining failures are the separately
tracked ADE-6 (2), ADE-23 (1 locally) and ADE-24 (1).

## Fix constraints

Test code only (`src/tests/conftest.py`, one new test). Do not weaken the production default and keep
`test_rate_limiting.py` testing the real limits.

## Risks

None for production. A test that deliberately depends on accumulated limiter state would now start clean;
`test_rate_limiting.py` builds its own app and passed unchanged.
