---
id: BLK-207
type: bug
title: "run_api_depth_pipeline.py at repo root is an orphaned wrapper with no documentation or CI integration"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T12:10:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [garbage, scripts, repo-hygiene, dead-code]
---

## Description

`run_api_depth_pipeline.py` at the repo root is a 7-line convenience wrapper:

```python
"""Convenience wrapper for the API depth pipeline script."""

from scripts.run_api_depth_pipeline import main


if __name__ == "__main__":
    raise SystemExit(main())
```

It imports from `scripts/run_api_depth_pipeline.py` (which is a 10KB script). The wrapper at the root adds zero value — a developer can just run `python -m scripts.run_api_depth_pipeline` or `python scripts/run_api_depth_pipeline.py` directly. The wrapper exists at the wrong level (repo root) and adds an unnecessary indirection layer.

## Problem Statement

- A 7-line file at the repo root that just re-exports and calls a function from `scripts/` — this is clutter
- It's not documented in README or CONTRIBUTING
- It's not referenced by CI, Makefile, or any other tooling
- It sets a precedent for putting wrapper scripts at the repo root instead of using proper entry points or Makefile targets

## Acceptance Criteria

- [ ] Delete `run_api_depth_pipeline.py` from the repo root
- [ ] If the script is useful, add a `make depth-pipeline` target to the Makefile that runs `python -m scripts.run_api_depth_pipeline`
- [ ] Document the script in CONTRIBUTING.md if it's part of the development workflow

## Constraints

- Don't delete `scripts/run_api_depth_pipeline.py` itself — only the root wrapper

## Dependencies

- `run_api_depth_pipeline.py` (root)
- `scripts/run_api_depth_pipeline.py` (actual script)

## Notes

- Found during full-repo audit; this is a minor issue but contributes to repo root clutter

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
