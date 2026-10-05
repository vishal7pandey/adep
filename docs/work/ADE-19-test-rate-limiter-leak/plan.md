# ADE-19 — Plan: rate limiter state leaks between tests

Status: plan-approved · Risk: low · Jira: ADE-19
Created: 2026-10-05 · Slug: test-rate-limiter-leak · Spec: spec.md

## Summary

Add an autouse fixture in a new `src/tests/conftest.py` that calls `reset_limiter()` (already provided in
`src/api/rate_limit.py` "for testing") before each test, plus a two-test regression that proves state does
not leak. No production code changes.

**Size:** S

## Current state

`src/api/rate_limit.py` exposes `get_limiter()` / `reset_limiter()`. `src/tests/` has no conftest. Tests run
with `python -m pytest src/tests/ -m "not integration"` (Makefile: `make test`).

## Approach

One autouse function-scoped fixture resetting the singleton. Smallest change that removes the cross-test
state; keeps the secure default.

**Alternatives rejected**
- Set `ADE_RATE_LIMIT_ENABLED=false` for tests: the middleware is only installed when enabled, so that would
  stop the API tests exercising the middleware at all and `test_rate_limit_enabled_by_default` would break.
- Raise the limits in test settings: hides the leak, still order dependent.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Write the regression test, see it fail | `src/tests/test_limiter_isolation.py` | AC1 | fails with `assert 1 == 0` |
| T2 | Add the autouse reset fixture | `src/tests/conftest.py` | AC1, AC3 | regression passes; full suite |
| T3 | Run the stop test 20 times | n/a | AC2 | 20 of 20 pass |

## Data, API and migration impact

None.

## Security and failure modes

No auth or runtime change. The rate-limit tests keep covering the 429 path.

## Rollout and rollback

Merge to master; revert the commit to undo. No deploy.

## Risks and open points

- Remaining failures in the suite belong to ADE-6, ADE-23, ADE-24 and are out of scope.
