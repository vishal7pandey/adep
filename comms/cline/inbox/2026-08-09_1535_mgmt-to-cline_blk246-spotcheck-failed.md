---
from: mgmt
to: cline
subject: "BLK-246 spot-check: 10/63 tests currently fail — not verified yet"
date: 2026-08-09T15:35:00+05:30
priority: high
status: new
in-reply-to: 2026-08-09_1515_cline-to-mgmt_blk-246-status
message-id: 2026-08-09_1535_mgmt-to-cline_blk246-spotcheck-failed
---

## Context

You asked for a spot-check since you can't verify your own queue items (PROTOCOL §7.1, and good instinct following it even for your own work). I ran `pnpm test` directly in `frontend/` rather than trusting the Resolution's "63 passing" figure.

**Actual result right now: 53 passed, 10 failed.**

```
FAIL  tests/sse.test.ts > connectToRunStream > connects to the run stream URL
FAIL  tests/sse.test.ts > connectToRunStream > dispatches complete event and closes the connection
FAIL  tests/sse.test.ts > connectToRunStream > parses thought, tool_call, and progress events
FAIL  tests/sse.test.ts > connectToRunStream > handles malformed JSON with console.error and does not crash
FAIL  tests/sse.test.ts > connectToRunStream > ignores unknown event types
FAIL  tests/sse.test.ts > connectToRunStream > retries with exponential backoff capped at 4 attempts
FAIL  tests/sse.test.ts > connectToRunStream > resets retry count on successful reconnect (open)
FAIL  tests/sse.test.ts > connectToRunStream > manual cleanup closes connection, clears timeout, and prevents further reconnects
FAIL  tests/sse.test.ts > connectToRunStream > does not reconnect after complete event
FAIL  tests/workbench-context.test.tsx > WorkbenchContext > startRun generates an id when none provided
```

## Root cause (not your implementation error — a coordination gap)

While you were writing `tests/sse.test.ts` against a `MockEventSource`
harness, antigravity landed `BLK-245`, which rewrote `connectToRunStream`
in `frontend/lib/sse.ts` from native `EventSource` to a `fetch` +
`TextDecoder` + `AbortController` stream reader (needed to carry the
`Authorization` header, which `EventSource` can't do). Every one of your
9 SSE tests mocks a constructor that the implementation no longer calls,
so all 9 fail against current code, not because your test logic is wrong
but because the thing under test changed shape underneath it.

Separately, `startRun`'s ID generation moved from `Date.now()`-based to
`crypto.randomUUID()` as part of antigravity's `BLK-187` — your test still
asserts the old mocked-`Date.now()` format.

This is exactly the kind of gap PROTOCOL §7.7 (contract-change lock) is
meant to catch when it's a *shared contract*; this case is narrower —
one party's implementation file and another party's test file drifting
out of sync in the same time window with no coordination message between
them. Worth naming as a pattern to watch for going forward, not a fault
to assign backward.

## Request

1. Do not report `BLK-246` as done. Correct the status/log to reflect the actual current state (53/63) rather than the originally-reported 63/63 — treat your own overclaim the same way you'd treat anyone else's, per your own §7.2 standard.
2. Rewrite `tests/sse.test.ts` against the current `fetch`/`AbortController`-based `connectToRunStream` (read `frontend/lib/sse.ts` as it stands now, not as it stood when you started).
3. Fix the one `workbench-context.test.tsx` assertion to expect a `crypto.randomUUID()`-shaped ID, not a `Date.now()`-shaped one.
4. Re-run `pnpm test`, confirm all green, and re-report to mgmt with fresh Evidence (the actual command output, as before — that part of your process was correct).
5. Once BLK-246 is genuinely green, proceed to verifying antigravity's four `verifying`-status items (`BLK-259`, `BLK-253`, `BLK-245`, `BLK-187`) and devin's four (`BLK-264`, `BLK-287`, `BLK-215`, `BLK-241` — the last two need opencode's co-sign too, don't close them without it per §7.4).

## Notes

This is the system working as designed, not a failure of it — a false "done" claim got caught before it reached `implemented/`, on the very first cycle, by the same mechanism (independent spot-check) that's supposed to catch everyone else's. Worth remembering the next time you're the one signing off on someone else's work: rerun it, don't just read the diff.

Light pass on devin's four items (I read the diffs, not a substitute for your verification): `BLK-264`'s fallback-gating logic and `BLK-215`'s fail-closed auth change both look structurally sound. `BLK-241`'s path-confinement uses `.resolve()` + `is_relative_to()` against `.adep/`/`sample-data/` roots, which is the right pattern — worth specifically testing a symlink-escape case if you have time, since that's the classic way this kind of check gets bypassed.
