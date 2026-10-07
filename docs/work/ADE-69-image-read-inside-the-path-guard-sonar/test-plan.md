# ADE-69 — Test plan: Image read inside the path guard (Sonar S2083 re-raised)

Status: draft · Risk: high · Jira: ADE-69

Test framework: pytest via `uv run python -m pytest`; command for all: `uv run python -m pytest src/tests -q -m "not integration"`
(baseline: 2 known failures, ADE-23 and ADE-24).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `src/tests/test_sonar_path_containment.py::TestImagePathContainment` (all), `::TestImagePathSiblingPrefix::{test_sibling_of_the_working_dir_is_refused, test_sibling_of_the_temp_dir_is_refused}` | `test_image_in_the_working_dir_is_still_read`, `test_image_in_the_system_temp_dir_is_still_read`, `test_jpeg_mime_is_kept_for_non_png` | `work-evil/` and `systmp-evil/` siblings share the root's string prefix and are refused | outside absolute path, `..` traversal, symlink out (skipped where not permitted) | verified |
| AC2 | manual | n/a (scanner re-query) | Sonar API shows `AaEUi-pJNs-rcCYFSaoq` CLOSED after the push scan; CodeQL check green on the PR | n/a: single state read | still OPEN: ticket stays open, investigate, never dismiss | planned (after merge) |

## Regression risk

Callers of `_encode_image` (`test_read_chart.py`, `test_classify.py`, `test_engine_tools.py`, `test_openai_provider.py`) must stay green.

## Untestable AC

Honest note: no test can fail before this fix, because the behaviour is already correct; the failing signal is the Sonar issue itself.

## Manual checks

AC2: `https://sonarcloud.io/api/issues/search?issues=AaEUi-pJNs-rcCYFSaoq&componentKeys=vishal7pandey_adep`, read `status` and `resolution`.

## Audit (after implementation)

<!-- filled after implementation -->
