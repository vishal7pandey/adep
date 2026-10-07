# ADE-73 — Test plan: Contain document store paths

Status: draft · Risk: high · Jira: ADE-73

Test framework: pytest via `uv run python -m pytest`; all: `uv run python -m pytest src/tests -q -m "not integration"`.
Baseline in the shared venv: 12 failures on unmodified master (2 known ADE-23/ADE-24 plus 10 environment ones, deselected in CI).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit/integration | `src/tests/test_document_store_containment.py` (TestStoreOperations, TestDocumentRoutes, TestEngineCallers, TestRunCreationDocumentRoots) | `test_legitimate_id_still_works`, `test_legitimate_document_routes_still_serve`, `test_list_documents_still_lists` | `a.b`, `.hidden`, empty id; `.adep-evil` and `sample-data-evil` siblings; missing page | `../x`, `/abs`, `a/b`, encoded traversal ids on 4 routes, symlinked dir or page leaving the store, thumbnail outside the store, auto-route with a file path | verified |
| AC2 | manual | n/a (scanner re-query) | alerts 7, 10, 24-27 `fixed` on master; PR CodeQL check green | n/a: single state reads | any still `open`: ticket stays open, dismissal proposal, never dismiss | planned |

## Regression risk

`test_path_containment.py`, `test_async_runs.py` (BLK-241 run guard and preview), `test_engine_tools.py`, `test_upload_validation.py`,
`test_audit_fixes.py`, `test_classify.py`, `test_batches.py` use the store and must stay green.

## Untestable AC

AC2 is a scanner state. Two symlink tests skip where symlinks are not permitted (this account); they run in CI (Linux).

## Manual checks

AC2: `gh api repos/vishal7pandey/adep/code-scanning/alerts/<id>` for 7, 10, 24, 25, 26, 27, read `state`.

## Audit (after implementation)

AC1, `src/tests/test_document_store_containment.py` (38 tests: 36 passed, 2 skipped because symlinks are not permitted on this
account; they run on Linux CI). On the unmodified code 12 of them failed (3 routes x 3 invalid ids returning 500, the thumbnail
route outside the store, the engine caller, the auto-route file path); all pass after the fix. Mutations:

- Mutation 1, the three store guards replaced by `if True:` and the `get_doc_dir` id check removed: 7 failed
  (`test_every_operation_rejects_an_invalid_id` for each invalid id). Restored.
- Mutation 2, the run-creation guard without `os.sep` (`startswith(adep_root)`): `test_sibling_dir_sharing_the_adep_prefix_is_403` and
  `test_sibling_dir_sharing_the_sample_data_prefix_is_403` failed (2). Restored.

Honest limit: the symlink tests that would bite the guard alone (with the regex intact) are skipped locally.

Full suite `uv run python -m pytest src/tests -q -m "not integration"`: 12 failed, 2061 passed, 4 skipped; the same 12 fail on unmodified
master in this venv (2 known ADE-23/ADE-24 plus 10 environment failures, deselected in CI). `ruff format --check` clean on the six touched
Python files.

AC2: pending, scanner re-query after merge.
