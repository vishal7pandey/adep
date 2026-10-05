# ADE-45 — Bump next to 16.3.6 (Dependabot alerts 1, 2, 3, 6, 7, 27)

Status: draft · Risk: medium · Jira: ADE-45

Covers six Jira findings that are one defect: ADE-45 (alert 1), ADE-46 (alert 2), ADE-47 (alert 3), ADE-48 (alert 6),
ADE-49 (alert 7), ADE-50 (alert 27). Alerts 1, 2, 3 are raised against `frontend/package.json`; alerts 6, 7, 27 are the same
advisories raised against `frontend/pnpm-lock.yaml`. ADE-45 is the key of this work item; the other five tickets are
closed separately, each on its own re-queried alert.

## Repro

Environment / version / commit where it fails: `master` @ 11665a0, `frontend/package.json` pins `next` 16.3.0.

1. `gh api repos/vishal7pandey/adep/dependabot/alerts/<id>` for ids 1, 2, 3, 6, 7, 27: all `state: open`, severity critical.
2. `grep -n "next@" frontend/pnpm-lock.yaml`: the lockfile resolves `next@16.3.0`.

Alert map (advisory, vulnerable range, first patched version):

| Alert | Jira | Manifest | Advisory | Range | Patched |
|---|---|---|---|---|---|
| 1 | ADE-45 | package.json | GHSA-p293-qw3h-jr36 (RCE on Windows-hosted servers) | >= 16.0.0, < 16.3.3 | 16.3.3 |
| 2 | ADE-46 | package.json | GHSA-2xp9-vwfh-vxw4 (RCE in image optimization with AVIF) | >= 16.0.0, < 16.3.3 | 16.3.3 |
| 3 | ADE-47 | package.json | GHSA-vcvr-r3jv-pc5j (RCE in `next/og` ImageResponse) | >= 16.2.0, < 16.3.6 | 16.3.6 |
| 6 | ADE-48 | pnpm-lock.yaml | GHSA-p293-qw3h-jr36 | as alert 1 | 16.3.3 |
| 7 | ADE-49 | pnpm-lock.yaml | GHSA-2xp9-vwfh-vxw4 | as alert 2 | 16.3.3 |
| 27 | ADE-50 | pnpm-lock.yaml | GHSA-vcvr-r3jv-pc5j | as alert 3 | 16.3.6 |

Automated repro (failing test, with the command to run it):

- `frontend/tests/next-patched-version.test.ts`, run `cd frontend && pnpm vitest run tests/next-patched-version.test.ts`.
  Fails on current code: 3 of 4 tests fail (package.json pin, lockfile versions, installed `next/package.json` version
  are all 16.3.0, below 16.3.6); the fourth test (the version comparator itself) passes.

Reproducibility: always.

## Expected

`next` is at the highest patched release needed by any open advisory, 16.3.6, in `package.json`, in the lockfile and
in the installed package, so the scanner no longer reports the six alerts.

## Actual

`next` is pinned to the exact version 16.3.0, which is inside every vulnerable range above; Dependabot reports the
six alerts as open.

## Root cause (with evidence)

- Where: `frontend/package.json` (`"next": "16.3.0"`), `frontend/pnpm-lock.yaml` (`next@16.3.0`).
- Why it fails: the dependency was pinned exactly (no caret), so it never moved when patched releases came out; the
  advisories were published after the pin.
- Introduced by: commit b02fa8e (2026-08-09) set the 16.3.0 pin; the pin was current then.
- Evidence: the six `gh api` reads above; `pnpm view next@16.3.6 version` confirms 16.3.6 is published.

## Blast radius

- The app does not use `next/og` / `ImageResponse` and does not configure image optimization (`next.config.ts` is
  empty, no `next/image` import under `app/`, `components/`, `lib/`), so the practical exposure of two of the three
  advisories is low; the Windows-hosted-server advisory applies to the way the server is hosted, and the Dockerfile
  runs on Linux (`node:24-alpine`). The bump is still required: the alerts stay open until the version changes.
- `eslint-config-next` is pinned to 16.3.0 as well. It is a lint plugin, not covered by any alert, and is left
  alone to keep the lint baseline (22 errors / 44 warnings, ADE-28) stable. Noted as a possible follow-up.
- Other callers of the pinned version: `frontend/Dockerfile` installs with `pnpm install --frozen-lockfile`, so it
  picks up the lockfile change with no edit.
- No data is affected. Exposed since the pin (2026-08-09) for the advisories published later.

## Regression criterion (AC1)

AC1: `frontend/tests/next-patched-version.test.ts` passes after the fix and fails on the current code: the `next` pin in
`package.json`, every `next@` version resolved in `pnpm-lock.yaml`, and the installed `next` package are all at or above 16.3.6.

AC2: The frontend keeps working on the new version: `pnpm test` passes (104 existing tests plus the new ones), `pnpm run build`
succeeds, and `pnpm lint` is not worse than the baseline of 22 errors and 44 warnings.

AC3: After the fix is merged and Dependabot has rescanned, `gh api repos/vishal7pandey/adep/dependabot/alerts/<id>`
returns `state: fixed` for ids 1, 2, 3, 6, 7 and 27 (verified after merge; the Jira tickets close only on that).

## Fix constraints

- Minimal diff: `next` to `16.3.6` (exact pin, as today) in `frontend/package.json` and the matching lockfile
  update made with pnpm, plus the regression test and the work item folder.
- No application code, config or CI change. Do not touch `eslint-config-next`.

## Risks

- A patch-level change inside 16.3.x; risk is a build or lint behaviour change. Mitigated by running tests, build and
  lint, and comparing lint counts to the baseline. Rollback: revert the commit.
- Risk level medium because the advisories are critical and the change touches the production dependency.
