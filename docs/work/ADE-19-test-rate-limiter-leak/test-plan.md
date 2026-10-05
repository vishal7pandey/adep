# ADE-19 — Test plan: rate limiter state leaks between tests

Status: plan-approved · Risk: low · Jira: ADE-19

Test framework and conventions found: pytest, `src/tests/`, run with
`python -m pytest src/tests/ -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_limiter_isolation.py::TestLimiterIsolation | test_b sees an empty limiter after test_a drained a bucket | n/a: a single drained bucket is the minimal leak | n/a: no invalid input, state isolation only | verified |
| AC1 | integration | src/tests/test_session_mgmt.py::TestDuplicateRun (existing) | passes in the full run | n/a: existing test | 404 case (`test_duplicate_not_found`) passes in full run | verified |
| AC2 | integration | src/tests/test_agent_control.py::TestStopEndpoint::test_stop_running_run (existing) | 20 of 20 runs pass | n/a: repetition is the check | n/a: existing test | verified |
| AC3 | integration | full non-integration suite | no 429 failures | n/a: whole-suite check | n/a: whole-suite check | verified |

## Regression risk

`test_rate_limiting.py` builds its own app and must stay green (it did in the full run).

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

AC1: before the fixture was added, test_b failed with `assert 1 == 0`; after, it passes (both observed).
