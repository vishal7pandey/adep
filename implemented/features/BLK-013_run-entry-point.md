---
id: BLK-013
type: feature
title: "run() entry point — run(template, skill, document) -> ExtractedResult"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-008, BLK-011, BLK-012]
tags: [run, entry-point, v1-slice]
---

## Description

Implement the `run()` function that composes a Template, Skill, and Document
into an extraction run. Instantiates the ReAct agent with the skill's prompt
and tool set, hands it the document and template, and lets it loop to
completion. Returns ExtractedResult with filled schema, grounding,
confidence, and trace.

## Acceptance Criteria

- [ ] `src/run.py` with run(template, skill, document) -> ExtractedResult
- [ ] Builds ValidatorConfig from skill + settings
- [ ] Builds initial AgentState with document handle
- [ ] Builds ToolRegistry with config-driven providers
- [ ] Invokes LangGraph graph to completion
- [ ] Returns ExtractedResult with is_complete, values, gap_report, trace
- [ ] Integration test with mocked LLM + mocked tools on invoice.png

## Dependencies

- BLK-008 (ReAct graph)
- BLK-011 (InvoiceSkill)
- BLK-012 (InvoiceTemplate)

## Notes

- vision.md §3.5 (Run Instance), §10 Phase 1 step 5
- Existing `src/run.py` has a skeleton — complete it
