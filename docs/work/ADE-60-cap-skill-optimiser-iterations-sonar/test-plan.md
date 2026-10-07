# ADE-60 — Test plan: Cap skill optimiser iterations (Sonar S6680 ADE-60, ADE-61, ADE-62)

Status: draft · Risk: medium · Jira: ADE-60

Test framework: pytest via `uv run python -m pytest`; tests in `src/tests/test_*.py`, `unittest.mock.patch` for the model call.
Command for all: `uv run python -m pytest src/tests -q -m "not integration"`; baseline: 2 known failures (ADE-23, ADE-24).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `src/tests/test_iteration_limits.py`: `TestGepaIterationLimit::test_loop_never_runs_past_the_limit[...]`, `TestMctsIterationLimit::...`, `TestCoEvolveIterationLimit::...`, `test_module_limit_matches_the_api_request_limit[...]` | a request of exactly the limit (50, 100, 10) runs exactly that many rounds | limit+1 (51, 101, 11) is clamped to the limit | 10**9 is clamped to the limit (a counting stub raises past limit+3 so a regression fails instead of hanging); module constants equal the API request limits | verified |
| AC2 | integration | `src/tests/test_iteration_limits.py::Test*::test_a_value_below_the_limit_is_untouched`; existing `test_prompt_evolver.py`, `test_workflow_optimizer.py`, `test_skill_composer.py` | 4, 4 and 2 requested rounds run exactly 4, 4 and 2 and report "Reached max iterations (4)" | n/a: the limit boundary is AC1 | n/a: no new abuse input beyond AC1 | verified |
| AC3 | manual | n/a (scanner re-query) | Sonar API shows the three issues CLOSED after the push scan | n/a: single state read per issue | OPEN: the ticket stays open, the fix is improved, never dismissed | planned (after merge) |

## Regression risk

Existing loop tests use small values (3, 4, 20) and stay below the limits. The API tests for `/skills/optimize`, `/skills/optimize-workflow`
and `/skills/co-evolve` keep passing (request limits unchanged).

## Untestable AC

None. AC3 is a scanner read.

## Manual checks

AC3: after merge and the push scan, `https://sonarcloud.io/api/issues/search?issues=<key>&componentKeys=vishal7pandey_adep`
for `AaESHmBojNIvKL1jZh97`, `AaESHmBOjNIvKL1jZh9u`, `AaESHmBxjNIvKL1jZh-B`; read `status` and `resolution`.

## Audit (after implementation)

<!-- filled after implementation -->
