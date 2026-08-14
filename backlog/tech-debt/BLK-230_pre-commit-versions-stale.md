---
id: BLK-230
type: tech-debt
title: "Pre-commit hooks pinned to older versions — ruff v0.4.0 and mypy v1.10.0 are behind current releases"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T14:10:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [pre-commit, linting, mypy, ruff, versions]
---

## Description

The `.pre-commit-config.yaml` pins:
- `ruff-pre-commit` to `v0.4.0` (current: v0.6+)
- `mirrors-mypy` to `v1.10.0` (current: v1.11+)
- `pre-commit-hooks` to `v4.6.0` (current: v4.6.0 — this one is fine)

Meanwhile, CI uses `uv sync --all-extras` which installs whatever `ruff` and `mypy` versions are in `pyproject.toml`'s dev dependencies. If the `pyproject.toml` versions differ from the pre-commit versions, developers get different lint/type results locally vs in CI.

## Problem Statement

- Pre-commit hook versions are pinned separately from `pyproject.toml` dev dependencies — they can drift
- A developer's pre-commit may pass with ruff v0.4.0 while CI fails with a newer ruff that has stricter rules
- The mypy version in pre-commit may produce different type errors than the mypy version in CI
- No `pre-commit autoupdate` is configured or documented as a maintenance task

## Acceptance Criteria

- [ ] Run `pre-commit autoupdate` to bring hook versions to latest
- [ ] Verify that `ruff` and `mypy` versions in `.pre-commit-config.yaml` match the versions in `pyproject.toml` dev dependencies
- [ ] Document a periodic `pre-commit autoupdate` cadence in CONTRIBUTING.md
- [ ] Verify CI and pre-commit produce the same lint/type results

## Constraints

- Don't upgrade without verifying that existing code passes the newer versions
- If newer ruff/mypy find new issues, fix them or add targeted ignores

## Dependencies

- `.pre-commit-config.yaml`
- `pyproject.toml` (dev dependency versions)

## Notes

- Found during full-repo audit; version drift between pre-commit and CI is a common maintenance gap

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
