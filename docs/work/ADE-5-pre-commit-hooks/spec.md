# ADE-5 — Install the pre-commit hooks

Status: spec-approved · Risk: low · Jira: ADE-5

## Problem

`.pre-commit-config.yaml` existed but `pre-commit` was not a dependency and no `.git/hooks/pre-commit` was installed, so
the hooks never ran. Its pins (ruff v0.4.0, mypy v1.10.0) were also far from the versions locked in `uv.lock`
(ruff 0.16.2, mypy 2.3.0).

## Requirements and acceptance criteria

1. AC1: `pre-commit` is in the `dev` extras of `pyproject.toml` and `uv.lock` (additions only, no upgrades).
2. AC2: `uv run pre-commit install` installs `.git/hooks/pre-commit`; the steps are documented in `AGENTS.md`.
3. AC3: the hooks never touch `sample-data/` (the demo set), `uv.lock` or `frontend/pnpm-lock.yaml`.
4. AC4: hooks that cannot pass today are disabled with a comment and ticket, like CI (ADE-1): ruff lint with
   `--fix` (1043 errors, ADE-20) and mypy (183 errors, ADE-21). Active: ruff-format, trailing-whitespace,
   end-of-file-fixer, check-yaml, check-added-large-files. Ruff pin matches the lock (v0.16.2).
5. AC5: the hooks were run once over the whole repo in their own commit; a second run is a no-op; the
   non-integration test results are unchanged (2 failures before and after: ADE-23, ADE-24).

## Out of scope

Fixing lint/type errors (ADE-20, ADE-21).

## Risks

The format commit touches about 170 tracked files (175 Python files reformatted; whitespace/EOF fixes in
frontend, notebooks, fixtures). It is behaviour-neutral (ruff-format preserves the AST) and verified by the
test suite, but it can conflict with other open branches: merge it early.
