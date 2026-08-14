---
from: mgmt
to: backend
subject: "Vision refined — deterministic-first → pragmatic-first"
date: 2026-08-07T20:50:00+05:30
priority: medium
status: new
in-reply-to: null
message-id: 2026-08-07_2050_mgmt-to-backend_vision-pragmatic-first
---

## Context

The vision.md has been refined. The previous "deterministic-first, no LLM
in validation" stance was overengineering — it was dogmatic about excluding
the LLM from validation when the real principle should be: use code where
it's cheap and reliable, use the LLM where it adds real value, don't build
more than you need [SF].

## What Changed

1. **§2.2 Reflect node**: "deterministic-first" → "pragmatic-first". Code
   checks by default; LLM may be consulted for semantic/contextual checks
   that code can't handle, with structured prompts.

2. **§4.1 Outcome Validator**: Renamed from "deterministic-first" to
   "pragmatic-first". Added check #6: optional semantic checks (LLM-assisted,
   structured prompts, off by default, opt-in per-Skill). The principle is
   now: "code first, LLM second, vibes never."

3. **§4 Architecture diagram**: Validator label changed from
   "(deterministic)" to "(pragmatic)".

4. **§12.3 Trace Compaction**: Softened from "deliberately avoided LLM
   summarizer" to "code-based pruning by default; LLM summarizer may be
   introduced as opt-in in v2 if the problem is real."

5. **BLK-009**: Title, description, acceptance criteria, and constraints
   updated to match. Added SEMANTIC_FAIL to GapType enum. Added optional
   semantic check hook to acceptance criteria.

## Action Required

- Read the updated §4.1 in `vision.md`.
- Note the change in BLK-009 acceptance criteria.
- No other backlog items are affected.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
