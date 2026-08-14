---
id: BLK-193
type: bug
title: "Frontend Dockerfile referenced in docker-compose.yml does not exist"
priority: high
status: verifying
phase: 2
owner: opencode
created: 2026-08-09T11:00:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: 2026-08-09T16:10:00+05:30
estimate: S
depends-on: []
tags: [docker, infra, frontend, ci, deployment]
---

## Description

`docker-compose.yml` defines a `frontend` service that builds from `./frontend/Dockerfile`:

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
```

No `Dockerfile` exists in the `frontend/` directory. `docker compose up --build` will fail with a build context error for the frontend service. The backend Dockerfile exists at the repo root, but nobody created one for the frontend.

This means the entire Docker Compose setup — which is the documented path for containerized deployment — is broken for the frontend half of the stack.

## Problem Statement

- `docker compose up` fails immediately when trying to build the frontend service
- The Docker Compose file was committed without ever being tested end-to-end
- CI pipeline (`ci.yml`) doesn't test Docker builds, so this breakage goes undetected
- README references Docker as a deployment option, but it doesn't work

## Acceptance Criteria

- [ ] Create `frontend/Dockerfile` for the Next.js app (multi-stage build: install deps, build, run)
- [ ] `docker compose up --build` successfully starts both backend and frontend
- [ ] Frontend container connects to backend via environment variable (`NEXT_PUBLIC_API_BASE_URL`)
- [ ] Add Docker build test to CI or document that Docker builds are manual-only

## Constraints

- Use the Node.js version matching `frontend/package.json` (currently Node 20 in CI, but project uses Node 24 locally — pick one and be consistent)
- Use `pnpm` in the Dockerfile to match the project's package manager (see BLK-194 for CI/npm inconsistency)

## Dependencies

- `docker-compose.yml`
- `frontend/` directory
- Related to BLK-194 (CI uses npm instead of pnpm) and BLK-195 (Dockerfile uses pip instead of uv)

## Notes

- Found during full-repo audit; the backend Dockerfile exists and works, but the frontend was never containerized

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Duplicate problem of BLK-180 — the non-existent `frontend/Dockerfile` now exists. Details + evidence in BLK-180 Resolution/Evidence. Also pinned `packageManager: pnpm@11.13.0` in `frontend/package.json` so corepack resolves a deterministic pnpm in CI and Docker. Test-execution wiring in `ci.yml` (`pnpm test`) is owned by cline per §2.1.

## Evidence

- `frontend/Dockerfile` present (multi-stage pnpm build).
- `pnpm install --frozen-lockfile` → `Done in 9.2s using pnpm v11.13.0`; `pnpm run build` → compiled + type-check clean, 9 static pages.
- `docker-compose.yml` parses with valid frontend build context.
- Local docker unavailable — `docker compose up --build` verification requested from cline.
