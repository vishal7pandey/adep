# ADE-51 — Test plan: Contain paths in key delete, benchmark fixture dir and page file (CodeQL path-injection alerts 3, 4, 5, 6)

Status: draft · Risk: high · Jira: ADE-51

Test framework and conventions found: pytest (run as `uv run python -m pytest`, `pytest.exe` is blocked on this machine),
tests in `src/tests/test_*.py`, FastAPI `TestClient` with a temp store per test (see `auth_client` in `test_auth.py`,
`client` in `test_benchmark_suite.py`), `tmp_path` and `monkeypatch`. Command for all: `uv run python -m pytest src/tests -q -m "not integration"`;
baseline on master: 2 known failures (ADE-23 `test_seeded_definitions_exist`, ADE-24 `test_compact_run_not_in_executor_returns_false`).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | integration | `src/tests/test_path_containment.py`: `TestApiKeyDeleteContainment::{test_delete_rejects_relative_traversal_and_keeps_outside_file, test_delete_rejects_sibling_dir_sharing_the_key_dir_name_prefix, test_delete_rejects_absolute_key_id_and_keeps_outside_file, test_delete_route_returns_404_for_traversal_id}`; `TestBenchmarkFixtureDirContainment::{test_relative_traversal_outside_cwd_is_rejected, test_sibling_dir_sharing_the_cwd_name_prefix_is_rejected, test_absolute_path_outside_cwd_is_rejected, test_the_cwd_itself_is_rejected}`; `TestDocumentPageContainment::{test_invalid_document_id_is_404_not_a_server_error, test_page_file_outside_the_document_store_is_not_served}` | n/a: the happy cases are the AC2 rows | a key id `../victim` (one level above `api_keys/`) and an absolute id both end at the `FileNotFoundError`, route 404; `fixture_dir` `../outside` and an absolute dir outside the cwd both give 404 and the runner spy is never called; a store path outside the documents dir gives 404 | the outside file still exists after `delete`; the benchmark runner is never called; the page body (`outside-the-store`) is never in the response; a backslash in the document id (invalid id) is 404, not an unhandled `ValueError` | verified |
| AC2 | integration | `src/tests/test_path_containment.py`: `test_delete_still_removes_a_legitimate_key`, `test_delete_unknown_key_still_raises_file_not_found`, `test_relative_dir_inside_cwd_is_accepted`, `test_absolute_dir_inside_cwd_is_accepted`, `test_missing_dir_inside_cwd_still_404`, `test_legitimate_page_is_served`; plus the existing `test_auth.py`, `test_benchmark_suite.py` suites | a real key is deleted (file gone, `get` returns None); `fixtures` and an absolute dir inside the cwd run the suite on the resolved dir; page 1 of an existing document returns 200 with its bytes | unknown key id raises `FileNotFoundError`; missing dir inside the cwd is 404; existing `test_trigger_benchmark_404_missing_dir` (`/nonexistent/path/`) still 404 and `test_trigger_benchmark_400_invalid_provider` still 400 | n/a: no new abuse input beyond the AC1 rows | verified |
| AC3 | manual | n/a (scanner re-query) | `gh api .../code-scanning/alerts/{3,4,5,6}` reads `state: fixed` after the post-merge CodeQL run | n/a: single state read per alert | state still `open` means the Jira ticket stays open with a comment saying why and the fix is improved, never dismissed | planned (after merge) |

## Regression risk

- `src/tests/test_auth.py` (key CRUD through the API, `delete_key` returns 204 for a real key), `src/tests/test_benchmark_suite.py`
  (`TestBenchmarkAPI`: 404 for `/nonexistent/path/`, 400 for an invalid provider with `fixture_dir=tmp_path`, which is outside the
  cwd: the provider check now runs before the path check so it stays 400), and any test hitting the document page routes must
  stay green. No existing test needs changing.

## Untestable AC

None. AC3 is a scanner read, covered under Manual checks.

## Manual checks

AC3: after merge, `gh run list -R vishal7pandey/adep --workflow CodeQL` to see the post-merge analysis, then
`gh api repos/vishal7pandey/adep/code-scanning/alerts/<id> --jq .state` for ids 3, 4, 5, 6. It cannot be automated before the merge:
code scanning results for the default branch only exist after the merge. Record the URL, state and date in each Jira ticket.

## Audit (after implementation)

AC1 and AC2, `src/tests/test_path_containment.py` (16 tests, 16 passed after the fix). Evidence the tests fail when the
behaviour breaks:

- Before the fix (commit "test(ADE-51): failing path-containment tests"): 7 failed, 6 passed. The key-delete tests ended with
  `DID NOT RAISE FileNotFoundError` and, through the route, `204 == 404` (a file outside `api_keys/` was really deleted);
  the benchmark tests got `200 == 404`; the page tests got an unhandled `ValueError` and `200 == 404`.
- Mutation 1, auth guard replaced by `if False:` (line `delete` in `src/api/auth.py`): `test_delete_rejects_relative_traversal_and_keeps_outside_file`
  (line 76), `test_delete_rejects_absolute_key_id_and_keeps_outside_file` (line 86) and
  `test_delete_route_returns_404_for_traversal_id` (line 123) failed (3 failed). Restored.
- Mutation 2, benchmark containment condition replaced by `if False:`: `test_relative_traversal_outside_cwd_is_rejected` (line 170) and
  `test_absolute_path_outside_cwd_is_rejected` (line 200) failed. Restored.
- Mutation 3, page `startswith` check replaced by `if False:`: `test_page_file_outside_the_document_store_is_not_served` (line 262) failed. Restored.
- Mutation 4, `ValueError` removed from the `except` in `get_page`: `test_invalid_document_id_is_404_not_a_server_error` (line 257) failed. Restored.
- Mutation 5 and 6 (prefix check without `os.sep`, benchmarks and auth): both survived the first test set (13 passed). Gap
  found; added `test_sibling_dir_sharing_the_cwd_name_prefix_is_rejected` (line 180) and
  `test_delete_rejects_sibling_dir_sharing_the_key_dir_name_prefix` (line 96); with them each mutation now fails exactly that
  test (1 failed). Restored; working tree holds only the fix.
- Legitimate-path tests (`test_delete_still_removes_a_legitimate_key` line 108, `test_relative_dir_inside_cwd_is_accepted` line 210,
  `test_absolute_dir_inside_cwd_is_accepted` line 219, `test_legitimate_page_is_served` line 247, missing-path tests lines 117 and 229)
  stayed green in every mutation, so they pin behaviour the fix must preserve (they assert results, not just "no error").

Full suite `uv run python -m pytest src/tests -q -m "not integration"`: 1981 passed, 1 skipped, 19 deselected, 2 failed, the
known baseline `test_compact_run_not_in_executor_returns_false` (ADE-24) and `test_seeded_definitions_exist` (ADE-23); nothing else failed.
`uv run ruff format --check` clean on the four touched files; `uv run ruff check` on the test file is clean; on `auth.py`,
`benchmarks.py` and `documents.py` the remaining findings are the same pre-existing ones (import order, unused import, long line
in lines not touched here, ADE-20; ruff lint is disabled in CI and pre-commit until then), none introduced by this change.

AC3: pending, read after merge and the post-merge CodeQL run.
