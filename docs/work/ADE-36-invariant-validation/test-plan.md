# ADE-36 — Test plan: schema and invariant validation

Status: implementing · Risk: medium · Jira: ADE-36

Test framework and conventions found: pytest, plain dict fixtures inline (no files needed); command
`uv run pytest src/tests/ -v -m "not integration"`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_engine_validation.py::test_validate_output_schema_conformance, ::test_validate_output_reports_missing_nested_required_field | conforming payload -> valid, no errors | n/a | missing nested required field -> error names the path | verified |
| AC2 | unit | ::test_non_empty_invariant | non-empty array -> checked | n/a | empty array -> violated, names the field | verified |
| AC3 | unit | ::test_balance_equals_invariant | 100+50-30=120 -> checked | n/a | closing=121 -> violated with the arithmetic in the message | verified |
| AC4 | unit | ::test_sum_equals_invariant | 80+8=88 -> checked | n/a | total=90 -> violated | verified |
| AC5 | unit | ::test_all_rows_have_invariant, ::test_all_rows_have_checks_multiple_required_fields | every node has a tag -> checked | n/a | one row with empty/missing tag -> violated naming the row index; multi-field require | verified |
| AC6 | unit | ::test_tolerance_range_invariant | PASS row within range -> checked | a non-PASS row outside range is not a violation (mixed PASS+FAIL rows) | a PASS row outside range -> violated | verified |
| AC7 | unit | ::test_missing_field_is_could_not_check_not_a_silent_pass, ::test_wrong_type_for_operator_is_could_not_check | n/a | n/a | an invariant naming an absent/wrong-type field -> could_not_check, never counted as passed (the ADE-12 false-positive gap) | verified |
| AC8 | unit | ::test_unknown_operator_is_could_not_check_not_a_crash | n/a | n/a | unknown `check` name -> could_not_check, no exception | verified |
| AC9 | unit | (all above) | pure dict fixtures, no network/LLM | n/a | n/a | verified |

## Regression risk

None — new module, nothing else imports it yet.

## Untestable AC

None.

## Manual checks

None.

## Audit (after implementation)

Red first: all 11 tests failed at collection (`ModuleNotFoundError: No module named
'src.engine.validation'`) before the module existed. After implementation: one test-authoring bug found
and fixed (a tolerance-range test asserted `checked` on a dataset with only a FAIL row — correctly
`could_not_check`, since there was nothing PASS to actually verify; fixed by adding a PASS row alongside
the FAIL row, which also better proves FAIL rows are skipped rather than silently passing too).

Five mutations applied to the real `src/engine/validation.py` (each confirmed to have changed the file
via `diff`), run, then restored (confirmed byte-identical with `diff -q`):

| Mutation | Test(s) run | Result |
|---|---|---|
| M1: `non_empty`'s type guard removed (always `CHECKED` on a non-list field) | `-k "missing_field or wrong_type"` | both fail |
| M2: unknown operator falls through to a no-op `CHECKED` instead of `COULD_NOT_CHECK` | `-k unknown_operator` | fails |
| M3: `balance_equals` drops its tolerance comparison (`if False` instead of the arithmetic check) | `-k balance_equals` | fails (a real $1 discrepancy is no longer caught) |
| M4: `tolerance_range` stops skipping non-PASS rows | `-k tolerance_range` | fails (a FAIL row outside range is now wrongly flagged) |
| M5: JSON-Schema required-field check disabled | `-k missing_nested` (first attempt with `-k schema` was too broad and missed the regression test — corrected) | fails |

Full suite after restoring: `src/tests/test_engine_validation.py` 11 passed; `pytest src/tests/ -m "not
integration"` 1813 passed, 9 failed (the same pre-existing ADE-23/ADE-24 failures, unchanged), 19
deselected. `ruff check`/`format --check`: clean.
