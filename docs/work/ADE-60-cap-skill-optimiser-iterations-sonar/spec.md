# ADE-60 — Cap skill optimiser iterations (Sonar S6680 ADE-60, ADE-61, ADE-62)

Status: draft · Risk: medium · Jira: ADE-60
<!-- Security finding: neutral wording on purpose; this repo is public. -->

Covers three SonarCloud findings, one rule (`pythonsecurity:S6680`, CRITICAL vulnerability: unchecked input controls a loop condition):

| Jira | Sonar issue | Location | Function |
|------|-------------|----------|----------|
| ADE-60 | `AaESHmBojNIvKL1jZh97` | `src/ai/prompt_evolver.py:752` | `optimize_skill` (GEPA loop) |
| ADE-61 | `AaESHmBOjNIvKL1jZh9u` | `src/ai/workflow_optimizer.py:658` | `optimize_workflow` (MCTS loop) |
| ADE-62 | `AaESHmBxjNIvKL1jZh-B` | `src/ai/skill_composer.py:546` | `co_evolve_skill` |

ADE-60 is the key of this work item; the others close separately, each on its own re-queried Sonar issue. Only these three issues are in scope.

## Repro

Environment: `master` @ ce93e7c, Python 3.14 venv, Windows; platform independent.

Automated repro: `src/tests/test_iteration_limits.py`, run `uv run python -m pytest src/tests/test_iteration_limits.py -q`.
On current code 9 of 15 tests fail (6 pass: boundary and below-limit cases that pin existing behaviour):
- For each loop, a `max_iterations` of limit+1 or 10**9 runs past the documented limit (a counting stub raises after a few extra
  rounds so the test fails instead of hanging): GEPA reflects 54 times instead of stopping at 50, MCTS selects 104 times instead
  of 100, co-evolution verifies 14 times instead of 10.
- Three drift-guard tests fail with `AttributeError`: the module limit constant does not exist.

Reproducibility: always.

## Expected

Each loop never runs more than a documented module limit, equal to the limit the API request model already enforces:
`MAX_GEPA_ITERATIONS = 50` (`OptimizeSkillRequest`), `MAX_MCTS_ITERATIONS = 100` (`OptimizeWorkflowRequest`),
`MAX_CO_EVOLUTION_ITERATIONS = 10` (`CoEvolveSkillRequest`). A larger `max_iterations` is clamped to the limit, with a warning
log; the result reports the limit that was applied ("Reached max iterations (50)"). Values at or below the limit, including zero
or negative, behave as before.

## Actual

`for iteration in range(1, max_iterations + 1)` (and `range(max_iterations)` in `co_evolve_skill`) use the caller's value as is.
The API model caps the request (`le=50`, `le=100`, `le=10`), but the three functions are public library entry points (also called by
scripts and tests), and nothing stops a direct call with a huge count: each iteration makes paid model calls.

## Root cause (with evidence)

- Where: `prompt_evolver.py:752`, `workflow_optimizer.py:658`, `skill_composer.py:546`.
- Why it fails: the bound is validated only at the HTTP boundary, not where it is used as a loop condition; Sonar's taint flow runs
  from the request model through the route to each loop.
- Introduced by: always present (original implementations).
- Evidence: the 9 failing tests; Sonar flows end at the three `range(...)` calls.

## Blast radius

- Callers: `src/api/routes/skills.py` (`/skills/optimize`, `/skills/optimize-workflow`, `/skills/co-evolve`, already limited by the
  request model to the same numbers, so no HTTP behaviour changes) and tests that pass small values (3, 4, 20).
- No other loop in these modules takes a caller-supplied count (checked `grep max_iterations` in the three files).
- Data affected: none.

## Regression criterion (AC1)

AC1: The failing tests in `src/tests/test_iteration_limits.py` pass after the fix and fail on the current code: each loop runs
exactly its limit for a requested limit, limit+1 and 10**9, and the module constants equal the API limits.

AC2: Behaviour below the limit is unchanged (a request of 4, 4 and 2 iterations runs exactly that many; the existing tests in
`test_prompt_evolver.py`, `test_workflow_optimizer.py`, `test_skill_composer.py` stay green) and the backend suite stays at its known
baseline (`-m "not integration"`: only ADE-23 and ADE-24 fail).

AC3: After the merge and the push scan, the Sonar API shows the three issues (`AaESHmBojNIvKL1jZh97`, `AaESHmBOjNIvKL1jZh9u`,
`AaESHmBxjNIvKL1jZh-B`) CLOSED (verified after merge; each Jira ticket closes only on its own issue).

## Fix constraints

- Clamp inline at the loop: `max_iterations = min(max_iterations, MAX_..._ITERATIONS)` with a warning when it clamps. No shared
  helper (keeps the bound visible to the scanner at each loop). Limits documented in the function docstring.
- Minimal diff: the three functions plus module constants, the new test file, this folder. No API shape change.
- Do not touch other findings or unrelated files.

## Risks

Medium: a direct caller that asked for more than the limit now gets fewer iterations (documented; the API never allowed it).
If Sonar does not accept the `min()` clamp as a sanitizer, the fix is improved (for example an explicit rejection), never dismissed.
Rollback: revert the merge commit.
