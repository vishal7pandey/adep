---
id: BLK-227
type: tech-debt
title: "docker-compose.yml uses deprecated 'version' key and has no environment variables for frontend"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T13:55:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [docker, infra, docker-compose, deprecated, config]
---

## Description

Two issues in `docker-compose.yml`:

1. **Deprecated `version` key**: Line 3 specifies `version: "3.8"`. Docker Compose v2 (the current standard) ignores this key and logs a deprecation warning. The `version` key has been deprecated since Docker Compose Specification v1.27.0.

2. **No environment variables for frontend**: The frontend service has no `environment` section to pass `NEXT_PUBLIC_API_BASE_URL`. The frontend needs to know where the backend is — in Docker Compose, the backend is at `http://backend:8000/api/v1` (service name as hostname), not `http://localhost:8000/api/v1` (the default in the frontend code). Without this environment variable, the frontend will try to connect to `localhost:8000` inside its own container and fail.

## Problem Statement

- The `version` key is cosmetic but generates deprecation warnings on every `docker compose` command
- The missing `NEXT_PUBLIC_API_BASE_URL` means the frontend container can't reach the backend — the frontend will load but all API calls will fail with connection errors
- This is another reason (beyond BLK-193) that `docker compose up` doesn't actually work end-to-end

## Acceptance Criteria

- [ ] Remove the `version: "3.8"` line
- [ ] Add `environment` section to the frontend service:
  ```yaml
  environment:
    - NEXT_PUBLIC_API_BASE_URL=http://backend:8000/api/v1
  ```
- [ ] Verify the frontend can reach the backend when both containers are running

## Constraints

- `NEXT_PUBLIC_` prefix is required for Next.js client-side environment variables
- The backend service name `backend` is used as the hostname (Docker Compose DNS)

## Dependencies

- `docker-compose.yml`
- Related to BLK-193 (missing frontend Dockerfile) — both must be fixed for Docker Compose to work

## Notes

- Found during full-repo audit; the docker-compose.yml was written but never tested

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
