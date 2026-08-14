---
id: BLK-195
type: bug
title: "Backend Dockerfile uses pip install instead of uv — inconsistent package management"
priority: medium
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T11:10:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [docker, infra, backend, package-manager, inconsistency]
---

## Description

The backend `Dockerfile` installs dependencies with:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```

The project has standardized on `uv` for Python dependency management — `pyproject.toml` is the source of truth, `uv.lock` is the lockfile, and `uv sync` is the documented install command in both README and CONTRIBUTING.md. `requirements.txt` is an auto-generated export (`uv export --format requirements-txt`) that is ~2,990 lines long (see BLK-202).

## Problem Statement

- Docker builds use `pip` with an auto-generated `requirements.txt` while the project uses `uv` with `pyproject.toml` + `uv.lock` everywhere else
- `requirements.txt` is a point-in-time export that can go stale if someone forgets to re-run `uv export` after updating `pyproject.toml`
- `pip install` doesn't respect `uv.lock`'s pinned transitive dependencies the same way `uv sync` does — subtle version differences can emerge
- The Dockerfile doesn't install the project in editable mode (`-e .`), which means `src/` imports might not resolve the same way as in dev

## Acceptance Criteria

- [ ] Replace `pip install -r requirements.txt` with `uv sync --frozen --no-dev` in the Dockerfile
- [ ] Install `uv` in the Docker image (copy from official installer or use `astral-sh/setup-uv` equivalent)
- [ ] Remove `COPY requirements.txt` — use `COPY pyproject.toml uv.lock` instead
- [ ] Verify the Docker image builds and the backend starts successfully
- [ ] Optionally remove `requirements.txt` from the repo entirely (see BLK-202)

## Constraints

- Keep the Docker image size reasonable — `uv` is a single binary, minimal overhead
- Ensure system dependencies (`libgl1`, `libglib2.0-0`) are still installed
- Don't break the existing health check or entrypoint

## Dependencies

- `Dockerfile`
- `pyproject.toml`, `uv.lock`
- Related to BLK-202 (requirements.txt redundancy)

## Notes

- Found during full-repo audit; the Dockerfile was likely written before the `uv` migration and never updated

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
