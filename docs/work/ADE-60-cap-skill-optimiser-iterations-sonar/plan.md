# ADE-60 — Cap skill optimiser iterations (Sonar S6680 ADE-60, ADE-61, ADE-62)

Status: draft · Risk: medium · Jira: ADE-60
Created: 2026-10-07 · Slug: cap-skill-optimiser-iterations-sonar · Spec: spec.md

## Summary

Add a documented module constant per optimiser (the number the API already enforces) and clamp `max_iterations` with `min()` right
before the loop, logging a warning when the clamp changes the value.

**Size:** S

## Current state

- `src/ai/prompt_evolver.py` `optimize_skill(..., max_iterations: int = 10, ...)`, loop `for iteration in range(1, max_iterations + 1)`
  at line 752; the for-else sets `convergence_reason = f"Reached max iterations ({max_iterations})"`.
- `src/ai/workflow_optimizer.py` `optimize_workflow(..., max_iterations: int = 20, ...)`, loop at line 658, same else-clause shape.
- `src/ai/skill_composer.py` `co_evolve_skill(..., max_iterations: int = 3)`, loop `for i in range(max_iterations)` at line 546.
- `src/api/routes/skills.py` request models: `le=50`, `le=100`, `le=10`.
- Tests: `uv run python -m pytest ...`; failing tests already in `src/tests/test_iteration_limits.py`.

## Approach

1. In each module add `MAX_GEPA_ITERATIONS = 50`, `MAX_MCTS_ITERATIONS = 100`, `MAX_CO_EVOLUTION_ITERATIONS = 10` with a comment saying
   they equal the API request limits.
2. Right before the loop: `if max_iterations > LIMIT: logger.warning(...)`, then `max_iterations = min(max_iterations, LIMIT)` so
   the loop, the log lines and the "Reached max iterations (N)" reason use the applied value. Docstring says "clamped to LIMIT".

**Alternatives rejected**
- Raise `ValueError` for oversized values: a library caller would crash after the API already returned 422; clamping keeps the
  result usable. Revisit if Sonar needs a rejection form.
- Import the limit from the API module: the AI modules must not depend on the API layer; a drift-guard test compares them instead.
- A shared `clamp_iterations` helper: hides the bound from the scanner at the loop.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Clamp in `optimize_skill` | `src/ai/prompt_evolver.py` | AC1, AC2 | `uv run python -m pytest src/tests/test_iteration_limits.py src/tests/test_prompt_evolver.py -q` |
| T2 | Clamp in `optimize_workflow` | `src/ai/workflow_optimizer.py` | AC1, AC2 | same with `test_workflow_optimizer.py` |
| T3 | Clamp in `co_evolve_skill` | `src/ai/skill_composer.py` | AC1, AC2 | same with `test_skill_composer.py` |
| T4 | Full suite, ruff, mutation audit, PR scan | none | AC1, AC2 | baseline 2 failures; Sonar PR scan shows no S6680 on the three lines |
| T5 | After merge and push scan read the three Sonar issues | none | AC3 | API shows CLOSED |

## Data, API and migration impact

None. HTTP behaviour is unchanged (the request models already reject larger values).

## Security and failure modes

Bounds the paid model calls and CPU a single call can trigger. A clamp is logged at WARNING level.

## Rollout and rollback

Merge via PR; revert the merge commit to undo.

## Risks and open points

Sonar may not treat `min()` as a sanitizer for S6680; the signal is the PR scan and then the push scan. Then switch to an explicit
check, not a dismissal.
