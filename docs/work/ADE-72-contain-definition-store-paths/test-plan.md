# ADE-72 — Test plan: Contain definition store paths

Status: draft · Risk: high · Jira: ADE-72

Test framework: pytest via `uv run python -m pytest`; all: `uv run python -m pytest src/tests -q -m "not integration"`.
Baseline in the shared venv: 12 failures on unmodified master (2 known ADE-23/ADE-24 plus 10 environment ones, deselected in CI).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit/integration | `src/tests/test_definition_store_containment.py` (TestEveryOperationRejectsABadId, TestEntityTypeIsContained, TestSymlinksCannotLeaveTheStore, TestLegitimateIdsKeepWorking, TestRoutesAnswerAnInvalidIdWithA4xx) | full CRUD cycle for valid ids, built-in definitions/skills/templates resolve, runs and `list_all`, legitimate routes still 200/201/404/204 | `a.b`, `.hidden`, empty id, 80-char id, `a b`; entity dir pointing at a sibling sharing the store name prefix | `../x`, `..\x`, `/abs`, `C:\abs`, `a/b`, `x/../y` on create/read/update/delete/exists and the typed wrappers; unknown or traversing entity type; symlinked file or directory leaving the store; invalid ids on 4 route families and POST body id | verified |
| AC2 | manual | n/a (scanner re-query) | alerts 11 to 23 `fixed` on master; PR CodeQL check green | n/a: single state reads | any still `open`: ticket stays open, dismissal proposal, never dismiss | verified |

## Regression risk

`test_audit_fixes.py` and `test_db_store.py` (ValueError and the `Invalid entity ID` message), `test_path_containment.py`,
`test_async_runs.py`, `test_reviewer_fixes.py`, and every test that goes through `DefinitionStore` or the definitions routes must stay
green.

## Untestable AC

AC2 is a scanner state. The file-symlink test skips where symlinks are not permitted (this account); the directory-symlink tests use a
directory junction there. All run on Linux CI.

## Manual checks

AC2: `gh api repos/vishal7pandey/adep/code-scanning/alerts/<id>` for 11 to 23, read `state`.

## Audit (after implementation)

AC1, `src/tests/test_definition_store_containment.py` (100 tests: 99 passed, 1 skipped, the file-symlink test, because symlinks are not
permitted on this account; the directory tests ran through a Windows junction). On the unmodified code 27 failed (6 entity-type cases and
21 route cases); all pass after the fix. Mutations:

- Mutation 1, the five guards replaced by `if True:` and the entity-type check disabled: 6 failed (`TestEntityTypeIsContained`). Restored.
- Mutation 2, `startswith(root)` without `os.sep`: `test_entity_dir_pointing_at_a_sibling_sharing_the_store_name_prefix_is_refused`
  failed (1). Restored.
- Mutation 3 (before the fix, by construction): without the app handler the 21 route tests fail with the unhandled `ValueError`.

Full suite `uv run python -m pytest src/tests -q -m "not integration"`: 12 failed, 2161 passed, 5 skipped; the same 12 fail on unmodified
master in this venv (2 known ADE-23/ADE-24 plus 10 environment failures, deselected in CI), so no regression. `ruff format --check` clean on
the touched Python files.

AC2: verified 2026-10-07: after the master CodeQL run on the PR #42 merge the code-scanning API shows alerts 11 to 23 `fixed`; the PR CodeQL check was green; Sonar API for pullRequest=42: 0 open issues.
