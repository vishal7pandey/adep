---
id: BLK-284
type: bug
title: "Definition-level agent overrides are only partially applied to the live run"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T11:25:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [agent, definitions, config, planner, validator, runtime]
---

## Description

`AgentDefinition` exposes multiple runtime override controls that imply a composed, definition-specific agent:

- `system_prompt`
- `agent_config.max_cycles_per_field`
- `agent_config.max_cycles_per_document`
- `agent_config.confidence_threshold`

In the live run path, only `max_cycles_per_document` is meaningfully applied. The rest are stored, editable, and returned through the API, but do not reliably alter planner or validator behavior.

## Problem Statement

Verified live-path behavior:

- `src/api/run_engine.py` reads `agent_config.max_cycles_per_document` and uses it for recursion limit
- `src/agent/graph.py` always uses `skill.system_prompt` in `plan_node()`
- `src/agent/graph.py:_check_caps()` always uses global `settings.max_cycles_per_field`
- progress/resolution checks in `observe_node()` and trace compaction still compare against global `settings.default_confidence_threshold`
- `build_validator_config()` only uses global settings plus `skill.confidence_overrides`, not `definition.agent_config.confidence_threshold`

This means a definition can claim a custom prompt or custom runtime tuning while the running agent still behaves like the base skill plus global settings.

That is a real orchestration bug because the definition model is the primary unit users compose in the UI, but the live planner/validator does not fully honor it.

## Acceptance Criteria

- [ ] `definition.system_prompt` is either merged into the active skill prompt intentionally or removed from the definition contract
- [ ] `agent_config.max_cycles_per_field` affects the live cap logic
- [ ] `agent_config.confidence_threshold` affects validation/progress logic consistently
- [ ] One canonical runtime config object is passed into graph nodes instead of ad hoc reads from global settings
- [ ] Tests prove a definition-level override changes actual planner/validator behavior

## Constraints

- Preserve existing built-in skill prompts unless a definition explicitly overrides them
- Avoid conflicting threshold logic between global settings, skill overrides, and definition overrides; define precedence clearly
- Keep the runtime config serializable and visible for debugging

## Dependencies

- `src/definitions/base.py`
- `src/api/routes/definitions.py`
- `src/api/run_engine.py`
- `src/run.py`
- `src/agent/graph.py`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
