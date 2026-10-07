# ADE-64 — Test plan: Update source-map-js to 1.2.2

Status: draft · Risk: low · Jira: ADE-64

Test framework and conventions found: vitest 4 with jsdom, tests in `frontend/tests/*.test.{ts,tsx}`. Run all with
`cd frontend && pnpm test`. Baseline on master: 11 files, 108 tests passed.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | `frontend/tests/source-map-js-patched-version.test.ts` (4 tests: comparator, lockfile entries, lockfile parent references, installed package) | lockfile has only 1.2.2 entries, parents use 1.2.2, installed 1.2.2 | comparator: `1.2.2` and `1.10.0` ok (numeric compare) | comparator rejects `1.2.1` and `1.0.9`; on the old lockfile 3 of 4 fail | verified |
| AC2 | integration | `pnpm install --frozen-lockfile`, `pnpm test`, `pnpm build` | install ok, 12 files / 112 tests pass, build exits 0 | diff is the lockfile only (3 insertions, 9 deletions) | n/a: no new behaviour | verified |
| AC3 | manual | n/a (scanner re-query) | `gh api repos/vishal7pandey/adep/dependabot/alerts/47 --jq .state` reads `fixed` | n/a: single state read | still `open`: ticket stays open, investigate, never dismiss | verified |

## Regression risk

The 11 existing frontend test files do not touch source-map-js; the build exercises postcss and Tailwind with the new version.

## Untestable AC

None. AC3 is a scanner read.

## Manual checks

AC3: after the merge and the push scan, `gh api repos/vishal7pandey/adep/dependabot/alerts/47 --jq .state`; record state,
URL and date in Jira ADE-64.

## Audit (after implementation)

AC1, `frontend/tests/source-map-js-patched-version.test.ts`:

- Before the update (old lockfile): 3 failed, 1 passed (lockfile entries, parent references, installed package fail; comparator passes).
- Mutation 1, comparator flipped (`a[i] > b[i]` to `a[i] < b[i]`): the comparator test failed (1 failed, 3 passed). Restored.
- Mutation 2, the old lockfile restored: 3 failed (as above). Updated lockfile back: 4 passed.

AC2: `pnpm install --frozen-lockfile` ok; `pnpm test`: 12 files, 112 tests passed; `pnpm build` exit 0. `git diff --stat`:
`frontend/pnpm-lock.yaml | 12 +++---------`, nothing else outside the new test and this work item.

AC3: after the merge (PR #38, merge ced2f20) and the push scan, `gh api repos/vishal7pandey/adep/dependabot/alerts/47` read
`state: fixed`, `fixed_at` 2026-10-07T04:48:46Z.
