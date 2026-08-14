---
id: BLK-184
type: bug
title: "Frontend tests make real network calls — flaky, slow, and non-deterministic"
priority: high
status: backlog
phase: 5
owner: antigravity
created: 2026-08-09T10:35:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [frontend, testing, quality, devx]
---

## Description

`frontend/tests/frontend/api.test.ts` contains tests that call the **real** API client functions (`fetchDefinitions()`, `fetchSkills()`, etc.). Since `fetch` in Node targets the actual network, these tests will:

- Fail when no backend is running (connection refused)
- Hang or timeout if the network is slow
- Return success when a dev server happens to be running (making the test non-deterministic)
- Provide **zero** assertion value: the test only checks that it throws `ApiError`, which is the wrong behavior — a well-mocked test would verify the client sends the right URL, headers, and parses responses correctly.

This is not how API client tests should be written. The suite cannot be run in CI (no backend), so it either fails CI or is skipped, both of which are broken.

## Root Cause

The tests were written as smoke tests that assume a reachable server. They were never wired to a mock strategy (e.g. `jest.mock('node-fetch')`, `vi.stubGlobal('fetch', mock)`).

## Files Affected

- `frontend/tests/frontend/api.test.ts`

## Acceptance Criteria

- [ ] Rewrite tests to mock `fetch` (e.g. with `jest` or `vi`) returning canned responses
- [ ] Verify the client sends correct URL, method, headers
- [ ] Verify it parses response bodies into typed objects
- [ ] Verify error paths (non-2xx, network failure, malformed JSON)
- [ ] Add a test runner script and `test` script to `frontend/package.json`
- [ ] Document how to run frontend tests in `frontend/README.md`

## Constraints

- Must not depend on a live backend
- Must be runnable in CI without network access

## Dependencies

- None

## Notes

- Found during frontend test audit
- `frontend/package.json` currently has **no test script** — there is no standard way to run these tests

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `antigravity`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
