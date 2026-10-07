# ADE-69 — Test plan: Image read inside the path guard (Sonar S2083 re-raised)

Status: draft · Risk: high · Jira: ADE-69

Test framework: pytest via `uv run python -m pytest`; command for all: `uv run python -m pytest src/tests -q -m "not integration"`
(baseline: 2 known failures, ADE-23 and ADE-24).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `src/tests/test_sonar_path_containment.py::TestImagePathContainment` (all), `::TestImagePathSiblingPrefix::{test_sibling_of_the_working_dir_is_refused, test_sibling_of_the_temp_dir_is_refused}` | `test_image_in_the_working_dir_is_still_read`, `test_image_in_the_system_temp_dir_is_still_read`, `test_jpeg_mime_is_kept_for_non_png` | `work-evil/` and `systmp-evil/` siblings share the root's string prefix and are refused | outside absolute path, `..` traversal, symlink out (skipped where not permitted) | verified |
| AC2 | manual | n/a (scanner re-query) | Sonar API shows `AaEUi-pJNs-rcCYFSaoq` CLOSED after the push scan; CodeQL check green on the PR | n/a: single state read | still OPEN: ticket stays open, investigate, never dismiss | verified |

## Regression risk

Callers of `_encode_image` (`test_read_chart.py`, `test_classify.py`, `test_engine_tools.py`, `test_openai_provider.py`) must stay green.

## Untestable AC

Honest note: no test can fail before this fix, because the behaviour is already correct; the failing signal is the Sonar issue itself.

## Manual checks

AC2: `https://sonarcloud.io/api/issues/search?issues=AaEUi-pJNs-rcCYFSaoq&componentKeys=vishal7pandey_adep`, read `status` and `resolution`.

## Audit (after implementation)

AC1, `src/tests/test_sonar_path_containment.py` (16 tests: 15 passed, 1 skipped because symlinks are not permitted on this account).
The two new sibling-prefix tests pass before and after the restructure (the behaviour was already correct), so the evidence that
they bite is mutation:

- Mutation 1, the guard replaced by `if True:`: 6 failed (all refusal tests). Restored.
- Mutation 2, `startswith(root)` without `os.sep`: `test_sibling_dir_sharing_the_working_dir_name_prefix_is_refused`,
  `TestImagePathSiblingPrefix::test_sibling_of_the_working_dir_is_refused` and `::test_sibling_of_the_temp_dir_is_refused` failed (3). Restored.
- Mutation 3, the temp root dropped from the loop: `test_image_in_the_system_temp_dir_is_still_read` failed (1). Restored.

Full suite `uv run python -m pytest src/tests -q -m "not integration"`: 1999 passed, 2 skipped, 19 deselected, 2 failed, the known
baseline (ADE-23, ADE-24). `ruff format --check` and `ruff check` clean on the two touched files.

AC2: verified 2026-10-07: after the push scan on master the Sonar API shows AaEUi-pJNs-rcCYFSaoq CLOSED, resolution FIXED; CodeQL check green on the PR.
