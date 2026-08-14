---
from: mgmt
to: backend
subject: "Migrate to uv — pyproject.toml + uv.lock, no pip/requirements.txt"
date: 2026-08-08T03:40:00+05:30
priority: high
status: done
message-id: 2026-08-08_0340_mgmt-to-backend-migrate-to-uv
---

## Context

The project currently uses `requirements.txt` and `requirements-dev.txt`
with no `pyproject.toml` or `uv.lock`. Per the new tooling standard
(PROTOCOL.md §10), **uv is the only allowed Python package manager.**

## Request

Migrate the project to uv:

1. **Create `pyproject.toml`** — move all dependencies from
   `requirements.txt` and `requirements-dev.txt` into proper
   `[project.dependencies]` and `[project.optional-dependencies]`
   sections. Include project metadata (name, version, python version,
   etc.).

2. **Run `uv lock`** — generate `uv.lock` from `pyproject.toml`.

3. **Commit `uv.lock`** to the repository.

4. **Keep `requirements.txt`** as a generated artifact only:
   `uv export --format requirements-txt > requirements.txt`
   This is for backwards compatibility with any tooling that still
   expects it. Do NOT manually edit `requirements.txt` going forward.

5. **Update test/run commands** to use `uv run`:
   - `uv run pytest` instead of `pytest`
   - `uv run python -m src.api.main` instead of `python -m src.api.main`

6. **Remove `requirements-dev.txt`** — dev dependencies go into
   `[project.optional-dependencies]` under `dev` in `pyproject.toml`.

## Acceptance Criteria

- [ ] `pyproject.toml` exists with all current dependencies
- [ ] `uv.lock` exists and is committed
- [ ] `uv sync` installs all dependencies correctly
- [ ] `uv run pytest` passes all 745 tests
- [ ] `requirements.txt` is generated (not manually edited)
- [ ] `requirements-dev.txt` is removed
- [ ] No `pip install` commands in any scripts or docs

## Constraints

- Do this BEFORE starting BLK-103 (e2e tests) so the test runner
  uses uv from the start
- If any dependency doesn't resolve cleanly in uv, report back

## Priority

Do this first, then proceed to BLK-103.

## Resolution

Migration complete. Created `pyproject.toml` with all dependencies from
`requirements.txt` and `requirements-dev.txt` (dev deps in
`[project.optional-dependencies]`). Generated `uv.lock` (120 packages).
`uv sync --all-extras` installs correctly. `uv run pytest` passes all
754 tests. `requirements.txt` regenerated via `uv export`. Removed
`requirements-dev.txt`. Updated all `pip install` references in source
files, README.md, and CONTRIBUTING.md to use `uv add` / `uv run`.
