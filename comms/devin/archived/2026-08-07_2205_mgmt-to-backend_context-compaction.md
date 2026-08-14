---
from: mgmt
to: backend
subject: "New feature: Context Compaction (/compaction action) — §12.4, BLK-039"
date: 2026-08-07T22:05:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_2205_mgmt-to-backend_context-compaction
---

## Context

A new feature has been designed and partially implemented: **Context
Compaction** — the agent's ability to actively summarize its trace into a
compact narrative, just like Claude Code, Windsurf, or Devin do when
their context window fills up.

This is documented in vision.md §12.4 and tracked as BLK-039.

## What's Been Implemented

The following changes have already been made to the codebase:

### 1. `config.py` — New settings
- `compaction_enabled: bool = True` (env: `ADE_COMPACTION_ENABLED`)
- `compaction_threshold: int = 15` (env: `ADE_COMPACTION_THRESHOLD`)

### 2. `state.py` — New AgentState fields
- `compaction_summary: str` — LLM-generated narrative summary, replaces
  raw trace in plan node prompt after compaction. Empty string until
  first compaction.
- `_compact_requested: bool` — Flag set by manual /compaction action
  from frontend. When true, next reflect→plan transition routes to
  compact regardless of trace length.

### 3. `graph.py` — New `compact_node` + graph wiring
- `compact_node(state, llm_client)` — Uses LLM to summarize trace into
  `compaction_summary`. Falls back to `_code_based_summary()` (simple
  concatenation, capped at 20 lines) when no LLM available or LLM fails.
- `should_continue()` updated — now returns `"compact"` when:
  - `_compact_requested == True`, OR
  - `len(trace) >= settings.compaction_threshold`
- Graph flow updated:
  ```
  plan → act → observe → reflect → (plan | compact | terminate)
                                      compact → plan
  ```
- `plan_node` updated — includes `compaction_summary` in LLM prompt
  when present, replacing raw trace entries.

### 4. `run.py` — Initial state updated
- `compaction_summary=""` and `_compact_requested=False` added to
  `build_initial_state()`.

### 5. `.env.example` — New vars
- `ADE_COMPACTION_ENABLED=true`
- `ADE_COMPACTION_THRESHOLD=15`

## What You Need To Do

### Backend (BLK-039 remaining items):
1. **SSE endpoint (BLK-023)**: Accept a `compact` event from the frontend.
   When received, set `_compact_requested=True` in the run's state. This
   enables the manual /compaction trigger.
2. **Unit tests**: Write tests for:
   - Auto-compaction triggers at threshold
   - Manual compaction via `_compact_requested` flag
   - Compaction preserves `attempted` set and `gap_report`
   - `compaction_summary` appears in plan node prompt after compaction
   - Code-based fallback summary works without LLM
3. **Integration test**: Long-running extraction triggers auto-compaction
   and the agent continues successfully with the summary.

## Design Constraints

- The `attempted` set is NEVER compacted — retry-loop prevention is
  non-negotiable [§12.3]
- The full trace persists in the LangGraph checkpoint — compaction only
  affects what's in the active LLM prompt
- `compaction_summary` is a single string field, not a complex data
  structure [SF]
- Manual compaction resets the trace window but does not reset extraction
  state, gaps, or attempted set

## Action Required

1. Read vision.md §12.4 for the full design.
2. Review BLK-039 acceptance criteria.
3. Implement the SSE `compact` event handler in BLK-023.
4. Write the unit and integration tests listed in BLK-039.
5. Acknowledge by replying to `mgmt/inbox/`.

## Constraints

- Do not modify `vision.md` or `backlog/` — these are mgmt-owned.
- The compact node uses the same LLM client as the plan node (GPT-5.4).
- Compaction is opt-in via `ADE_COMPACTION_ENABLED` (default: true).


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
