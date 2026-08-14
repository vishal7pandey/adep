---
id: BLK-226
type: tech-debt
title: "Dockerfile doesn't install project in editable mode — src/ imports may not resolve correctly in container"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T13:50:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [docker, infra, packaging, imports]
---

## Description

The backend `Dockerfile` installs dependencies but never installs the project itself:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/
```

There's no `RUN pip install -e .` or `RUN pip install .` step. The `pyproject.toml` defines the project as `ade` with packages under `src/`. Without installing the project, Python may not recognize `src` as a package root, and imports like `from src.api.main import app` work only because `WORKDIR /app` puts the `src/` directory on the Python path implicitly.

## Problem Statement

- The project is not installed as a package in the Docker image — it works by coincidence (WORKDIR + relative imports), not by design
- If the entrypoint or working directory changes, imports will break
- `pip install -e .` would properly register the package and make `src` a recognized root
- The `uvicorn` command `src.api.main:app` works because of the implicit path, but `python -m src.api.main` might not

## Acceptance Criteria

- [ ] Add `COPY pyproject.toml .` before the install step
- [ ] Add `RUN pip install --no-deps -e .` after installing dependencies (or `uv sync` per BLK-195)
- [ ] Verify the Docker image builds and the backend starts successfully
- [ ] Verify both `uvicorn src.api.main:app` and `python -m src.api.main` work in the container

## Constraints

- Don't reinstall dependencies — use `--no-deps` to avoid reinstalling what's already in `requirements.txt`
- Coordinate with BLK-195 (Dockerfile uv migration) — if switching to `uv sync`, this is handled automatically

## Dependencies

- `Dockerfile`
- `pyproject.toml`
- Related to BLK-195 (Dockerfile uses pip instead of uv)

## Notes

- Found during full-repo audit; the Dockerfile works but for the wrong reasons — implicit path resolution instead of proper package installation

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
