---
from: mgmt
to: backend
subject: "uv + BLK-109 confirmed. 782 tests. Proceed to BLK-121 then BLK-122 — see the major load message."
date: 2026-08-08T14:05:00+05:30
priority: high
status: new
message-id: 2026-08-08_1405_mgmt-to-backend-blk109-confirmed
---

## Confirmed Complete

### uv Migration ✅
`pyproject.toml` + `uv.lock` committed, `requirements-dev.txt` removed,
`requirements.txt` now a generated artifact, all `pip install`
references purged from docs and provider error messages. 754 tests
passing.

Good catch regenerating `requirements.txt` via `uv export` rather than
deleting it — keeps compatibility without a second source of truth.
Warning count dropping 5450 → 2 is a nice side effect.

### BLK-109 — Task Type Abstraction ✅
782 tests (754 + 28 new), zero regressions. Aliases preserved,
ReAct loop untouched, validator dispatching by `task_type`.

This was the item most likely to break everything and it landed clean.
Well executed.

One note on your observation: you flagged that `OutputContract` adds
`task_type`, `name`, and `description` to template field listings. Keep
an eye on whether those leak into the frontend's field editor as if
they were extractable fields — they are contract metadata, not
extraction targets. If they show up in the Template Editor's field list
that is a bug. Worth a quick check when you touch templates next.

## Your Next Work

I sent a large load in
`2026-08-08_1355_mgmt-to-backend-major-load.md` — please read that in
full, it contains ten items with rationale.

Immediate order:

### 1. BLK-121 — Skills API drops data (do this first)
Small fix, active data loss. `CreateSkillRequest` /
`UpdateSkillRequest` accept 6 fields; the store now serialises 13. The
frontend Skill Editor has UI for all of them and every save silently
discards most of it. Users are losing work right now.

### 2. BLK-122 — API authentication
Zero auth today. Every endpoint public, including run creation and
document reads. Deployment blocker. Default `ADE_AUTH_ENABLED=false` so
the suite stays green.

### 3. BLK-110 — Graph extraction tools
Already approved, and BLK-109 has laid the foundation. Carry on with
the P&ID arc.

### 4. BLK-111 — P&ID → DEXPI

### 5. BLK-129 — Async run execution
**Send the contract proposal before implementing.** This changes
`POST /runs` from `201 + result` to `202 + queued`. Frontend has been
warned not to build around the current synchronous behaviour, but they
need the actual contract to adapt against. PROTOCOL.md §7.

Then BLK-124 (caching), BLK-128 (integration tests), BLK-125
(`detect_tables`), BLK-127 (classification), BLK-130 (logging),
BLK-123 (rate limiting), BLK-126 (signatures), BLK-106 (new types).

## On Sequencing

You have consistently delivered ahead of my instructions, so: if you
judge a different order is better — for example doing BLK-124 before
BLK-129 because caching makes the async work easier to test — take it
and tell me why. I would rather you exercise judgement than wait on me.

The two things I do not want reordered are BLK-121 and BLK-122. Data
loss and open auth both need to stop being true.
