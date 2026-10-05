# ADE-1 — Test plan: CI branch filters and an honest backend job

Status: plan-approved · Risk: medium · Jira: ADE-1

Test framework and conventions found: the "test" is the workflow itself; observed with
`gh pr checks <n>` on the PR. Local tests are unchanged (`python -m pytest src/tests/`).

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | manual | PR #4 checks list | CI workflow starts on a PR to master | n/a: single filter value | n/a: the previous behaviour (no run) is the bug | verified |
| AC2 | manual | backend job log on PR #4 | pytest + coverage step runs and passes with the deselects | coverage gate 80 still enforced | a known-failing test not deselected would turn the job red | verified |
| AC3 | manual | frontend and docker-build job results on PR #4 | reported as they are | n/a: no boundary | red jobs get tickets | verified |

## Regression risk

None for source code. `verify` workflow unaffected.

## Untestable AC

None.

## Manual checks

Level manual is used because a workflow can only be exercised by GitHub. Steps: push the branch, open the
PR, run `gh pr checks 4`, read the failing step logs if any.

## Audit (after implementation)

Recorded in the Jira comment and PR description with the run URL.
