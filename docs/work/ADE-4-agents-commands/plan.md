# ADE-4 — Plan: make the AGENTS.md commands true

Status: plan-approved · Risk: low · Jira: ADE-4
Created: 2026-10-05 · Slug: agents-commands · Spec: spec.md

## Summary

Run every documented command, rewrite the Commands block and notes to match reality (including known failures
with tickets), and bump the broken pnpm pin in `frontend/package.json`.

**Size:** S

## Current state

`AGENTS.md` Commands block (lines 8-16), `Makefile`, `.github/workflows/ci.yml`, `frontend/package.json`.

## Approach

Execute, observe, document. Smallest tooling change: one version number.

**Alternatives rejected**
- Only document "use npx pnpm@latest": leaves the repo pin broken for everyone.
- Remove `packageManager`: loses corepack pinning in CI.

## Tasks

| # | Task | Files | Serves | Verify by |
|---|------|-------|--------|-----------|
| T1 | Run each command, record results | n/a | AC1 | outputs in spec.md |
| T2 | Bump pnpm pin | `frontend/package.json` | AC1 | local `pnpm install/test/build`; CI frontend job green |
| T3 | Rewrite Commands block and notes | `AGENTS.md` | AC1 | re-read against results |

## Data, API and migration impact

None.

## Security and failure modes

No secrets; `.env` not touched. The backend was started locally on port 8000 and stopped; no LLM calls.

## Rollout and rollback

Merge; revert to undo.

## Risks and open points

- Corepack may not resolve pnpm 11.22.0 on the runner; visible on the PR.
