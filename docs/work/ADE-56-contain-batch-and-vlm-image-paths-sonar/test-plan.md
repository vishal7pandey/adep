# ADE-56 — Test plan: Contain batch and VLM image paths (Sonar S2083 ADE-56, ADE-57)

Status: draft · Risk: high · Jira: ADE-56

Test framework and conventions found: pytest (run as `uv run python -m pytest`, `pytest.exe` is blocked on this machine),
tests in `src/tests/test_*.py`, `tmp_path`, `monkeypatch`, `unittest.mock`. Command for all:
`uv run python -m pytest src/tests -q -m "not integration"`; baseline on master: 2 known failures (ADE-23
`test_seeded_definitions_exist`, ADE-24 `test_compact_run_not_in_executor_returns_false`).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `src/tests/test_sonar_path_containment.py`: `TestSaveBatchContainment::{test_relative_traversal_id_is_rejected_and_nothing_is_written, test_sibling_dir_sharing_the_batches_name_prefix_is_rejected, test_absolute_id_is_rejected_and_nothing_is_written}`; `TestImagePathContainment::{test_absolute_path_outside_both_roots_is_refused, test_relative_traversal_out_of_the_working_dir_is_refused, test_sibling_dir_sharing_the_working_dir_name_prefix_is_refused, test_encode_image_raises_for_a_path_outside, test_refusal_is_immediate_not_retried_with_backoff, test_symlink_inside_the_working_dir_pointing_outside_is_refused}` | n/a: the happy cases are the AC2 rows | batch id `../escape` (one level above `batches/`) and `../batches-evil/x` (sibling sharing the name prefix) both raise `ValueError`; image `../outside/secret.png` and a `work-evil/` sibling of the working dir both refused | an absolute batch id and an absolute image path outside both roots are refused; no file appears outside `.adep/batches`; the model client is never called; the refusal comes back in under 1.5 s (no backoff); a symlink to an outside file is refused (skipped where symlinks are not permitted) | verified |
| AC2 | integration | `src/tests/test_sonar_path_containment.py`: `test_legitimate_id_is_saved_inside_the_batches_dir`, `test_overwriting_an_existing_batch_still_works`, `test_image_in_the_working_dir_is_still_read`, `test_image_in_the_system_temp_dir_is_still_read`, `test_jpeg_mime_is_kept_for_non_png`; plus the existing `test_batches.py`, `test_read_chart.py`, `test_classify.py`, `test_engine_tools.py`, `test_openai_provider.py` | a batch is saved and loaded back; a page under `.adep/documents/d1/` and a crop in the temp dir are sent to the client as `data:image/png;base64,...` | overwrite of an existing batch; `.jpg` keeps `image/jpeg` | n/a: no new abuse input beyond the AC1 rows | verified |
| AC3 | manual | n/a (scanner re-query) | the Sonar API shows both issues closed after the push scan on master | n/a: single state read per issue | status still OPEN means the Jira tickets stay open with a comment saying why and the fix is improved, never dismissed | planned (after merge) |
| AC4 | static analysis | PR CodeQL check; after merge, code-scanning alert 50 API | no new high `py/path-injection` alert on `_encode_image`; alert 50 reads `fixed` on master | two allowed roots: working directory and temp directory | outside paths and symlink escapes still fail the AC1 tests; never dismiss alert 50 | local verified; CodeQL pending |

## Regression risk

- `src/tests/test_batches.py` (batch CRUD through the API, `save_batch`/`load_batch` round trip with `monkeypatch.chdir(tmp_path)`),
  tests that stub `_call_vlm`/`vlm` with real temporary images (`test_read_chart.py`, `test_classify.py`, `test_engine_tools.py`,
  `test_openai_provider.py`): temp images live under the system temp directory, which is an allowed root. No existing test needs changing.

## Untestable AC

None. AC3 is a scanner read, covered under Manual checks.

## Manual checks

AC3: after the merge and the push scan of `master`, run the query
`https://sonarcloud.io/api/issues/search?issues=<key>&componentKeys=vishal7pandey_adep` (anonymous) for `AaESHl-HjNIvKL1jZh79` and
`AaESHmAUjNIvKL1jZh9X` and read `status` and `resolution`. It cannot be automated before the merge: the push analysis of the
default branch only exists after it. Record the state and date in each Jira ticket.

Before merge, the PR CodeQL check must pass without introducing a new high-severity finding. Alert 50 (`py/path-injection`)
was reported at `src/providers/vlm_azure.py:82` after three forms of the two-root guard failed to satisfy the analyzer. The
revised plan uses the direct two-root boolean guard, matching the successful one-root pattern in
`src/api/routes/documents.py`; verify the PR check after implementation and do not merge unless it is green.

## Audit (after implementation)

AC1 and AC2, `src/tests/test_sonar_path_containment.py` (14 tests: 13 passed and 1 skipped here, the symlink test, because
symlinks are not permitted on this Windows account; it runs where they are). Evidence the tests fail when the behaviour breaks:

- Before the fix (commit "test(ADE-56): failing containment tests ..."): 7 failed, 6 passed, 1 skipped. The save tests ended with
  `DID NOT RAISE ValueError`; the image tests got `ok is True` (the file was read and the client called) and `_encode_image` did not raise.
- Mutation 1, `save_batch` guard replaced by `if False:`: `test_relative_traversal_id_is_rejected_and_nothing_is_written`,
  `test_sibling_dir_sharing_the_batches_name_prefix_is_rejected` and `test_absolute_id_is_rejected_and_nothing_is_written` failed (3). Restored.
- Mutation 2, `save_batch` prefix check without `os.sep`: `test_sibling_dir_sharing_the_batches_name_prefix_is_rejected` failed (1). Restored.
- Mutation 3, `_encode_image` guard replaced by `if False:`: the three `vlm()` refusal tests and
  `test_encode_image_raises_for_a_path_outside` failed (4). Restored.
- Mutation 4, `_encode_image` prefix check without `os.sep`: `test_sibling_dir_sharing_the_working_dir_name_prefix_is_refused` failed (1). Restored.
- Mutation 5, system temp directory dropped from the allowed roots: `test_image_in_the_system_temp_dir_is_still_read` failed (1)
  (`ok=False`, "outside the allowed directories"). Restored.
- Mutation 6, `retry=retry_if_not_exception_type(...)` removed from `_call_vlm`: `test_refusal_is_immediate_not_retried_with_backoff`
  failed (1; the run took 16 s because of the backoff). Restored.
- The legitimate-path tests (batch round trip and overwrite, working-dir image, `.jpg` MIME) stayed green in every mutation, so they
  pin behaviour the fix must preserve. The working tree held only the fix after the audit.

Full suite `uv run python -m pytest src/tests -q -m "not integration"`: 1997 passed, 2 skipped, 19 deselected, 2 failed, the known
baseline `test_compact_run_not_in_executor_returns_false` (ADE-24) and `test_seeded_definitions_exist` (ADE-23); nothing else failed.
`uv run ruff format --check` clean on the three touched files; `uv run ruff check` reports the same 2 pre-existing findings
(unused import and a long line in `batches.py`, ADE-20) before and after this change, none introduced.

AC3: pending, read after merge and the push scan.

CodeQL PR finding: alert 50 remained at the filesystem path operation through implementations using `any(...)` or
`commonpath` across a collection of roots. After human approval of the amended plan, `_encode_image` now uses two named roots
and one explicit `or`-combined `startswith(root + os.sep)` condition inline, following the existing successful containment
guard in `src/api/routes/documents.py`. The affected caller suite passes (89 passed, 1 skipped); the PR CodeQL rerun is
pending. Alert 50 is tracked separately in ADE-67; do not merge unless the PR CodeQL check is green.
