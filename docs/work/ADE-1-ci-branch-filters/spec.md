# ADE-1 — CI never runs on PRs: ci.yml targets main, default branch is master

Status: spec-approved · Risk: medium · Jira: ADE-1

## Repro

Environment: master @ 9f61bcb on GitHub (vishal7pandey/adep).

1. Open any PR against `master` (PR #1, #2, #3).
2. Only the `verify` check (factory-verify) appears; the `CI` workflow never starts.

Automated repro: none possible locally; evidence is `gh pr checks 3` listing only `verify`, and
`.github/workflows/ci.yml` having `branches: [main]` for both `push` and `pull_request`.

Reproducibility: always.

## Expected

A PR to `master` runs the backend and frontend jobs, and the result is honest: green only if the
code is good, not red for reasons already known and ticketed.

## Actual

CI never runs. Run locally on a clean checkout (ADE-3), CI would be red on day one: ruff 1043 errors
(ADE-20), mypy 183 errors (ADE-21), 10 tests fail on a clean checkout (ADE-23, ADE-24).

## Root cause (with evidence)

- Where: `.github/workflows/ci.yml` `on.push.branches` and `on.pull_request.branches`.
- Why it fails: filters say `main`; the repo's default branch is `master`.
- Introduced by: initial commit, always present.
- Evidence: ADE-3 baseline comment; `gh pr checks`.

## Blast radius

Every PR and push to master has been unchecked by the project's own CI. Branch protection requires only
`verify` until the job names below are added as required checks.

## Regression criterion (AC1)

AC1: a PR to `master` triggers the `CI` workflow (jobs `backend`, `frontend`, `docker-build`), observed on
this PR with `gh pr checks`.

AC2: the backend job is honest: steps that fail today are disabled with a comment and ticket key (ruff:
ADE-20, mypy: ADE-21) or deselect exactly the known-failing tests by node id (ADE-23, ADE-24); the 80%
coverage gate stays on and the two duplicate pytest runs become one.

AC3: the frontend and docker jobs are reported as they are; failures outside this ticket get a ticket and
the failing step is disabled with a comment naming it: frontend eslint (22 errors) is ADE-28, the backend
Dockerfile (copies a requirements.txt that does not exist) is ADE-27. Frontend tests and build pass.

## Fix constraints

Only `.github/workflows/ci.yml` and the work item. No test or source changes. Nothing is dropped
silently: every disabled step or test names its ticket.

## Risks

Medium (CI config). A wrong filter would leave CI silently off again; mitigated by observing the run on
this PR. Deselecting tests lowers what CI protects until ADE-23/24 are fixed; the lines are listed in
the workflow comments and removed as tickets close.
