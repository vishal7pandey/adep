---
id: BLK-063
type: feature
title: "CI/CD pipeline, Docker, and release automation"
priority: low
status: backlog
phase: 4
owner: unassigned
created: 2026-08-08T00:15:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-026, BLK-018]
tags: [devops, ci/cd, docker, testing, deployment, release]
---

## Description

Set up continuous integration, Docker containerization, and release
automation for the backend and frontend. Ensures reproducible builds,
test runs, and deployment artifacts.

## Components

### 1. Backend Docker
- `Dockerfile` in `src/` or repo root
- Python 3.11+ base image
- Install deps from `pyproject.toml` via `uv sync`
- Copy `src/` and frontend build to container
- Expose port 8000
- Use `uvicorn` entrypoint
- `.dockerignore` for `.adep/`, `node_modules/`, etc.

### 2. Frontend Docker
- `Dockerfile` in `frontend/`
- Multi-stage build: `node:20-alpine` → install → build → nginx
- Nginx config for Next.js static export
- Expose port 3000

### 3. Docker Compose
- `docker-compose.yml` at root
- Services:
  - `backend` on port 8000
  - `frontend` on port 3000
  - shared volume for `.adep/` data
- `docker-compose.override.yml` for local dev

### 4. GitHub Actions (or local CI)
- `.github/workflows/ci.yml`
- Jobs:
  - Backend lint (`ruff`)
  - Backend tests (`pytest`)
  - Backend type check (`mypy`)
  - Frontend lint (`eslint`)
  - Frontend build (`next build`)
  - Frontend unit tests (`jest`)
- Run on every PR and push to `main`

### 5. Release Automation
- `bump2version` or manual `pyproject.toml` version bump
- `CHANGELOG.md` with conventional commits
- Git tags for releases (`v0.1.0`, `v0.2.0`)
- GitHub Release with artifacts

### 6. Pre-commit Hooks
- `pre-commit` config:
  - `ruff` for backend
  - `black` or `ruff format` for backend
  - `eslint --fix` for frontend
  - `prettier` for frontend
  - `mypy` type check

## Acceptance Criteria

- [ ] `docker build -t ade-backend -f Dockerfile .` works
- [ ] `docker build -t ade-frontend -f frontend/Dockerfile .` works
- [ ] `docker-compose up` starts both services
- [ ] Workbench connects to backend in Docker
- [ ] `.github/workflows/ci.yml` runs backend + frontend checks
- [ ] Pre-commit hooks installed and documented
- [ ] `CHANGELOG.md` exists
- [ ] Release process documented in `README.md`
- [ ] `.adep/` data persisted in named volume

## Constraints

- CI must run offline-friendly tests (mock external providers)
- Do not push Docker images to registry in v1 (local builds only)
- Keep Dockerfiles minimal [SF]

## Dependencies

- BLK-018 (FastAPI scaffold)
- BLK-026 (frontend scaffold)
