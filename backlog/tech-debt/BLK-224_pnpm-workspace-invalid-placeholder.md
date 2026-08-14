---
id: BLK-224
type: tech-debt
title: "pnpm-workspace.yaml has invalid placeholder content — 'set this to true or false' is not valid YAML config"
priority: low
status: verifying
phase: 2
owner: opencode
created: 2026-08-09T13:40:00+05:30
started: 2026-08-09T15:30:00+05:30
completed: 2026-08-09T15:40:00+05:30
estimate: S
depends-on: []
tags: [frontend, config, pnpm, invalid]
---

## Description

`frontend/pnpm-workspace.yaml` contains:

```yaml
allowBuilds:
  unrs-resolver: set this to true or false
```

The value `set this to true or false` is a placeholder instruction that was never replaced with an actual boolean value. This is not valid pnpm configuration — `allowBuilds` expects boolean values (`true` or `false`), not instructional text.

## Problem Statement

- pnpm may ignore this file or produce a warning during install
- The file was clearly created from a template or prompt and never finalized
- It indicates that the frontend setup was done hastily without verification

## Acceptance Criteria

- [ ] Replace `set this to true or false` with `true` (to allow building native dependencies like `unrs-resolver`)
- [ ] Verify `pnpm install` runs without warnings related to this file
- [ ] Alternatively, remove the file entirely if `allowBuilds` is not needed

## Constraints

- None — single line fix

## Dependencies

- `frontend/pnpm-workspace.yaml`

## Notes

- Found during full-repo audit; a small but clear indicator of incomplete setup

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `opencode` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

## Resolution

Replaced the placeholder text with a real boolean per the ticket's primary AC:

```yaml
allowBuilds:
  unrs-resolver: true
```

`pnpm install --frozen-lockfile` completes with no warning referencing this file; `unrs-resolver` builds natively (`postinstall: Done`), so native dep builds are permitted as BLK-224 intends.

## Evidence

- `frontend/pnpm-workspace.yaml` now contains `allowBuilds: {unrs-resolver: true}` (previously `set this to true or false`).
- `pnpm install --frozen-lockfile` output: `.../node_modules/unrs-resolver postinstall: Done`, `Done in 9.2s` — no config warnings.
