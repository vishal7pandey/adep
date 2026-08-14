---
id: BLK-213
type: tech-debt
title: "CI pipeline has no Docker build test — broken Docker Compose goes undetected"
priority: low
status: verifying
phase: 2
owner: opencode
created: 2026-08-09T12:40:00+05:30
started: 2026-08-09T16:10:00+05:30
completed: 2026-08-09T16:30:00+05:30
estimate: S
depends-on: []
tags: [ci, docker, deployment, testing]
---

## Description

The CI pipeline (`.github/workflows/ci.yml`) runs backend lint, type check, tests, coverage, and frontend lint + build. It does **not** test Docker builds — neither `docker build` for the backend Dockerfile nor `docker compose build` for the full stack.

This is why BLK-193 (missing frontend Dockerfile) went undetected: the Docker Compose file references a Dockerfile that doesn't exist, but CI never tries to build it.

## Problem Statement

- Docker builds can be broken without CI noticing
- The Docker Compose setup is the documented deployment path, but it's never validated
- Infrastructure changes (Dockerfile, docker-compose.yml, .dockerignore) have no automated verification
- A developer can merge a change that breaks `docker compose up` and CI will be green

## Acceptance Criteria

- [ ] Add a Docker build job to `ci.yml` that runs `docker build .` for the backend and `docker compose build` for the full stack
- [ ] The job should run on every PR and push to main
- [ ] Optionally add a smoke test that starts the containers and hits `/health`
- [ ] Don't require Docker build to pass for PRs that don't touch Docker files (use path filters)

## Constraints

- Docker builds are slow — consider caching or only running on path-filtered changes
- Don't require a working Azure provider for Docker smoke tests

## Dependencies

- `.github/workflows/ci.yml`
- `Dockerfile`, `docker-compose.yml`
- Related to BLK-193 (missing frontend Dockerfile) — that bug would have been caught by this

## Notes

- Found during full-repo audit; CI coverage is good for code but absent for infrastructure

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Added a `docker-build` job to `.github/workflows/ci.yml` (runs every push/PR; the two heavy steps only actually run when Docker-relevant files changed, via `dorny/paths-filter@v3` over `Dockerfile`, `docker-compose.yml`, `frontend/Dockerfile`, `.dockerignore`, `frontend/.dockerignore`, and the workflow file). This is exactly the gate that would have caught BLK-180/193.

## Evidence

- `.github/workflows/ci.yml` `docker-build` job: checkout → path filter → `docker build -f Dockerfile -t adep-backend:ci .` + `docker compose build`, each gated on `steps.filter.outputs.docker == 'true'`.
- Docker not installed locally; red/green of this job is for the CI runner / cline to confirm.
