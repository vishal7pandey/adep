---
id: BLK-178
type: bug
title: "Makefile 'make install' references deleted requirements-dev.txt"
priority: high
status: verifying
phase: 5
owner: opencode
created: 2026-08-09T10:05:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: 2026-08-09T15:45:00+05:30
estimate: S
depends-on: []
tags: [build, devx, tooling, regression]
---

## Description

`make install` in the root `Makefile` runs `pip install -r requirements-dev.txt`, but `requirements-dev.txt` was deleted from the repo. BLK-154 fixed the CI pipeline which referenced the same file, but the Makefile was not updated. Running `make install` today fails immediately.

This is a developer-experience regression: new contributors following the README or Makefile will hit this failure.

## Acceptance Criteria

- [ ] Update `Makefile` `install` target to use `pip install -r requirements.txt` plus the dev extras from `pyproject.toml` (`pip install -e ".[dev]"`)
- [ ] Run `make install` successfully in a fresh environment
- [ ] Verify CI still passes

## Constraints

- Must keep the same dev deps: pytest, pytest-cov, ruff, mypy
- Should not break existing contributors who use `uv`

## Dependencies

- None

## Notes

- The `pyproject.toml` already declares `[project.optional-dependencies].dev` which is the canonical location for dev deps
- Related to BLK-154 (CI pipeline broken — references deleted requirements-dev.txt)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Merged with duplicate BLK-235 and coordinated with BLK-200 (Makefile pip→uv). `make install` rewritten to `uv sync --all-extras` — the canonical install per PROTOCOL §11.1 and CONTRIBUTING.md, which installs `pyproject.toml` deps + `dev` extras (pytest, pytest-cov, ruff, mypy). The `requirements-dev.txt` line is gone. Same sweep converted `dev`, `test`, `test-cov`, `seed` targets to `uv run`.

## Evidence

- `Makefile` diff: `install:` body is now `uv sync --all-extras`; `dev` → `uv run uvicorn ...`; `test` → `uv run pytest src/tests/ -v`; `test-cov` → `uv run pytest ... --cov=src --cov-report=term-missing --cov-fail-under=80`; `seed` → `uv run python -m scripts.seed`.
- `uv sync --all-extras` run in repo root succeeded: `Resolved 121 packages`, `Installed 8 packages` (mypy 2.3.0, pytest-cov 7.1.0, ruff 0.16.2, coverage 7.15.4, etc.).
- No `requirements-dev.txt` reference remains anywhere in the Makefile.
