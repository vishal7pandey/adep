---
id: BLK-243
type: bug
title: "Attempted-set retry dedup is disabled for page-level tools — region_id default mismatch ('' vs '_global')"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T12:15:00+05:30
started: null
completed: null
estimate: S
depends-on: []
tags: [backend, agent, retry-dedup, loop-detection, tokens, reliability]
---

## Description

The "already attempted (do not retry)" set is meant to prevent the LLM from reissuing the same failed tool call (agent graph, BLK-049 / §12.3). Two nodes disagree on the key used to store/read attempts.

- `plan_node` (graph.py ~line 264): `region_id = action.args.get("region_id", "")` then checks `attempted[region_id]` (defaulting to empty string).
- `observe_node` (graph.py ~line 405): records failures under `region_id = tool_args.get("region_id", "_global")`.

So when the LLM omits `region_id` (the common case for page-level tools that target no region), `plan_node` looks up `attempted[""]` while `observe_node` wrote the failure under `attempted["_global"]`. The lookup misses, and the LLM's next identical reissued call is treated as a fresh attempt — burning up to N cycles/tokens on tools that already failed.

## Problem Statement

The "do not retry" guard, which is a core part of the project's trajectory-integrity and token-saving narrative (BLK-049, BLK-082 style protections), is effectively disabled for any tool call without an explicit `region_id`. Since `region_id` is primarily emitted for crops/regions extracted by other tools, most page-level leaf tools (OCR, read_page, etc.) are affected. Symptoms: higher token consumption, repeated identical failures, longer runs, and faster progress toward `max_cycles_per_document`.

## Acceptance Criteria

- [ ] `plan_node` and `observe_node` use a single canonical "no region" key (recommended: `"_global"`), so a call omitted → `"_global"` in both
- [ ] A unit test replays the exact scenario: tool fails without `region_id`, plan_node receives the same `tool+args` again, and it is skipped as already-attempted
- [ ] No regression on regioned calls (region_id present → per-region buckets unchanged)
- [ ] Optionally surface in the trace whether a skipped attempt was logged

## Constraints

- Do not change the semantics of `attempted` for region-scoped work
- Preserve backward compatibility during graph state transitions (state serialized with old keys should still skip correctly or be normalized on load)

## Dependencies

- `src/agent/graph.py` (`plan_node`, `observe_node`)
- `src/agent/state.py` (`attempted` schema, §12.3)

## Notes

- Discovered while reading the attempt-set handling in graph.py; retry-loop prevention is silently disabled for the common `region_id`-less path.

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T12:15 (mgmt)**: Filed — key mismatch between `plan_node` (defaults to `""`) and `observe_node` (defaults to `"_global"`).
