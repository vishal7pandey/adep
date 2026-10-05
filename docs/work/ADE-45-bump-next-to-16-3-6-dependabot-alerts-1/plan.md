# ADE-45 — Bump next to 16.3.6 (Dependabot alerts 1, 2, 3, 6, 7, 27)

Status: draft · Risk: medium · Jira: ADE-45
Created: 2026-10-05 · Slug: bump-next-to-16-3-6-dependabot-alerts-1 · Spec: spec.md

## Summary

Raise the exact pin of `next` from 16.3.0 to 16.3.6 (the highest patched version among the six alerts) in
`frontend/package.json`, refresh `frontend/pnpm-lock.yaml` with pnpm, and keep a small vitest guard that fails if
the pin, the lockfile or the installed package falls below 16.3.6.

**Size:** S

## Current state

- `frontend/package.json`: `"next": "16.3.0"`, `"eslint-config-next": "16.3.0"`, `packageManager` pnpm 11.22.0.
- `frontend/pnpm-lock.yaml`: `next@16.3.0` entries (importer, packages and snapshots sections).
- Commands: `cd frontend && pnpm test` (vitest, 104 tests today), `pnpm run build`, `pnpm lint` (baseline 22 errors /
  44 warnings, ADE-28; `pnpm lint` exits non-zero today).
- The failing regression test `frontend/tests/next-patched-version.test.ts` already exists (3 of 4 tests fail).

## Approach

Run `pnpm add next@16.3.6 --save-exact` in `frontend/` (keeps the exact-pin style), review the lockfile diff, then run
tests, build and lint. Only the `next` package line changes in `package.json`; the lockfile may also change
`next`'s own transitive entries.

**Alternatives rejected**
- Use a caret range (`^16.3.6`): changes the project's pinning policy; not needed to fix the alert.
- Wait for the automatic Dependabot PR: none is open for this package, and the sweep asks for a tracked fix.
- Also bump `eslint-config-next`: unrelated to any alert and could move the lint baseline.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Bump `next` to 16.3.6 with pnpm | `frontend/package.json`, `frontend/pnpm-lock.yaml` | AC1 | `pnpm vitest run tests/next-patched-version.test.ts` passes (4 of 4) |
| T2 | Run the whole frontend suite, build and lint | none | AC2 | `pnpm test` all green; `pnpm run build` exit 0; `pnpm lint` still 22 errors / 44 warnings |
| T3 | After merge and a Dependabot rescan, re-query the six alerts | none (Jira comments) | AC3 | `gh api repos/vishal7pandey/adep/dependabot/alerts/<id>` shows `fixed` for 1, 2, 3, 6, 7, 27 |

## Data, API and migration impact

None. No schema, endpoint, config or environment variable changes. The Docker build installs from the lockfile.

## Security and failure modes

Removes six critical advisories. Failure mode: the build or a runtime behaviour differs on 16.3.6; it would show in
`pnpm run build` or the tests. No secrets are involved.

## Rollout and rollback

Merge the PR; CI (`frontend` job) runs tests and build. Rollback: revert the merge commit; the alerts reopen.

## Risks and open points

- Dependabot may take time to rescan after the merge; AC3 is checked by polling the alerts, and tickets stay open
  until they read `fixed`.
- Lint output could change with the new Next.js version; the signal is the lint count vs the 22/44 baseline.
