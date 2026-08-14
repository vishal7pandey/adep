---
id: BLK-180
type: bug
title: "docker-compose.yml references missing frontend/Dockerfile — compose up frontend always fails"
priority: high
status: verifying
phase: 5
owner: opencode
created: 2026-08-09T10:15:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: 2026-08-09T16:10:00+05:30
estimate: S
depends-on: []
tags: [docker, infrastructure, deployment, frontend]
---

## Description

`docker-compose.yml` declares a `frontend` service with `build: context: ./frontend, dockerfile: Dockerfile`. However, there is no `Dockerfile` in `frontend/` — the directory contains only `AGENTS.md`, `CLAUDE.md`, config files, `app/`, `components/`, `context/`, `lib/`, `public/`, and `tests/`.

Running `docker-compose up` (or `docker compose up`) will fail immediately for the frontend service with "Dockerfile not found" / "Cannot locate specified Dockerfile: Dockerfile".

The backend service builds successfully, but the full stack cannot be brought up.

## Root Cause

BLK-063 added the Docker backend + compose file, but the frontend Dockerfile was never created (or was lost in a refactor). The compose file references a non-existent file.

## Acceptance Criteria

- [ ] Create `frontend/Dockerfile` (Node-based multi-stage build: install, build, serve Next.js standalone)
- [ ] Verify `docker-compose up --build` brings up both backend on :8000 and frontend on :3000
- [ ] Frontend build passes in Docker and connects to backend via `NEXT_PUBLIC_API_BASE_URL`
- [ ] Update README with docker-compose instructions

## Constraints

- Must use frontend's `pnpm` workspace lock (`pnpm-lock.yaml`) or `npm` as appropriate
- Backend `depends_on` already handles ordering
- Should not require manual steps beyond `docker-compose up --build`

## Dependencies

- None

## Notes

- Found during infrastructure audit
- Backend Dockerfile already exists and works (BLK-063)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Created `frontend/Dockerfile` (multi-stage: `deps` = `corepack enable && pnpm install --frozen-lockfile` on `node:24-alpine`; `builder` = copy deps + source + `NEXT_PUBLIC_API_BASE_URL` build arg/env, `pnpm build`; `runner` = non-root `nextjs` user, copies `.next`, `node_modules`, `public`, `package.json`, `next.config.ts`, CMD `pnpm start`). Updated `docker-compose.yml`: removed deprecated `version: "3.8"` key (also part of BLK-227), added `NEXT_PUBLIC_API_BASE_URL` build arg + runtime env to the frontend service. Added `frontend/.dockerignore`. Node aligned to 24 in Docker, CI (BLK-193/231 consistency) and local dev.

## Evidence

- `frontend/Dockerfile` created (see file, 32 lines).
- `docker-compose.yml` parsed: `backend` and `frontend` services present; frontend `build: {context: './frontend', dockerfile: 'Dockerfile', args: {NEXT_PUBLIC_API_BASE_URL: '${NEXT_PUBLIC_API_BASE_URL:-http://localhost:8000/api/v1}'}}`.
- `pnpm run build` in `frontend/` completes: `✓ Compiled successfully`, `Finished TypeScript`, 9 static pages generated.
- Docker is not installed on this dev machine, so the `docker compose up --build` smoke can't be run locally — that exact verification is delegated to cline (and enforced by a new CI docker-build job, BLK-213).
