---
id: BLK-189
type: tech-debt
title: "detect_tables tool does not exist despite 4 skills declaring a preference for it"
priority: medium
status: backlog
phase: 5
owner: devin
created: 2026-08-09T11:00:00+05:30
started: null
completed: null
estimate: M
depends-on: []
tags: [backend, tools, skills, consistency, gap]
---

## Description

BLK-125 documented this issue and it was marked complete, but an independent re-audit confirms `detect_tables` tool is **still not implemented** in `src/tools/`. At least 4 skills declare a `tool_preferences` entry for it:

- `src/skills/invoice.py`
- `src/skills/pay_stub.py`
- `src/skills/bank_statement.py`
- `src/skills/medical_claim.py`

The agent will attempt to call a `detect_tables` tool that doesn't exist in the registry, causing a tool-not-found error mid-run and consuming cycle budget on a dead probe.

There is a `src/tools/table_detection.py` import path, but it doesn't appear to be registered as the `detect_tables` tool name in the runtime registry. This is a latent runtime failure.

## Acceptance Criteria

- [ ] Independently verify `detect_tables` tool registration in the runtime ToolRegistry
- [ ] Either implement `detect_tables` or remove its appearance from all 4 skills' `tool_preferences`
- [ ] Add a test that verifies every tool referenced by any prebuilt skill exists in the registry
- [ ] No skill should reference a tool that doesn't exist

## Constraints

- Must be backward-compatible with stored skills/configs
- If the tool is added, it should be cacheable via BLK-124

## Dependencies

- Registration test should be part of the existing registry test suite

## Notes

- This was first filed as BLK-125 (marked complete) but the re-audit finds the tool still missing
- Related to BLK-144 (config-driven OCR provider selection) and BLK-173 (provider config validation)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.
