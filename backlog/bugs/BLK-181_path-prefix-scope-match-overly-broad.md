---
id: BLK-181
type: bug
title: "Auth scope matching uses startswith — broad prefix can match unintended routes"
priority: medium
status: backlog
phase: 5
owner: devin
created: 2026-08-09T10:20:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [security, auth, api, middleware]
---

## Description

In `src/api/auth.py`, `_required_scope()` matches routes by `path.startswith(prefix)`. This is overly broad: any route whose path *starts with* the configured prefix gets that prefix's scope, even if it's a different route.

For example, `GET /api/v1/runs-evil` or `GET /api/v1/runs/extra/path` would match the `("GET", "/api/v1/runs", SCOPE_RUNS_READ)` tuple because it starts with `/api/v1/runs`.

This is a security hardening issue: a route that should be public or belong to a different scope may inadvertently be protected by (or worse, granted) the wrong scope. Currently only the routes mounted in `main.py` exist, but as new endpoints are added under sibling prefixes (e.g. `/api/v1/rumors`), they could silently inherit a wrong scope requirement.

Conversely, a new route `/api/v1/runs/public` would be assigned `runs:read` scope rather than being public or having its own scope.

## Acceptance Criteria

- [ ] Replace `startswith` with exact path-segment matching (split by `/`, compare segment-by-segment)
- [ ] Add test covering: sibling prefix, nested path, exact match
- [ ] Verify all existing routes in the app still resolve to the correct scope

## Constraints

- Must not break authentication for existing client code
- Path matching should be O(k) per route entry, not O(n^2) over all segments

## Dependencies

- None

## Notes

- Found during auth middleware audit
- Related to BLK-122 (Auth) and BLK-153 (Auth disabled by default)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
