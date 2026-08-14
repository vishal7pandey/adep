---
id: BLK-235
type: tech-debt
title: "Makefile references requirements-dev.txt which doesn't exist — 'make install' will fail"
priority: medium
status: verifying
phase: 2
owner: opencode
created: 2026-08-09T14:35:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: 2026-08-09T15:45:00+05:30
estimate: S
depends-on: []
tags: [makefile, infra, broken, dependencies]
---

## Description

The Makefile `install` target runs:

```makefile
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
```

`requirements-dev.txt` does not exist in the repository. The `pyproject.toml` defines dev dependencies in the `dev` optional group, and CI uses `uv sync --all-extras` to install them. But `make install` will fail with:

```
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements-dev.txt'
```

## Problem Statement

- `make install` is broken — it will fail on the second line
- A new developer following CONTRIBUTING.md (which likely says `make install`) will hit this error immediately
- The Makefile uses `pip` instead of `uv` (already covered in BLK-200), but the missing `requirements-dev.txt` is a separate, more critical issue — it's a hard failure, not just a style inconsistency
- The `requirements.txt` file itself is flagged as redundant in BLK-202

## Acceptance Criteria

- [ ] Replace `make install` with `uv sync --all-extras` (coordinates with BLK-200)
- [ ] Or, if keeping pip: remove the `requirements-dev.txt` line and add `pip install -e ".[dev]"` to install dev dependencies from `pyproject.toml`
- [ ] Verify `make install` works after the fix

## Constraints

- Coordinate with BLK-200 (Makefile uses pip not uv) — both should be fixed together

## Dependencies

- `Makefile`
- `requirements-dev.txt` (missing)
- Related to BLK-200 (Makefile pip vs uv) and BLK-202 (requirements.txt redundant)

## Notes

- Found during full-repo audit; this is a hard failure that would block any new developer following the documented setup process

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Duplicate content of BLK-178 — merged. `make install` now runs `uv sync --all-extras` (BLK-200 coordination), which also covers dev deps from the `dev` optional group in `pyproject.toml`. `requirements-dev.txt` line removed.

## Evidence

- `Makefile` `install:` → `uv sync --all-extras`; `uv sync --all-extras` verified in repo root (Resolved 121, Installed 8 packages: mypy, pytest-cov, ruff, coverage…).
- See BLK-178 Resolution + Evidence (merged duplicate).
