# ADE-35 — Test plan: budget tracker

Status: implementing · Risk: low · Jira: ADE-35

Test framework and conventions found: pytest, no fixtures needed (pure dataclass arithmetic); command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_budget.py::test_spend_remaining_and_fraction_used_do_not_mutate, ::test_remaining_never_goes_negative_on_an_already_exhausted_budget, ::test_fraction_used_guards_against_zero_division | exact remaining/fraction values for a mid-spend state | a zero-max budget guards against division by zero | an already-exhausted spend never returns negative remaining | verified |
| AC2 | unit | ::test_record_tool_accumulates_turns_and_cost_correctly | 3 crop calls + 1 free call -> turns=3, cost=3x crop cost | n/a | n/a | verified |
| AC3 | unit | ::test_unlisted_tool_name_defaults_to_one_turn_zero_cost | n/a | an unknown tool name | n/a | verified |
| AC4 | unit | ::test_status_recommendations_appear_below_threshold, ::test_status_has_no_low_turns_recommendation_when_plenty_remain | 8/10 turns spent -> the specific "Only 2 turns left" recommendation | n/a | 9/10 turns remaining -> no "turns left" recommendation | verified |
| AC5 | unit | ::test_estimate_budget_for_complexity_scales_with_zones_and_resolution, ::test_estimate_budget_for_complexity_caps_runaway_zone_counts | more zones / more pixels -> larger budget | n/a | absurd zone_count does not produce an unbounded max_turns | verified |
| AC6 | unit | (all above) | pure arithmetic, no I/O; seconds set via the real (fast) `time.time()` call, well within a wide tolerance | n/a | n/a | verified |

## Regression risk

None — new module, nothing else imports it yet.

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

Red first: all 9 tests failed at collection (`ModuleNotFoundError: No module named 'src.engine.budget'`)
before the module existed. After implementation: 1 test-authoring bug found and fixed on my own first
pass (a "no recommendation" test used a turns-remaining value that still crossed the batching threshold)
and one weak assertion tightened (`len(recommendations) >= 1` → pinned to the specific "Only 2 turns
left" text, after a mutation revealed a second, independent recommendation rule was masking the first).

Four mutations applied to the real `src/engine/budget.py` (each confirmed to have changed the file via
`diff`), run, then restored (confirmed byte-identical with `diff -q`):

| Mutation | Test(s) run | Result |
|---|---|---|
| M1: `record_tool` always costs 1 turn (ignores `TOOL_TURNS` lookup) | `-k record_tool` | fails (free tool now counted as a turn) |
| M2: `Spend.remaining` drops its `max(0, ...)` guards | `-k negative` | fails (remaining goes negative instead of clamping to 0) |
| M3: `estimate_budget_for_complexity` drops the `min(zone_count * 2, 20)` cap | `-k caps_runaway` | fails (a zone_count of 10,000 produces `max_turns=20015`, far past the sane range) |
| M4: both low-turns `if`/`elif` branches in `status()` disabled | `-k threshold` | fails once the assertion was pinned to the specific recommendation text (the first mutation attempt was too weak: a third, independent recommendation rule — high turn-fraction-used — still fired and masked it) |

Full suite after restoring: `src/tests/test_engine_budget.py` 9 passed; `pytest src/tests/ -m "not
integration"` 1802 passed, 9 failed (the same pre-existing ADE-23/ADE-24 failures, unchanged), 19
deselected. `ruff check`/`format --check`: clean.
