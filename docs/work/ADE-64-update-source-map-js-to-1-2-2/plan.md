# ADE-64 — Update source-map-js to 1.2.2

Status: draft · Risk: low · Jira: ADE-64
Created: 2026-10-07 · Slug: update-source-map-js-to-1-2-2 · Spec: spec.md

## Summary

Re-resolve the transitive `source-map-js` to 1.2.2 with `pnpm update source-map-js --lockfile-only` and add a guard test in
the style of `next-patched-version.test.ts`.

**Size:** S

## Current state

`frontend/pnpm-lock.yaml` has `source-map-js@1.2.1` and `@1.2.2` entries; three parents use 1.2.1. Guard tests live in
`frontend/tests/*.test.ts` (vitest). Dependabot cannot open the PR itself (see spec).

## Approach

1. Add `frontend/tests/source-map-js-patched-version.test.ts` and see it fail on the current lockfile.
2. `cd frontend && pnpm update source-map-js --lockfile-only`; check that only `pnpm-lock.yaml` changed.
3. `pnpm install --frozen-lockfile`, `pnpm test`, `pnpm build`.

**Alternatives rejected:** a `pnpm.overrides` entry in `package.json`/`pnpm-workspace.yaml` (a permanent pin for a problem
the lockfile alone solves); waiting for Dependabot (its job fails for this alert).

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Guard test, red on the old lockfile | `frontend/tests/source-map-js-patched-version.test.ts` | AC1 | 3 failed |
| T2 | Lockfile update | `frontend/pnpm-lock.yaml` | AC1, AC2 | 4 passed; diff only the lockfile |
| T3 | Install, test, build, CI incl. CodeQL and sonarcloud | none | AC2 | all green |
| T4 | After merge and scan, re-query alert 47 | none | AC3 | `state: fixed` |

## Data, API and migration impact

None.

## Security and failure modes

Removes a vulnerable version from the lockfile. No new packages.

## Rollout and rollback

Merge via PR; revert the merge commit to undo.

## Risks and open points

If alert 47 stays open after the scan, the Jira ticket stays open and the finding is reported; never dismissed.
