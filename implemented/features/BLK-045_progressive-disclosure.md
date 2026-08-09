---
id: BLK-045
type: feature
title: "Progressive disclosure — 3-tier transparency for agent reasoning"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T22:35:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-028]
tags: [frontend, ux, transparency, progressive-disclosure, audit, heuristics]
---

## Description

Implement a 3-tier progressive disclosure system for agent reasoning
transparency, per the Agentic UX Audit Heuristics framework. Users get
the right level of detail based on their needs — from glanceable status
to full raw logs — without cognitive overload.

## Motivation

The UX audit framework states: if an application forces all users to
view raw execution logs by default, it violates the minimalist design
heuristic. Conversely, hiding all logic behind a conversational facade
with no drill-down violates transparency and erodes trust.

ADEP's 3-pane workbench already has some of this (Pane 1 shows the
trace), but it needs formal tiering.

## Tier Design

**Level 1 — Surface (default view):**
- Pane 1: Current cycle status badge (Planning/Acting/Observing/Reflecting)
- Pane 1: Field-completion progress bar (`4/7 Fields Extracted`)
- Pane 1: Latest thought as a one-line summary
- Pane 2: Confidence badges (green/yellow/red) on field cards
- Pane 3: Bbox highlights with color-coded confidence

**Level 2 — Expansion (click to expand):**
- Pane 1: Click a cycle → expand to show thought + tool call + tool result
- Pane 1: Tool call args in readable format (not raw JSON)
- Pane 1: Observation summary (not raw tool output)
- Pane 2: Click a field → show extraction provenance (which tool, which region, confidence score)
- Pane 3: Click a bbox → show tool that produced it + raw grounding coords

**Level 3 — Deep Dive (expert mode toggle):**
- Pane 1: Raw JSON payloads for tool calls and results
- Pane 1: Full trace log (all cycles, not just rolling window)
- Pane 1: Compaction summary (if compaction occurred)
- Pane 1: Attempted actions set (retry-loop prevention visibility)
- Pane 2: Raw extraction JSON (full, unfiltered)
- Pane 3: Normalized bbox coordinates (0-1000 scale) + page numbers

## Acceptance Criteria

- [ ] Level 1 is the default view — no user action needed
- [ ] Level 2: clicking a cycle card in Pane 1 expands to show tool call + result
- [ ] Level 2: clicking a field card in Pane 2 shows provenance (tool, region, confidence)
- [ ] Level 3: "Expert Mode" toggle in sidebar or pane header
- [ ] Level 3: shows raw JSON, full trace, attempted set, compaction summary
- [ ] Smooth expand/collapse animations (no jarring layout shifts)
- [ ] Level 2 expansion is per-cycle (not all-or-nothing)
- [ ] Expert mode persists across page reloads (localStorage)
- [ ] ADEP brand colors: Level 1 uses standard palette, Level 3 uses monospace/darker tones
- [ ] Both dark and light mode supported

## Constraints

- Level 1 must be glanceable — no more than 3 seconds to understand current status
- Level 3 must not load raw data until toggled (performance) [SF]
- Progressive disclosure is per-pane — each pane manages its own expansion state

## Dependencies

- BLK-028 (Pane 1 — Agent Console, where most disclosure happens)

## Notes

- Agentic UIUX Audit: §Implementing Progressive Disclosure
- Nielsen heuristic: "Visibility of system status" + "Aesthetic and minimalist design"
- Microsoft HAI Guideline: "Make clear how well the system understands the user"
