---
id: BLK-194
type: bug
title: "CI pipeline uses npm ci but project standardizes on pnpm — both lockfiles committed"
priority: medium
status: verifying
phase: 2
owner: opencode
created: 2026-08-09T11:05:00+05:30
started: 2026-08-09T15:00:00+05:30
completed: 2026-08-09T16:10:00+05:30
estimate: S
depends-on: []
tags: [ci, frontend, package-manager, inconsistency]
---

## Description

The CI pipeline (`.github/workflows/ci.yml`) installs frontend dependencies with `npm ci`:

```yaml
- name: Install dependencies
  working-directory: frontend
  run: npm ci
```

But the README, CONTRIBUTING.md, and the user's environment all use `pnpm` as the Node.js package manager. The `frontend/` directory contains **both** `package-lock.json` (npm) and `pnpm-lock.yaml` (pnpm), which is itself a problem — two lockfiles for different package managers in the same project guarantees dependency drift.

## Problem Statement

- CI installs with `npm ci` using `package-lock.json`, while developers install with `pnpm install` using `pnpm-lock.yaml` — the two lockfiles can resolve to different transitive dependency versions
- Having both lockfiles committed is a known anti-pattern that causes "works in CI but not locally" (or vice versa) bugs
- The project's own conventions (`CONTRIBUTING.md`) say to use `pnpm`, but CI doesn't follow that convention
- `npm ci` requires `package-lock.json` to be in sync with `package.json`; if a developer updates deps via pnpm only, the npm lockfile goes stale and CI breaks silently or with confusing errors

## Acceptance Criteria

- [ ] Remove `frontend/package-lock.json` from the repo
- [ ] Update CI to use pnpm: `corepack enable`, `pnpm install --frozen-lockfile`
- [ ] Add `.gitignore` entry for `package-lock.json` to prevent re-creation
- [ ] Verify CI passes with pnpm-based install and build

## Constraints

- Don't touch the backend CI steps (those use `uv` correctly)
- Ensure `pnpm-lock.yaml` is up to date before switching CI

## Dependencies

- `.github/workflows/ci.yml`
- `frontend/package-lock.json` (to be removed)
- `frontend/pnpm-lock.yaml` (to be kept as sole lockfile)

## Notes

- Found during full-repo audit; the dual-lockfile situation is a classic sign of inconsistent tooling decisions

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

- Deleted `frontend/package-lock.json` (dual-lockfile antipattern removed — matches PROTOCOL §11.2 pnpm-only).
- CI frontend job now: `node-version: "24"`, `corepack enable`, `pnpm install --frozen-lockfile`, `pnpm run lint`, `pnpm run build` (test job added by cline).
- Root `.gitignore` gained `frontend/package-lock.json` so npm's lockfile cannot be re-created in this tree.
- `pnpm-lock.yaml` is current (frozen install verified against it). Node alignment to 24 closes the CI/local Node mismatch (see BLK-231).

## Evidence

- `.github/workflows/ci.yml` frontend job: npm ci → `pnpm install --frozen-lockfile`; node `"20"` → `"24"`; `npm run lint/build` → `pnpm run lint/build`.
- `pnpm install --frozen-lockfile` in `frontend/` → `Done in 9.2s using pnpm v11.13.0`; `pnpm run build` → `✓ Compiled successfully`, type-check clean.
- `git status` shows `frontend/package-lock.json` deleted; `.gitignore` contains `frontend/package-lock.json`.
- `git ls-files frontend/` shows `pnpm-lock.yaml` untracked (to be committed by whoever commits this wave), `package-lock.json` removed from tracking.
