# ADE-1 — Plan: CI branch filters and an honest backend job

Status: plan-approved · Risk: medium · Jira: ADE-1
Created: 2026-10-05 · Slug: ci-branch-filters · Spec: spec.md

## Summary

Point `ci.yml` at `master`, and make the backend job reflect reality: comment out ruff and mypy (tickets
ADE-20, ADE-21), run pytest once with the coverage gate, deselecting the ten known-failing tests by node
id (ADE-23, ADE-24).

**Size:** S

## Current state

`.github/workflows/ci.yml` has jobs `backend`, `frontend`, `docker-build`; filters on `main`. Baseline from
ADE-3 on a clean Python 3.11 checkout: coverage 90.02% (gate passes), 12 failing tests of which two (ADE-6)
were local venv artefacts and one (ADE-25, timing benchmark) is machine dependent.

## Approach

Edit the workflow only; push and watch the real run on the PR. If a step fails for a new reason on
GitHub's runner, fix small or file a ticket and disable that exact thing with a comment.

**Alternatives rejected**
- Rename the default branch to `main`: affects every clone and the protection rules; owner decision.
- Drop the whole pytest step: loses the 90 percent of tests that pass.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Branch filters to master | `.github/workflows/ci.yml` | AC1 | `gh pr checks` shows CI jobs |
| T2 | Disable ruff/mypy with comments, merge pytest runs, deselect known failures | `.github/workflows/ci.yml` | AC2 | backend job result |
| T3 | Report frontend/docker results | n/a | AC3 | job results, tickets if red |

## Data, API and migration impact

None.

## Security and failure modes

No secrets involved. Workflow permissions unchanged.

## Rollout and rollback

Merge; revert the commit to undo. After merge, the required checks in branch protection can include the
CI job names.

## Risks and open points

- GitHub runner may expose failures not seen locally (Linux, Node 24, pnpm); handled per AC3.
