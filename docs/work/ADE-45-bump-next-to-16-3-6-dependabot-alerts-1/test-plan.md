# ADE-45 — Test plan: Bump next to 16.3.6 (Dependabot alerts 1, 2, 3, 6, 7, 27)

Status: draft · Risk: medium · Jira: ADE-45

Test framework and conventions found: vitest 4 with jsdom, globals on, tests in `frontend/tests/*.test.{ts,tsx}`,
`@` alias to `frontend/`. Run all with `cd frontend && pnpm test`. Baseline on master before the change: 10 files, 104
tests passed; `pnpm lint` 22 errors / 44 warnings (ADE-28).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | unit | `frontend/tests/next-patched-version.test.ts` (4 tests: comparator, package.json pin, lockfile versions, installed version) | pin `16.3.6`, lockfile `next@16.3.6`, installed 16.3.6 all pass | comparator: `16.3.6` ok, `16.10.0` ok (numeric, not string, compare) | comparator: `16.3.5` and `15.9.9` rejected; on current code (16.3.0) the three file/installed tests fail | planned |
| AC2 | integration | existing `pnpm test` suite, `pnpm run build`, `pnpm lint` | 104 + 4 tests pass, build exits 0 | lint count equals baseline 22 errors / 44 warnings (must not get worse) | n/a: no new behaviour, nothing to abuse | planned |
| AC3 | manual | n/a (scanner re-query) | `gh api .../dependabot/alerts/{1,2,3,6,7,27}` reads `state: fixed` | n/a: single state read per alert | state still `open` means the Jira ticket stays open with a comment saying why | planned |

## Regression risk

Existing frontend tests (10 files) exercise components and libs, not Next internals; they must stay green. The build
exercises Next 16.3.6 itself. No existing test needs changing.

## Untestable AC

None. AC3 is a scanner read, covered under Manual checks.

## Manual checks

AC3: after merge, `gh api repos/vishal7pandey/adep/dependabot/alerts/<id> --jq .state` for each id; it cannot be
automated before the merge because the scanner only runs on the default branch. Record each state, URL and date in the
matching Jira ticket.

## Audit (after implementation)

<!-- filled in audit mode -->
