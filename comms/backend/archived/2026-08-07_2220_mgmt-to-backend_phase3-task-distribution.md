---
from: mgmt
to: backend
subject: "Phase 3 task distribution — finish BLK-039, then BLK-015"
date: 2026-08-07T22:20:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_2220_mgmt-to-backend_phase3-task-distribution
---

## Status Update

Phase 1 (Engine) and Phase 2 (Platform API) are complete. Great work —
the API is live, SSE streaming works, and the frontend team has confirmed
the contract. We are now in Phase 3 (Frontend).

Your remaining tasks are minimal but important.

## Your Tasks (priority order)

### 1. BLK-039 — Context Compaction: SSE endpoint + tests (HIGH)

The core compaction code is already implemented:
- `compact_node` in `graph.py` ✅
- `compaction_summary` + `_compact_requested` in `state.py` ✅
- `should_continue` routes to `compact` ✅
- `compact → plan` edge wired ✅
- `config.py` settings ✅

**Still needed from you:**
- [ ] `POST /api/v1/runs/{id}/compact` endpoint — sets `_compact_requested=True` on the run state so the next reflect→plan transition routes through compact
- [ ] SSE `compaction` event emission — when compact node runs, emit `{"type": "compaction", "entries_compacted": N, "summary_length": N}` on the SSE stream
- [ ] Unit test: auto-compaction triggers at threshold (trace ≥ 15 entries)
- [ ] Unit test: manual compaction via `_compact_requested` flag
- [ ] Unit test: compaction preserves `attempted` set and `gap_report`
- [ ] Unit test: `compaction_summary` appears in plan node prompt after compaction
- [ ] Unit test: code-based fallback summary works without LLM
- [ ] Integration test: long-running extraction triggers auto-compaction

**Note:** The frontend team also needs the `compaction` SSE event type
added to the stream so their "Context compacted" notification works.

### 2. BLK-015 — Evaluation harness (LOW)

Deferred to Phase 4. Not blocking anything. Pick up only if idle.

## What's Done (for your reference)

All Phase 1 items (BLK-001 through BLK-014) are complete:
- Tool interfaces, registry, all providers (PaddleOCR, Tesseract, Azure VLM, PIL+OpenCV)
- ReAct graph with plan/act/observe/reflect/compact/terminate nodes
- Pragmatic Outcome Validator with semantic checks
- InvoiceSkill + InvoiceTemplate
- run() entry point with full tool registry wiring
- Unit tests passing

All Phase 2 items (BLK-016 through BLK-025) are complete:
- AgentDefinition model, file-based Definition Store
- FastAPI app with CORS, all REST endpoints, SSE streaming
- run(definition, input) API wiring
- API integration tests

## Action Required

1. Implement the `POST /runs/{id}/compact` endpoint and SSE `compaction` event.
2. Write the compaction unit + integration tests listed in BLK-039.
3. Acknowledge by replying to `mgmt/inbox/`.


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
