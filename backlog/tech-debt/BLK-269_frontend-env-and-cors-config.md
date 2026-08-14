---
id: BLK-269
type: tech-debt
title: "Frontend API base URL and backend CORS are not configurable for production deployment"
priority: medium
status: backlog
phase: 5
owner: antigravity
created: 2026-08-09T10:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-180]
tags: [frontend, deployment, config, env]
---

## Description

The frontend's `lib/api.ts` and `lib/sse.ts` both default to `http://localhost:8000/api/v1`. There is no `.env.example` in `frontend/`, no `NEXT_PUBLIC_API_BASE_URL` documentation, and no production deployment story.

When the app is deployed (or run via docker-compose as BLK-180 targets), the browser would point at the user's own localhost, not the backend. There is also no `frontend/.env.example` telling operators which vars to set.

Additionally, the backend's CORS is hardcoded to `localhost:3000` / `127.0.0.1:3000` — a deployed frontend origin would be blocked entirely.

## Problem Statement

- `NEXT_PUBLIC_API_BASE_URL` is used but undocumented
- `.env.example` at repo root covers backend only, not frontend
- Backend CORS allow-list is hardcoded to localhost; production needs configurable origins
- No guidance in README or CONTRIBUTING for deploying the frontend against a remote backend

## Acceptance Criteria

- [ ] Add `frontend/.env.example` with `NEXT_PUBLIC_API_BASE_URL` documented
- [ ] Make backend CORS origins configurable via an env var (e.g. `ADE_CORS_ORIGINS`)
- [ ] Document the deployment procedure for a non-localhost frontend in README
- [ ] Ensure docker-compose (BLK-180) wires frontend to backend hostname correctly

## Constraints

- Must preserve localhost defaults for local dev
- Must follow the config env standardization direction in BLK-176

## Dependencies

- BLK-180 (frontend Dockerfile)

## Notes

- Found during infrastructure & deployment audit
- Related to BLK-176 (config/environment standardization)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `antigravity` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
