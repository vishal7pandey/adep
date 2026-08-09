---
id: BLK-039
type: feature
title: "Context Compaction — /compaction action (auto + manual)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T22:00:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-008]
tags: [agent, compaction, context, llm, graph, core]
---

## Description

Implement active context compaction for the ReAct agent — the ability to
summarize the trace into a compact narrative, just like Claude Code,
Windsurf, or Devin do when their context window fills up.

Two trigger modes:

1. **Auto-compaction (threshold-based).** After the `reflect` node, if the
   trace length exceeds `ADE_COMPACTION_THRESHOLD` (default: 15 entries),
   the graph routes to a `compact` node instead of back to `plan`. The
   compact node uses the LLM to summarize the trace into a structured
   `compaction_summary` string, then routes to `plan` with the summary
   replacing the raw trace in the LLM prompt.

2. **Manual compaction (`/compaction` action).** The frontend Agent Console
   (Pane 1) has a "Compact" button. Clicking it sends a `compact` event
   via SSE to the backend, setting `_compact_requested=True` in State. On
   the next `reflect → plan` transition, the graph routes to `compact`
   regardless of trace length.

Graph flow with compaction:
```
plan → act → observe → reflect → (plan | compact | terminate)
                                    compact → plan
```

## Acceptance Criteria

- [x] `compact_node` function in `graph.py` that uses LLM to summarize trace
- [x] `_code_based_summary` fallback when no LLM available or LLM fails
- [x] `compaction_summary` field in `AgentState` (string, default "")
- [x] `_compact_requested` flag in `AgentState` (bool, default False)
- [x] `should_continue` conditional edge routes to `compact` when:
  - `_compact_requested == True`, OR
  - `len(trace) >= settings.compaction_threshold`
- [x] `compact` node wired into graph: `compact → plan` edge
- [x] `plan_node` includes `compaction_summary` in LLM prompt when present
- [x] `compaction_enabled` and `compaction_threshold` in `config.py` Settings
- [x] `ADE_COMPACTION_ENABLED` and `ADE_COMPACTION_THRESHOLD` in `.env.example`
- [ ] SSE endpoint accepts `compact` event from frontend, sets `_compact_requested=True`
- [ ] Unit test: auto-compaction triggers at threshold
- [ ] Unit test: manual compaction via `_compact_requested` flag
- [ ] Unit test: compaction preserves `attempted` set and `gap_report`
- [ ] Unit test: `compaction_summary` appears in plan node prompt after compaction
- [ ] Unit test: code-based fallback summary works without LLM
- [ ] Integration test: long-running extraction triggers auto-compaction

## Constraints

- Compaction is opt-in via `ADE_COMPACTION_ENABLED=true` (default: true)
- The `attempted` set is NEVER compacted — retry-loop prevention is
  non-negotiable [§12.3]
- The full trace persists in the LangGraph checkpoint — compaction only
  affects what's in the active LLM prompt
- `compaction_summary` is a single string field, not a complex data
  structure [SF]
- Manual compaction resets the trace window but does not reset extraction
  state, gaps, or attempted set

## Dependencies

- BLK-008 (ReAct graph implementation — compact node is a new node in the graph)

## Notes

- vision.md §12.4 (Context Compaction)
- The compact node uses the same LLM client as the plan node (GPT-5.4)
- Frontend "Compact" button in Pane 1 (BLK-028) sends SSE event to backend
- Backend SSE endpoint (BLK-023) needs to accept `compact` event type
