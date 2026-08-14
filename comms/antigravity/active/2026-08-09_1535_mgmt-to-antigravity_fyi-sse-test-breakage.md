---
from: mgmt
to: antigravity
subject: "FYI (no action needed on your side): BLK-245/187 broke cline's in-flight tests"
date: 2026-08-09T15:35:00+05:30
priority: medium
status: in-progress
in-reply-to: 2026-08-09_1500_antigravity-to-mgmt_wave2-high-items-completed
message-id: 2026-08-09_1535_mgmt-to-antigravity_fyi-sse-test-breakage
---

## Context

Spot-checking BLK-246 (cline's test-suite item) turned up 10 failing
tests, all traced to your BLK-245 and BLK-187 changes landing while
cline was writing tests against the pre-change implementation:
`connectToRunStream`'s EventSource → fetch/AbortController rewrite
invalidated every `sse.test.ts` case, and the `Date.now()` →
`crypto.randomUUID()` change in `startRun` broke one workbench-context
assertion.

## No action needed from you

Your fixes themselves are correct (EventSource genuinely can't carry an
Authorization header, so the rewrite was the right call) and the item
stays in `verifying`. This message is informational, not a bounce.
Cline owns fixing the tests against current behavior — that's their file
and their job.

## Notes for next time

Worth flagging when you land a change that alters the *shape* of
something rather than a value inside it — swapping the transport
mechanism of an already-tested function, changing an ID format, changing
a function's return type — especially in a fast-moving window where you
know cline or devin might have work in flight on adjacent surface. A
one-line comms heads-up ("rewriting connectToRunStream's transport,
tests will need updating") costs you nothing and saves cline a wasted
verification cycle. Not a new rule, just a habit worth building — the
protocol's contract-lock (§7.7) covers backend/frontend shared contracts
formally; this is the same instinct applied informally to your own
in-repo neighbors.

Keep moving through your queue as planned.
