---
id: BLK-069
type: feature
title: "Agent Composer — generate full definition from natural language"
priority: high
status: backlog
phase: 5
owner: unassigned
created: 2026-08-08T00:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-031, BLK-067, BLK-068]
tags: [ai, adas, agent-composer, natural-language, definition-builder, research]
---

## Description

A meta-agent that takes a natural language request and produces a
complete Agent Definition by calling the Template Composer (BLK-067),
Skill Composer (BLK-068), and Agent Composer, then binding them into
an executable ReAct graph.

## Motivation

From `agentic agent builder.md`: the Agent Composer is the final
assembly phase, stitching generated templates, skills, and atomic tools
into an executable runtime loop. This is the capstone ADAS feature.

## Design

**Input:**
- Natural language request:
  > "Build an agent that extracts vendor, invoice number, line items,
  > tax, and total from PDF invoices, with high precision and math
  > cross-checks."

**Pipeline:**
1. Agent Composer parses intent
2. Calls Template Composer → generates Template
3. Calls Skill Composer → generates Skill for that Template
4. Selects tool set (OCR, VLM, crop, cross_check, etc.)
5. Generates system prompt override
6. Sets max iterations
7. Produces Agent Definition preview

**Output:**
- Complete `AgentDefinition` (name, skill, template, tools, prompt,
  max iterations)
- All components open in editor for review

**UI:**
- New "Build Agent from Description" wizard at `/build`
- Textarea for description
- Step-by-step preview: generated template → skill → tools → review
- User can edit any component before saving

## Acceptance Criteria

- [ ] `POST /api/v1/definitions/generate` accepts NL request and
      returns generated definition
- [ ] Wizard UI at `/build`
- [ ] Generated definition preview with editable components
- [ ] Generated components saved to Definition Store
- [ ] Generated definition can run immediately after save
- [ ] Test: one NL request → complete invoice definition generated

## Constraints

- v1: human review required before saving
- Generated components are not deployed automatically
- Requires BLK-067 and BLK-068 first

## Dependencies

- BLK-031 (Definition Builder)
- BLK-067 (AI Template Composer)
- BLK-068 (AI Skill Composer)

## Notes

- `agentic agent builder.md`: Agent Composer binds primitives into
  LangGraph ReAct runtime
- OneFlow optimization (BLK-074) may be applied later
