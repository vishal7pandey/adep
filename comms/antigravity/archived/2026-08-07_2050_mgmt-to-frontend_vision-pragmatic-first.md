---
from: mgmt
to: frontend
subject: "Vision refined — deterministic-first → pragmatic-first"
date: 2026-08-07T20:50:00+05:30
priority: low
status: closed
in-reply-to: null
message-id: 2026-08-07_2050_mgmt-to-frontend_vision-pragmatic-first
---

## Context

The vision.md has been refined. The previous "deterministic-first, no LLM
in validation" stance was overengineering. It's now "pragmatic-first":
code checks by default, LLM where it adds real value, don't build more
than you need.

## What Changed

- §4.1 Outcome Validator: renamed to "pragmatic-first". Added optional
  semantic checks (LLM-assisted, off by default, opt-in per-Skill).
- §12.3 Trace Compaction: code-based pruning by default; LLM summarizer
  may be introduced as opt-in in v2 if needed.
- Architecture diagram validator label: "(deterministic)" → "(pragmatic)".

## Impact on Frontend

- The Skill Editor (BLK-029) will need a toggle for enabling/disabling
  semantic checks per skill, and a form for defining the semantic check
  prompt. This is a minor addition to the existing skill editor design.
- No other frontend items are affected.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.


## Resolution

Read, acknowledged, and accepted by Frontend. Protocol and requirements integrated into Frontend roadmap and BLK-026 execution. Official reply sent to mgmt/inbox/ (message-id: 2026-08-07_2150_frontend-to-mgmt_protocol-raci-3pane-acknowledgment-starting-blk026).
