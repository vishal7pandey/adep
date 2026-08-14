---
id: BLK-200
type: tech-debt
title: "Makefile uses pip install contradicting uv sync in README and CONTRIBUTING"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T11:35:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [makefile, package-manager, inconsistency, onboarding]
---

## Description

The `Makefile` `install` target uses:

```makefile
install:
    pip install -e ".[dev]"
```

But `README.md` and `CONTRIBUTING.md` both instruct developers to use:

```
uv sync
```

The project has `pyproject.toml` configured for `uv` with a `uv.lock` lockfile. The Makefile was never updated after the `uv` migration.

## Problem Statement

- A developer who runs `make install` gets a different environment than one who follows the README
- `pip install -e ".[dev]"` doesn't use `uv.lock`, so transitive dependency versions may differ
- The Makefile is referenced in `CONTRIBUTING.md` as the source of development commands, creating a contradiction: the docs say "use `uv sync`" but also "use `make install`"
- This is the same class of inconsistency as BLK-195 (Dockerfile uses pip) — the `uv` migration was incomplete

## Acceptance Criteria

- [ ] Update Makefile `install` target to use `uv sync --all-extras`
- [ ] Review all other Makefile targets for `pip`/`python` usage and update to `uv` equivalents where applicable
- [ ] Verify `make install` produces the same environment as `uv sync`

## Constraints

- Keep the Makefile as a convenience wrapper — just point it at the right commands
- Don't remove targets, only update their underlying commands

## Dependencies

- `Makefile`
- Related to BLK-195 (Dockerfile uses pip instead of uv)

## Notes

- Found during full-repo audit; the `uv` migration touched README and CONTRIBUTING but missed the Makefile and Dockerfile

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
