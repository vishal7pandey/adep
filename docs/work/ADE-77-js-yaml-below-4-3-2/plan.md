# ADE-77 — js-yaml below 4.3.2

Status: draft · Risk: low · Jira: ADE-77
Created: 2026-10-07 · Slug: js-yaml-below-4-3-2 · Spec: spec.md

## Summary

Re-resolve the transitive `js-yaml` to 4.3.2 with `pnpm update js-yaml --lockfile-only` and add a guard test in the style of
`source-map-js-patched-version.test.ts` (ADE-64).

**Size:** S

## Current state

`frontend/pnpm-lock.yaml` has `js-yaml@4.3.1` and one parent reference (`@eslint/eslintrc@3.3.6`, range `^4.3.0`). Guard
tests live in `frontend/tests/*.test.ts` (vitest, `include: tests/**`). Commands: `CI=true pnpm install --frozen-lockfile`,
`pnpm test`, `pnpm build` in `frontend/`. Baseline on master: 12 files, 113 tests passed.

## Approach

1. Add `frontend/tests/js-yaml-patched-version.test.ts` and see it fail on the current lockfile (2 failed).
2. `cd frontend && pnpm update js-yaml --lockfile-only`; check that only `pnpm-lock.yaml` changed.
3. `pnpm install --frozen-lockfile`, `pnpm test`, `pnpm build`; then the backend baseline in a clean worktree (no code change,
   so it must be unchanged).

**Alternatives rejected:** a `pnpm.overrides` entry (a permanent pin for a problem the lockfile alone solves; the parent's
range already admits the fix); bumping eslint (larger than a lockfile re-resolution); waiting for a Dependabot PR (none is
open; for the sibling alert 47 its job failed with `security_update_not_possible`).

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Guard test, red on the old lockfile | `frontend/tests/js-yaml-patched-version.test.ts` | AC1 | 2 failed |
| T2 | Lockfile update | `frontend/pnpm-lock.yaml` | AC1, AC2 | 3 passed; diff only the lockfile |
| T3 | Install, test, build, CI incl. CodeQL and sonarcloud | none | AC2 | all green |
| T4 | After merge and scan, re-query alert 8 | none | AC3 | `state: fixed` |

## Data, API and migration impact

None.

## Security and failure modes

Removes a vulnerable dev dependency version from the lockfile. No new packages. The guard test goes red if the lockfile
regresses below 4.3.2.

## Rollout and rollback

Merge via PR; revert the merge commit to undo.

## Risks and open points

If alert 8 stays open after the scan, the Jira ticket stays open and the finding is reported; never dismissed.
