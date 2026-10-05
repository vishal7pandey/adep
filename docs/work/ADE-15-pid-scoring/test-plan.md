# ADE-15 — Test plan: P&ID scoring

Status: plan-approved · Risk: medium · Jira: ADE-15

Test framework and conventions found: pytest in `src/tests/`, named `test_<area>.py`, `tmp_path` fixtures; run with `.venv/Scripts/python.exe -m pytest src/tests/test_pid_scoring.py src/tests/test_pid_ground_truth.py -q`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | src/tests/test_pid_scoring.py::TestCountRecall | found equals truth gives 1.0 | found above truth caps recall at 1.0 and reports over-extraction; found below truth gives the ratio | truth zero gives not applicable, never 1.0; missing or malformed categories count as zero found | verified |
| AC2 | unit | src/tests/test_pid_scoring.py::TestLabelPrecision | all tags on drawing gives 1.0 | tag whose letter and number parts are separate labels counts as present; duplicates count once | invented tags lower precision; partial parts do not count; no tags gives not applicable | verified |
| AC3 | unit | src/tests/test_pid_scoring.py::TestNormalizeTag | case, spaces, separators, superscripts equal | empty and None normalise to empty | different tags stay different (PI-101 vs PI-102, V-1 vs V-10) | verified |
| AC4 | unit | src/tests/test_pid_ground_truth.py::TestLoad | hand-authored XML gives expected category counts and label set | label-class and flange elements are not valves; empty plant gives zero counts | malformed XML or SVG raises an error naming the file | verified |
| AC5 | unit | src/tests/test_pid_ground_truth.py::TestDiscover | tmp dir with xml+svg pair is found | svg in an `svg/` subfolder is found; xml without svg is skipped with a message | env var unset or directory missing gives empty list and a message | verified |
| AC6 | unit | src/tests/test_pid_ground_truth.py::TestRender | small SVG renders to a PNG with the PNG signature | zoom 2.0 doubles the width of zoom 1.0 | missing SVG raises a clear error | verified |
| AC7 | integration | whole suite plus CI | new tests pass without model, network or DEXPI files | n/a: suite either passes or not | the engine and old-engine suites still pass | verified |

## Regression risk

Nothing existing imports the new modules. The suite already has 2 known failures (ADE-23, ADE-24) unrelated to this work.

## Untestable AC

None. The manual check on real reference files (AC4) is recorded in the PR, not automated, because the files cannot be in the repo.

## Manual checks

Done 2026-10-05 with `ADE_DEXPI_REF_DIR` pointing at the three real reference pairs: every count matched an independent hand count from the XML (edges 23/9/5, equipment 21/8/0, valve classes summed 11/3/2); real printed labels scored label precision 1.0 and invented tags 0.0; all three drawings rendered to PNG. C03V04 has zero equipment, which exercises the not-applicable path.

## Audit (after implementation)

Seven mutations were applied to the implementation, one at a time, and each was caught by a named test:

| Mutation | Caught by |
|---|---|
| recall without the `min()` cap | `TestCountRecall::test_more_found_caps_recall_and_reports_over_extraction` |
| zero truth reported as 1.0 | `TestCountRecall::test_zero_truth_is_not_applicable_never_one` |
| separators kept in normalisation | `TestNormalizeTag::test_case_space_and_separators_are_ignored` |
| any part instead of all parts | `TestLabelPrecision::test_partial_parts_do_not_count` |
| duplicate tags not de-duplicated | `TestLabelPrecision::test_duplicate_tags_count_once_but_still_count_for_recall` |
| label classes counted as valves | `TestLoad::test_counts_by_category` |
| svg subfolder ignored (behavioural, redone after a first attempt broke the syntax instead) | `TestDiscover::test_svg_in_a_svg_subfolder_is_found` |

Files were restored after each run and the suite re-run green (32 passed).
