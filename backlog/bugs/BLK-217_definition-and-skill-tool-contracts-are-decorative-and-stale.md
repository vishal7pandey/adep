---
id: BLK-217
type: bug
title: "Definition and skill tool contracts are decorative and can drift from the live registry"
priority: high
status: backlog
phase: 1
owner: devin
created: 2026-08-09T11:05:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [agent, tools, definitions, skills, wiring, planner, backend]
---

## Description

The product model exposes multiple layers of tool configuration:

- `AgentDefinition.tool_names`
- skill-level `tools` metadata in the API/store
- skill-level `tool_preferences`

But the live run path ignores the first two entirely and only uses `tool_preferences` as weak prompt text. The planner still sees the full global registry, and `act_node()` will execute any registered tool the LLM names.

## Problem Statement

The current wiring has three failures:

- `src/api/run_engine.py` always calls `build_tool_registry()` with no filtering from `definition.tool_names`
- `src/agent/graph.py` advertises every `registry.specs()` entry to the planner and executes every `registry.call()` target with no definition- or skill-level allowlist
- dynamically loaded skills do not even materialize the stored `tools` list into the `Skill` object, so that metadata is inert in the live path

There is also verified metadata drift between what definitions claim and what the registry can actually provide. As of August 9, 2026, comparing `PREBUILT_DEFINITIONS[*].tool_names` to `build_tool_registry().names()` shows these claimed tools are missing from the live registry:

- `crop_image`
- `cross_check`
- `detect_figures`
- `locate`

This makes the agent contract misleading in two ways:

- the UI/store suggest per-definition tool composition exists when it does not
- definitions can advertise tools that no execution path can ever invoke successfully

## Acceptance Criteria

- [ ] The live registry is filtered or validated against `AgentDefinition.tool_names`
- [ ] Skill-level tool metadata has a real execution role or is removed from the contract
- [ ] Planner prompts only advertise tools the current run is actually allowed to call
- [ ] Definitions with nonexistent tools fail validation at create/update time or are auto-normalized explicitly
- [ ] Integration tests prove that disallowed tools cannot be planned or executed for a given definition
- [ ] Prebuilt definitions are reconciled with actual registry names

## Constraints

- Preserve backward compatibility for older definitions where practical
- Avoid silently dropping requested tools without surfacing validation errors
- If allowlisting is introduced, make sure graph-extraction definitions still receive their specialized tool set

## Dependencies

- `src/definitions/base.py`
- `src/api/routes/definitions.py`
- `src/api/routes/skills.py`
- `src/api/run_engine.py`
- `src/agent/graph.py`
- `src/run.py`

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
