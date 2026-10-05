# ADE-35 — Plan: budget tracker

Status: plan-approved · Risk: low · Jira: ADE-35
Created: 2026-10-05 · Slug: budget-tracker · Spec: spec.md

## Summary

One new module, `src/engine/budget.py`, ported closely from ade2's `src/ade2/budget.py` (read in full).
**Size:** S.

## Current state

- `src/engine/` exists (ADE-34: `__init__.py`, `skills.py`). This story adds a sibling module; no
  changes to `skills.py`.
- Commands: `uv run pytest src/tests/ -v -m "not integration"`, `uv run ruff check src/`,
  `uv run ruff format src/`.

## Approach

Direct port of `budget.py`'s pieces, same dataclass shapes:
1. `Budget` (max_turns=30, max_cost_usd=2.0, max_seconds=600.0 — same defaults as ade2).
2. `Spend` (turns, cost_usd, seconds) with `remaining(budget)` and `fraction_used(budget)`.
3. `TOOL_TURNS` / `TOOL_COST_USD` module-level cost tables (perception tools cost 1 turn + a dollar
   estimate; local/free tools cost 0 of both).
4. `BudgetTracker` (`record_tool`, `status()` with threshold-based recommendation strings).
5. `estimate_budget_for_complexity(zone_count, image_pixels)`.

For AC6's clock concern: `BudgetTracker.spend.seconds` is derived from `time.time() - start_time` inside
`record_tool`, same as ade2. Tests that need deterministic seconds inject `start_time` directly into the
dataclass (it's a plain field, not computed at call time) rather than mocking `time.time()` — simpler and
matches how the dataclass is already structured.

**Alternatives rejected**
- A clock-injection parameter threaded through every method: unnecessary ceremony for a dataclass field
  that's already directly settable in tests.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Failing tests first (red) | `src/tests/test_engine_budget.py` | AC1-AC6 | tests fail (no `budget.py` yet) |
| T2 | `src/engine/budget.py` | `src/engine/budget.py` | AC1-AC6 | tests pass |

## Data, API and migration impact

None — new, inert module.

## Security and failure modes

None. Pure in-memory accounting.

## Rollout and rollback

Merge; revert to undo. No migration, no runtime behavior change (nothing calls this module yet).

## Risks and open points

None beyond what's in the spec.
