# ADE-71 — Test plan: Contain webhook store paths

Status: draft · Risk: high · Jira: ADE-71

Test framework: pytest via `uv run python -m pytest`; all: `uv run python -m pytest src/tests -q -m "not integration"`.
Baseline in the shared venv: 12 failures on unmodified master (2 known ADE-23/ADE-24 plus 10 environment ones, deselected in CI).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit/integration | `src/tests/test_webhook_store_containment.py` (TestEveryOperationRejectsABadId, TestSymlinksCannotLeaveTheStore, TestLegitimateIdsKeepWorking, TestRoutesAnswerAnInvalidIdWithA4xx) | full CRUD cycle for valid ids, secret masking, event scan, duplicate create, missing hook, legitimate routes 201/200/404/204 | `a.b`, `.hidden`, empty id, 80-char id, `a b`; webhooks dir pointing at a sibling sharing the store name prefix | `../x`, `..\x`, `/abs`, `C:\abs`, `a/b`, `x/../y` on create/get/get_raw/update/delete; traversal never touches a file beside the webhooks dir; symlinked hook file leaving the store; invalid ids on the route family; POST with a traversal id writes nothing | verified |
| AC2 | manual | n/a (scanner re-query) | alerts 29 to 42 `fixed` on master; PR CodeQL check green | n/a: single state reads | any still `open`: ticket stays open, dismissal proposal, never dismiss | verified |

## Regression risk

`test_wave7.py` (store and routes), `test_reviewer_fixes.py` (imports `_atomic_write` and the SSRF checks), `test_audit_fixes.py`,
`test_webhook_emission.py` must stay green.

## Untestable AC

AC2 is a scanner state. The file-symlink test skips where symlinks are not permitted (this account); the directory case uses a directory
junction there. Both run on Linux CI.

## Manual checks

AC2: `gh api repos/vishal7pandey/adep/code-scanning/alerts/<id>` for 29 to 42, read `state`.

## Audit (after implementation)

AC1, `src/tests/test_webhook_store_containment.py` (67 tests: 66 passed, 1 skipped, the hook-file symlink test, because symlinks are not
permitted on this account; the directory test ran through a Windows junction). On the unmodified code 43 failed and 13 passed (run with
`-k "not abs"`, because the two absolute-id create cases hang trying to write at the drive root); all pass after the fix. Mutations:

- Mutation 1, the five guards replaced by `if True:` and the id check removed: 43 failed (same run, `-k "not abs"`). Restored.
- Mutation 2, `startswith(root)` without `os.sep`: `test_hooks_dir_pointing_at_a_sibling_sharing_the_store_name_prefix_is_refused`
  failed (1). Restored.

Full suite `uv run python -m pytest src/tests -q -m "not integration"`: 12 failed, 2227 passed, 6 skipped; the same 12 fail on unmodified
master in this venv (2 known ADE-23/ADE-24 plus 10 environment failures, deselected in CI), so no regression. `ruff format --check` clean on
the two touched Python files.

AC2: verified 2026-10-07: after the master CodeQL run 37578049266 the code-scanning API shows alerts 29 to 42 `fixed` (fixed_at 2026-10-07T05:48:08Z); the PR CodeQL check was green; Sonar API for pullRequest=43: 0 open issues.
