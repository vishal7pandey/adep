# ADE-5 — Test plan: pre-commit hooks

Status: plan-approved · Risk: low · Jira: ADE-5

Test framework and conventions found: `uv run pytest src/tests/ -m "not integration"`; hooks via `uv run pre-commit run --all-files`.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | manual | `git diff --stat uv.lock` | 92 lines added, 0 removed | n/a: lock diff only | n/a: no upgrades observed | verified |
| AC2 | manual | `ls .git/hooks/pre-commit` | file present after install | n/a: single file | n/a: not applicable | verified |
| AC3 | manual | `git status --short sample-data` after the run | no changes | excluded paths incl. lockfiles | n/a: exclusion is the check | verified |
| AC4 | manual | `pre-commit run --all-files` | active hooks pass | n/a: config check | disabled hooks would fail (1043 / 183 errors) | verified |
| AC5 | integration | full non-integration pytest run | 2 failed, 1790 passed, same as before | second hook run is a no-op | n/a: same failures only | verified |

## Regression risk

Formatting changes every Python file; ruff-format preserves the AST; tests unchanged.

## Untestable AC

None.

## Manual checks

Commands listed in the rows above.

## Audit (after implementation)

Before: 2 failed, 1790 passed. After the format commit: 2 failed, 1790 passed (same two tests).
