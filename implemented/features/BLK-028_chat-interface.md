---
id: BLK-028
type: feature
title: "Pane 1 — Agent Console (streaming reasoning trace)"
priority: high
status: backlog
phase: 3
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: L
depends-on: [BLK-027]
tags: [frontend, agent-console, pane-1, ui, core, streaming]
---

## Description

Build Pane 1 — the Agent Console. This is the primary consumption surface
in the 3-pane workbench (Devin/Windsurf-style). User selects an agent
definition from the sidebar, uploads a document, and watches the agent's
ReAct loop stream in real time with collapsible visual cards.

Streamed content per ReAct cycle:
1. **Thought** — LLM chain-of-thought text with subtle typing effect
2. **Action** — tool call pill/accordion: `🔧 crop(page=1, bbox=[100,200,400,300])`
3. **Observation** — structured tool result (OCR text + confidence, or
   inline thumbnail for crop results)
4. **Reflection** — gap report status bar: `4/7 Fields Extracted — 1 Invariant Failing`

This item absorbs BLK-032 (reasoning trace display) — the Agent Console
IS the reasoning trace, not a separate enhancement.

## Acceptance Criteria

- [ ] Definition selector in sidebar (lists available agent definitions)
- [ ] Document upload (drag-and-drop or file picker)
- [ ] SSE connection for real-time streaming (via `lib/sse.ts`)
- [ ] Thought cards: collapsible, subtle gray background, typing effect
- [ ] Tool call cards: tool name + args in a high-visibility pill/accordion
- [ ] Observation cards: structured result display
- [ ] Inline thumbnail preview for crop tool results (rendered in the card)
- [ ] Field-completion progress bar: `4/7 Fields Extracted`
- [ ] Gap report display if extraction is partial
- [ ] Auto-scroll to latest cycle
- [ ] Independent vertical scrollbar (overflow-y-auto, does not scroll the page)
- [ ] Sticky header (Compact button + progress bar stay visible while scrolling)
- [ ] Cycle counter + collapsible per-cycle grouping
- [ ] Compact button in header (triggers /compaction via SSE) [§12.4]
- [ ] "Compacting..." spinner when compaction is in progress
- [ ] "Context compacted" notification on `compaction` SSE event
- [ ] Loading states and error handling

## Dependencies

- BLK-027 (API client)

## Notes

- vision.md §0.2 (Pane 1 — Agent Console), §7.2 criteria 12-13
- Absorbs BLK-032 (reasoning trace display is the core of Pane 1, not a separate enhancement)
