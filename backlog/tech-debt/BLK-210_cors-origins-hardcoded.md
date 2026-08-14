---
id: BLK-210
type: tech-debt
title: "CORS hardcoded to localhost:3000 — no environment-based configuration for production deployments"
priority: low
status: backlog
phase: 2
owner: opencode
created: 2026-08-09T12:25:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [cors, security, config, deployment, hardcoding]
---

## Description

In `src/api/main.py`, CORS origins are hardcoded:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

There is no environment variable to configure allowed origins. In any non-local deployment (Docker, staging, production), the frontend will be blocked by CORS unless the backend is modified.

## Problem Statement

- Any deployment that doesn't run on `localhost:3000` will have CORS issues
- The Docker Compose setup maps frontend to port 3000 on the host, but if the frontend is deployed separately (different domain, different port), CORS will block all API requests
- `allow_methods=["*"]` and `allow_headers=["*"]` with `allow_credentials=True` is overly permissive — this combination is a known security concern
- The `.env.example` file has no `ADE_CORS_ORIGINS` variable, suggesting CORS configuration was never considered for non-local environments

## Acceptance Criteria

- [ ] Add `cors_origins` setting to `src/config.py` (comma-separated list, default to `http://localhost:3000,http://127.0.0.1:3000`)
- [ ] Add `ADE_CORS_ORIGINS` to `.env.example`
- [ ] Update `src/api/main.py` to read origins from settings
- [ ] Consider narrowing `allow_methods` and `allow_headers` to only what's needed (GET, POST, PUT, DELETE, PATCH, OPTIONS; Authorization, Content-Type)

## Constraints

- Keep localhost defaults for development convenience
- Don't break existing local development workflow

## Dependencies

- `src/api/main.py`
- `src/config.py`
- `.env.example`

## Notes

- Found during full-repo audit; this is a common oversight in FastAPI projects that are developed locally and never configured for deployment

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
