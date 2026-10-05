# ADE-5 — Plan: pre-commit hooks

Status: plan-approved · Risk: low · Jira: ADE-5
Created: 2026-10-05 · Slug: pre-commit-hooks · Spec: spec.md

## Summary

Add the dependency, fix the hook config (pins, excludes, disabled hooks with tickets), install, document, then run
all hooks once in a separate commit.

**Size:** S

## Current state

`.pre-commit-config.yaml` (ruff, ruff-format, mypy, hygiene hooks), `pyproject.toml` dev extras, `AGENTS.md`.

## Approach

Commit 1: `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `AGENTS.md`, this work item.
Commit 2: the files the hooks rewrite (only that), so history separates config from churn.

**Alternatives rejected**
- Keep ruff lint/mypy hooks: they would block every commit until ADE-20/21 are done.
- Skip the repo-wide run: every later commit would carry unrelated reformatting.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Add pre-commit to dev extras, relock | `pyproject.toml`, `uv.lock` | AC1 | `git diff --stat uv.lock` additions only |
| T2 | Fix config | `.pre-commit-config.yaml` | AC3, AC4 | `pre-commit run --all-files` |
| T3 | Install and document | `AGENTS.md` | AC2 | `.git/hooks/pre-commit` exists |
| T4 | Run hooks over the repo in its own commit | rewritten files | AC5 | second run passes; pytest unchanged |

## Data, API and migration impact

None.

## Security and failure modes

No secrets. `sample-data/` excluded.

## Rollout and rollback

Merge; revert the format commit to undo churn; hook is per clone (`pre-commit install`).

## Risks and open points

- Merge conflicts with open branches.
