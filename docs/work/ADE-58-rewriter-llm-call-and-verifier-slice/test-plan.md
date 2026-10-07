# ADE-58 — Test plan: Rewriter LLM call and verifier slice (Sonar S930 ADE-58, S6466 ADE-59)

Status: draft · Risk: low · Jira: ADE-58

Test framework: pytest via `uv run python -m pytest`; tests in `src/tests/test_*.py`, `unittest.mock.patch` (with `autospec` to enforce the
real `invoke_llm` signature). Command for all: `uv run python -m pytest src/tests -q -m "not integration"`; baseline: 2 known failures
(ADE-23, ADE-24).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `src/tests/test_sonar_bug_fixes.py`: `TestDecomposeSkillCallsTheModelCorrectly::{test_llm_path_returns_the_sub_skills_the_model_proposed, test_invoke_llm_is_called_with_arguments_it_accepts, test_reply_wrapped_in_prose_is_still_parsed, test_empty_reply_degrades_to_a_result_without_sub_skills}`; `TestHeuristicVerifyEmptyCollections::{test_gaps_none_in_a_dict_is_treated_as_empty, test_gaps_none_on_an_object_is_treated_as_empty}` | the stubbed chat client replies with JSON: the sub-skill `extract_header` is returned and `_call_llm` ran once; `autospec` accepts the call and `temperature` is not among the kwargs | a JSON reply wrapped in prose is extracted by the regex fallback | an empty model reply (call failed) gives no sub-skills and a "No JSON" rationale; `gaps: None` / `satisfied: None` (dict or object) is treated as empty instead of raising | verified |
| AC2 | integration | `src/tests/test_sonar_bug_fixes.py::TestHeuristicVerifyEmptyCollections::{test_no_gap_report, test_empty_gap_report_dict, test_empty_gap_and_satisfied_lists, test_at_most_eight_gaps_are_diagnosed, test_a_missing_gap_gets_the_high_severity_failure_action_diagnosis}`; the existing `src/tests/test_query_rewriter.py` (mocks updated to `LLMResponse`) | a missing-field gap gives the exact high-severity diagnosis; no report gives only the shallow-trace diagnosis | 12 gaps give exactly 8 diagnoses and 8 proposed tests; empty report and empty lists give none | n/a: no new abuse input beyond AC1 | verified |
| AC3 | manual | n/a (scanner re-query) | Sonar API shows `AaESHmCCjNIvKL1jZh-E` and `AaESHmB5jNIvKL1jZh-D` CLOSED after the push scan | n/a: single state read per issue | OPEN: the ticket stays open, investigate; a false-positive claim is a proposal to the owner, never applied | planned (after merge) |

## Regression risk

`test_query_rewriter.py` mocks (return a `str`) are updated to the real contract in the fix commit. `test_surrogate_verifier*.py`,
`test_skill_composer.py` (co-evolution calls `verify_skill`) must stay green.

## Untestable AC

None. AC3 is a scanner read.

## Manual checks

AC3: after merge and the push scan, `https://sonarcloud.io/api/issues/search?issues=<key>&componentKeys=vishal7pandey_adep`
for the two keys; read `status` and `resolution`.

## Audit (after implementation)

<!-- filled after implementation -->
