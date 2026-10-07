# ADE-64 — Update source-map-js to 1.2.2

Status: draft · Risk: low · Jira: ADE-64
<!-- Security finding: neutral wording on purpose; this repo is public. -->

Dependabot alert 47 (high): `source-map-js` `>= 1.0.0, < 1.2.2`, first patched 1.2.2, manifest `frontend/pnpm-lock.yaml`.
Alert state read on 2026-10-07: `open`.

## Repro

Environment: `master` @ 6419fb4, `frontend/pnpm-lock.yaml`, pnpm 11.22.0.

1. `grep source-map-js frontend/pnpm-lock.yaml`.

Observed: three parents (`css-tree`, `postcss@8.5.23`, `postcss@8.5.26`) resolve `source-map-js: 1.2.1`, and a
`source-map-js@1.2.1` package entry exists next to the patched `1.2.2` one (used by one parent). 1.2.1 is below the
first patched version.

Automated repro: `frontend/tests/source-map-js-patched-version.test.ts` (new), run with `cd frontend && pnpm test`; on the
current lockfile 3 of its 4 tests fail (lockfile entries, parents, installed package), the comparator test passes.

Reproducibility: always.

## Expected

Every `source-map-js` resolution in the lockfile is 1.2.2 or above.

## Actual

Part of the tree still resolves 1.2.1. Dependabot's own security job for this alert fails
(`security_update_not_possible`, `npm_and_yarn in /frontend for source-map-js`), so it never opens a PR, although every
parent allows `^1.2.1` and 1.2.2 resolves locally.

## Root cause (with evidence)

- Where: `frontend/pnpm-lock.yaml` (transitive entries, no direct dependency in `frontend/package.json`).
- Why it fails: the lockfile pinned 1.2.1 when it was last resolved (1.2.2 was published 2026-09-30); nothing re-resolves
  a transitive dependency by itself and the Dependabot updater cannot do it for this pnpm tree.
- Introduced by: always present until a re-resolution.
- Evidence: `pnpm update source-map-js --lockfile-only` with the repo's pnpm 11.22.0 rewrites those resolutions to 1.2.2 and
  touches only `pnpm-lock.yaml` (diff: 3 insertions, 9 deletions, the old 1.2.1 package and snapshot entries removed).

## Blast radius

Build-time dependency of postcss, css-tree and @tailwindcss/node (CSS tooling, source maps) in the frontend build. No runtime
code in `frontend/src` imports it. No data affected.

## Regression criterion (AC1)

AC1: `frontend/tests/source-map-js-patched-version.test.ts` fails on the old lockfile (3 failed) and passes after the update
(4 passed): the lockfile resolves, and every parent points at, source-map-js 1.2.2 or above; the installed package for
postcss is 1.2.2 or above.

AC2: `pnpm install --frozen-lockfile`, `pnpm build` and `pnpm test` succeed, and the diff is the lockfile plus the new test
(plus this work item), no `package.json` change.

AC3: After the merge and the push scan, `gh api repos/vishal7pandey/adep/dependabot/alerts/47` reads `state: fixed`
(closure rule: Jira ADE-64 goes to Done only then).

## Fix constraints

Lockfile only, produced by the package manager (`pnpm update source-map-js --lockfile-only`); no hand edit, no override or
`package.json` change. Never dismiss the alert.

## Risks

Low: a patch release of a leaf dependency, all parents declare `^1.2.1`. Rollback: revert the merge commit. If the alert
stays open after the scan, investigate (another manifest or version) and report; do not dismiss.
