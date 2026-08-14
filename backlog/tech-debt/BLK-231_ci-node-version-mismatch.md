---
id: BLK-231
type: tech-debt
title: "CI uses Node 20 but project uses Node 24 locally — version mismatch between dev and CI"
priority: low
status: verifying
phase: 2
owner: opencode
created: 2026-08-09T14:15:00+05:30
started: 2026-08-09T16:10:00+05:30
completed: 2026-08-09T16:30:00+05:30
estimate: S
depends-on: []
tags: [ci, node, versions, inconsistency, frontend]
---

## Description

The CI pipeline sets up Node 20:

```yaml
- name: Set up Node
  uses: actions/setup-node@v4
  with:
    node-version: "20"
```

The developer's environment uses Node 24 (per the dev environment configuration). The `frontend/package.json` doesn't specify an `engines` field, so there's no enforced Node version. Next.js 15 (used by this project) requires Node 18.18+, so both Node 20 and Node 24 work, but they may produce different build outputs or have different behavior with certain APIs.

## Problem Statement

- A developer using Node 24 may produce a build that behaves differently in CI (Node 20)
- No `engines` field in `package.json` means no version enforcement — any Node version can be used
- The `.nvmrc` or `.tool-versions` file doesn't exist, so there's no signal to tools like `nvm` or `asdf` about the expected version
- This is the same class of inconsistency as BLK-194 (CI uses npm, project uses pnpm) — CI doesn't match the development environment

## Acceptance Criteria

- [ ] Add `engines` field to `frontend/package.json` specifying the minimum Node version
- [ ] Either update CI to match the developer's Node version (24) or document Node 20 as the target and add `.nvmrc`
- [ ] Consider using `actions/setup-node` with `node-version-file` pointing to `.nvmrc` for automatic version alignment

## Constraints

- Don't break the CI build — verify the chosen Node version works with all dependencies
- Node 20 is LTS and may be the safer choice for CI stability

## Dependencies

- `.github/workflows/ci.yml`
- `frontend/package.json`

## Notes

- Found during full-repo audit; the Node version mismatch is not currently causing failures but it's a latent risk

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Aligned everything on Node 24 (matches local dev; satisfies Next 16.3's `node>=20.9` engine): CI `frontend` job now uses `node-version-file: .nvmrc` (auto-follow), a root `.nvmrc` with `24` was added, and `frontend/package.json` got an `engines` minimum of `>=20.9.0`. Docker uses `node:24-alpine` (BLK-180/193). `pnpm install` + `pnpm run build` verified under Node 24.

## Evidence

- `.nvmrc` at repo root: `24`.
- `.github/workflows/ci.yml`: `node-version-file: .nvmrc` (replaces `node-version: "20"`).
- `frontend/package.json`: `"engines": { "node": ">=20.9.0" }`.
- `pnpm run build` clean under Node 24.
