# ADE-77 — Test plan: js-yaml below 4.3.2

Status: draft · Risk: low · Jira: ADE-77

Test framework and conventions found: vitest with jsdom, tests in `frontend/tests/*.test.{ts,tsx}`. Run all with
`cd frontend && pnpm test`. Baseline on master: 12 files, 113 tests passed.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | `frontend/tests/js-yaml-patched-version.test.ts` (3 tests: comparator, lockfile entries, lockfile parent references) | lockfile has only 4.3.2 entries and parents use 4.3.2 | comparator: `4.3.2` and `4.10.0` ok (numeric compare) | comparator rejects `4.3.1` and `4.0.0`; on the old lockfile 2 of 3 fail | verified |
| AC2 | integration | `CI=true pnpm install --frozen-lockfile`, `pnpm test`, `pnpm build` | install ok, 13 files / 115 tests pass, build exits 0 | diff is the lockfile only plus the new test | n/a: no new behaviour | verified |
| AC3 | manual | n/a (scanner re-query) | `gh api repos/vishal7pandey/adep/dependabot/alerts/8 --jq .state` reads `fixed` | n/a: single state read | still `open`: ticket stays open, investigate, never dismiss | planned |

## Regression risk

The 12 existing frontend test files do not touch js-yaml; the build exercises the toolchain with the lockfile's other
re-resolved packages (`picomatch` 4.0.7, `@jridgewell/sourcemap-codec` 1.6.0). The Python suite is not affected (no backend
change); its baseline is re-checked in a clean worktree without `.env`.

## Untestable AC

None. AC3 is a scanner read.

## Manual checks

AC3: after the merge and the push scan, `gh api repos/vishal7pandey/adep/dependabot/alerts/8 --jq .state`; record state, URL
and date in Jira ADE-77.

## Audit (after implementation)

AC1, `frontend/tests/js-yaml-patched-version.test.ts`:

- Before the update (old lockfile): 2 failed, 1 passed (lockfile entries and parent references fail with
  `js-yaml@4.3.1 is below 4.3.2` / `edge to js-yaml 4.3.1 is below 4.3.2`; the comparator test passes). Whole suite then
  13 files, 2 failed, 113 passed.
- Mutation 1, comparator flipped (`a[i] > b[i]` to `a[i] < b[i]`): the comparator test failed (1 failed, 2 passed). Restored.
- Mutation 2, the old lockfile restored: 2 failed (as above). Updated lockfile back: 3 passed.

AC2: `CI=true pnpm install --frozen-lockfile` ok; `pnpm test`: 13 files, 115 tests passed; `pnpm build` ok (all routes
prerendered). `git diff --stat`: only `frontend/pnpm-lock.yaml` (11 insertions, 17 deletions) outside the new test and this
work item.
