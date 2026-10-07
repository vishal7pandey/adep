# ADE-77 — js-yaml below 4.3.2

Status: draft · Risk: low · Jira: ADE-77
<!-- Security finding: neutral wording on purpose; this repo is public. -->

Dependabot alert 8 (high): `js-yaml` `>= 4.0.0, < 4.3.2`, first patched 4.3.2, manifest `frontend/pnpm-lock.yaml`
(advisory GHSA-2883-xcg3-v3hh, `maxTotalMergeKeys` does not limit CPU use for empty merge sources). Alert state read on
2026-10-07: `open`.

## Repro

Environment: `master` @ ef900ae, `frontend/pnpm-lock.yaml`, pnpm 11.22.0.

1. `grep js-yaml frontend/pnpm-lock.yaml`.

Observed: one package entry `js-yaml@4.3.1` (lockfile lines 1872 and 4601) and one parent reference `js-yaml: 4.3.1` (line
3013, from `@eslint/eslintrc@3.3.6`). 4.3.1 is below the first patched version. `pnpm why js-yaml` shows the only path:
eslint 9 -> `@eslint/eslintrc` -> `js-yaml`.

Automated repro: `frontend/tests/js-yaml-patched-version.test.ts` (new), run with `cd frontend && pnpm test`; on the current
lockfile 2 of its 3 tests fail (`js-yaml@4.3.1 is below 4.3.2` and `edge to js-yaml 4.3.1 is below 4.3.2`), the comparator
test passes.

Reproducibility: always.

## Expected

Every `js-yaml` resolution in the lockfile is 4.3.2 or above, so Dependabot's next scan closes the alert.

## Actual

`js-yaml@4.3.1` is locked. No Dependabot PR is open for it.

## Root cause (with evidence)

- Where: `frontend/pnpm-lock.yaml` (transitive entry only; `js-yaml` is not in `frontend/package.json`).
- Why it fails: the lockfile pinned 4.3.1 when it was last resolved; nothing re-resolves a transitive dependency by itself.
  `@eslint/eslintrc@3.3.6` declares `js-yaml: ^4.3.0`, so 4.3.2 is already in range and no parent bump or override is needed.
- Introduced by: always present until a re-resolution.
- Evidence: `pnpm update js-yaml --lockfile-only` with the repo's pnpm 11.22.0 re-resolves it to 4.3.2 and touches only
  `pnpm-lock.yaml`. Same fix as chatpid (its PR #21, same advisory).

## Blast radius

Dev tooling only (eslint config loading); `js-yaml` is not imported by the shipped frontend code or the Next build output.
Single version in the lockfile, so no second parent. The package manager's re-resolution also deduplicated two other
transitive packages inside their existing ranges (`picomatch` 4.0.5 to 4.0.7, `@jridgewell/sourcemap-codec` 1.5.5 to 1.6.0,
both build tooling); the full frontend suite and `next build` pass with them. No data affected.

## Regression criterion (AC1)

AC1: `frontend/tests/js-yaml-patched-version.test.ts` fails on the old lockfile (2 failed) and passes after the update
(3 passed): the lockfile resolves, and every parent points at, js-yaml 4.3.2 or above.

AC2: `CI=true pnpm install --frozen-lockfile`, `pnpm test` and `pnpm build` succeed in `frontend/`, and the diff is the
lockfile plus the new test (plus this work item), no `package.json` change.

AC3: After the merge and the push scan, `gh api repos/vishal7pandey/adep/dependabot/alerts/8` reads `state: fixed` (closure
rule: Jira ADE-77 goes to Done only then).

## Fix constraints

Lockfile only, produced by the package manager (`pnpm update js-yaml --lockfile-only`); no hand edit, no override or
`package.json` change. Never dismiss the alert. Python code is not touched.

## Risks

Low: a patch release of a dev-only leaf dependency within its parent's range. Rollback: revert the merge commit. If the
alert stays open after the scan, investigate (another manifest or version) and report; do not dismiss.
