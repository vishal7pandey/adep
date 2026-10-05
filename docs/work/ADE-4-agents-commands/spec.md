# ADE-4 — AGENTS.md commands were never executed

Status: spec-approved · Risk: low · Jira: ADE-4

## Repro

Environment: master @ 98becb0, Windows 11, Git Bash, uv 0.8.9, Node 24.18, global pnpm 11.22.0.

1. Run each command in the `AGENTS.md` "Commands" block.
2. Results on 2026-10-05:
   - `uv sync --all-extras`: works, lock unchanged.
   - `uv run pytest src/tests/ -v -m "not integration"`: runs; 2 failed, 1790 passed (ADE-23, ADE-24).
   - `make test-cov`: `make` is not installed here; the equivalent pytest command passes the 80% gate (about 90%).
   - `uv run ruff check src/`: runs, 1043 errors (ADE-20). `uv run mypy ...`: on the 3.14 venv stops with a numpy stub
     syntax error; on CI's Python 3.11 it reports 183 errors (ADE-21).
   - `uv run uvicorn src.api.main:app --reload --port 8000`: starts, `/health` returns `{"status":"ok"}`.
   - `cd frontend && pnpm install`: FAILS: `packageManager` pins pnpm 11.13.0, which pnpm refuses to run
     ("broken release"). After bumping the pin to 11.22.0: install works (needs `CI=true` when node_modules is
     stale), `pnpm test` 104 passed, `pnpm run build` works, `pnpm lint` 22 errors (ADE-28).

Automated repro: none (documentation); evidence is the command output above.

Reproducibility: always.

## Expected

An agent can copy each command from AGENTS.md and it either works, or the section says exactly why and which
ticket tracks it.

## Actual

The section claimed all commands work and mentioned `make` targets and `pnpm install` that do not run as-is.

## Root cause (with evidence)

- Where: `AGENTS.md` Commands block; `frontend/package.json` `packageManager`.
- Why it fails: the block was written from the Makefile, CI and package.json without running it; the pnpm pin
  points at a release pnpm itself marks broken.
- Introduced by: factory adoption (35534f1) and the initial commit for the pin.
- Evidence: command output above; CI frontend job installs fine on Linux via corepack, so the bump must keep it green.

## Blast radius

Docs plus one tooling pin. The pin affects local installs and corepack in CI.

## Regression criterion (AC1)

AC1: every command in the AGENTS.md Commands block has been run and the block states the real result;
the CI `frontend` job stays green with the new pnpm pin.

## Fix constraints

Edit only the project part of AGENTS.md (outside the factory block) and `packageManager` in
`frontend/package.json`. No lockfile change.

## Risks

Low. If corepack cannot fetch pnpm 11.22.0 the frontend CI job fails visibly on the PR and the pin is reverted.
