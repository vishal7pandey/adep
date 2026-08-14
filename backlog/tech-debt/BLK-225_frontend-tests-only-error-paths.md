---
id: BLK-225
type: tech-debt
title: "Frontend test file tests only error paths — 8 tests, all asserting 'throws when server unreachable', zero functional tests"
priority: medium
status: backlog
phase: 2
owner: antigravity
created: 2026-08-09T13:45:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [frontend, testing, quality, false-confidence]
---

## Description

The sole frontend test file (`frontend/tests/frontend/api.test.ts`, 36 lines) contains 8 tests. Every single test follows the same pattern:

```typescript
test('fetchDefinitions throws ApiError when server is unreachable', async () => {
    await expect(fetchDefinitions()).rejects.toThrow(ApiError);
});

test('fetchSkills throws ApiError when server is unreachable', async () => {
    await expect(fetchSkills()).rejects.toThrow(ApiError);
});

// ... 6 more identical tests for fetchTemplates, pauseRun, resumeRun, stopRun, rollbackRun, compactRun
```

All 8 tests assert that API functions throw `ApiError` when the server is unreachable. No test verifies:
- Correct request construction (URL, method, headers, body)
- Response parsing (JSON → typed objects)
- Auth header propagation
- Status code handling (202, 404, 429, etc.)
- SSE event parsing
- Analytics metric computation
- Component rendering

## Problem Statement

- 8 tests that all verify the same thing (network error → ApiError) provide false confidence — "we have tests!" but they test nothing meaningful
- The tests don't even mock `fetch` — they rely on the server being unreachable, which means they pass in any environment without a backend but would also pass if the API client is completely broken (as long as it throws)
- No test runner is configured in `package.json` — these tests can only be run manually with a test runner
- CI doesn't run frontend tests at all

## Acceptance Criteria

- [ ] Add a proper test runner (Vitest or Jest) to `package.json` with a `test` script
- [ ] Mock `fetch` in tests and verify request construction (URL, method, headers, body)
- [ ] Add tests for successful response parsing (mock responses → typed objects)
- [ ] Add tests for specific error status codes (404, 429, 503)
- [ ] Add tests for auth header propagation
- [ ] Add tests for SSE client (connection, event parsing, reconnection)
- [ ] Add tests for analytics metric computation
- [ ] Add frontend test step to CI

## Constraints

- Use Vitest (compatible with Next.js ecosystem) or Jest with Next.js plugin
- Mock `global.fetch` for API tests
- Don't rely on server being unreachable — use deterministic mocks

## Dependencies

- `frontend/tests/frontend/api.test.ts`
- `frontend/package.json` (add test runner)
- `.github/workflows/ci.yml` (add frontend test step)
- Related to BLK-218 (frontend near-zero test coverage)

## Notes

- Found during full-repo audit; the existing tests are technically not wrong but they provide almost zero value — they're the testing equivalent of a stub

## Implementation Log

- **2026-08-09T16:00 (mgmt)**: Reassigned from `cline` (mandate suspended, see projectmgmt/STATUS.md 2026-08-09 16:00 note) to `antigravity`. Test-code ownership for this file's domain reverts to the implementing team; independent verification now happens via cross-team review (devin<->antigravity) instead of a dedicated gate.

- **2026-08-09 (mgmt)**: Assigned to `cline` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
