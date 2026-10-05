# ADE-4 — Test plan: make the AGENTS.md commands true

Status: plan-approved · Risk: low · Jira: ADE-4

Test framework and conventions found: documentation change; the check is running the commands.

| AC | Level | Test (name/path) | Happy | Boundary | Negative | Status |
|----|-------|------------------|-------|----------|----------|--------|
| AC1 | manual | run every command of the AGENTS.md Commands block, then the CI frontend job on the PR | each command runs or fails exactly as documented | stale node_modules needs CI=true (documented) | pnpm 11.13.0 pin refused before the fix (observed) | verified |

## Regression risk

Frontend CI job uses `corepack enable` and the new pin.

## Untestable AC

None.

## Manual checks

Steps and outputs are in spec.md (Repro).

## Audit (after implementation)

Before: `pnpm install` aborted with "pnpm v11.13.0 is a broken release". After: install, test (104 passed) and build succeed.
