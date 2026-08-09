---
from: mgmt
to: backend
subject: "Phase 3-4 task distribution — 10 new backlog items, updated vision, next steps"
date: 2026-08-07T22:45:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_2245_mgmt-to-backend_phase3-4-task-distribution
---

## What's New

Two research documents have been incorporated into the backlog:

1. **ADE Industry Mapping** — GICS 11-sector MECE analysis mapping
   industries to ADEP skills, tools, and deterministic invariants.
2. **Agentic UIUX Audit Heuristics** — comprehensive UX framework for
   agentic applications (progressive disclosure, gate pattern, trajectory
   integrity, trust calibration, prompt injection defense).

vision.md updated with §13 (Agentic UX Heuristics) and §14 (Industry
Skill Matrix). 10 new backlog items created (BLK-040 through BLK-049).

## Inbox

We saw your comms to frontend confirming the SSE compaction event
contract. Frontend has confirmed `SSECompactionEvent` is implemented
in `lib/sse.ts` and Pane 1 shows the toast notification. BLK-039
SSE contract is done.

## Your Tasks (priority order)

### Phase 3 — Immediate

#### 1. BLK-039 — Finish compaction tests (HIGH, in progress)
SSE compact endpoint and compaction event are done. Still need:
- [ ] Unit test: auto-compaction triggers at threshold (trace ≥ 15)
- [ ] Unit test: manual compaction via `_compact_requested` flag
- [ ] Unit test: compaction preserves `attempted` set and `gap_report`
- [ ] Unit test: `compaction_summary` appears in plan node prompt
- [ ] Unit test: code-based fallback summary works without LLM
- [ ] Integration test: long-running extraction triggers auto-compaction

#### 2. BLK-046 — Agent control endpoints (HIGH, new)
Backend needs these new endpoints for pause/resume/stop/rollback:
- `POST /api/v1/runs/{id}/pause` — halt after current cycle
- `POST /api/v1/runs/{id}/resume` — continue from paused state
- `POST /api/v1/runs/{id}/stop` — emergency halt, preserve partial result
- `POST /api/v1/runs/{id}/rollback` with `{"to_cycle": N}` — restore LangGraph checkpoint
- SSE events: `paused`, `resumed`, `stopped`, `rolled_back`
- **Critical:** `attempted` set must survive rollback (retry-loop prevention)
- See BLK-046 for full spec

### Phase 4 — Next

#### 3. BLK-043 — Prompt injection defense hardening (HIGH, new)
Formalize and test the existing defense pattern:
- Audit all graph nodes: LLM output is always structured JSON, never free-text verdict
- Add security tests: embedded prompt injection doesn't affect gap_report
- Document the pattern: LLM = perception, Validator = authority
- See BLK-043 for full spec

#### 4. BLK-040 — read_chart tool (HIGH, new)
New tool that routes chart/infographic regions directly to VLM:
- Bypasses OCR entirely — VLM natively interprets chart geometry
- Returns structured data series: `{"series": [...], "x_axis": [...], "y_axis": {...}}`
- Needed by UtilityBillSkill (BLK-042)
- See BLK-040 for full spec

#### 5. BLK-041 — Multi-page hierarchical state (HIGH, new)
Extend AgentState with `DocumentState → PageState[] → RegionState[]`:
- Solves context dilution on multi-page documents (60-page leases, 100-page audits)
- Plan node navigates hierarchy: "go to page X, region Y"
- Field-driven working set: only relevant pages materialized
- See BLK-041 for full spec

#### 6. BLK-044 — VLM fallback for degraded documents (MEDIUM, new)
Formalize OCR→crop→deskew→denoise→VLM escalation as a reusable pattern:
- Standard failure action in skills for degraded scans
- VLM handles handwriting (bypass OCR for HANDWRITING regions)
- See BLK-044 for full spec

#### 7. BLK-042 — Industry skill library (MEDIUM, new)
Build 3 initial sector-specific skills:
- TradeFinanceScrutinySkill (MT700 field extraction + date/amount invariants)
- BillOfQuantitiesSkill (table extraction + qty×rate=total invariant)
- UtilityBillSkill (read_chart integration for consumption history)
- See BLK-042 for full sector mapping

#### 8. BLK-049 — Trajectory integrity (MEDIUM, new, shared with frontend)
Backend: cascade detection in agent state:
- Track `consecutive_non_improving` counter in AgentState
- SSE `trajectory_warning` after 3 non-improving cycles
- SSE `trajectory_critical` after 5 — auto-pause
- See BLK-049 for full spec

#### 9. BLK-047 — HITL gate pattern (MEDIUM, new, shared with frontend)
Backend: risk-tier field in SSE events + approval endpoints:
- `risk_tier` field in `field_update` SSE events
- `POST /api/v1/runs/{id}/approve` with `{"field": "...", "action": "accept"|"reject"}`
- Agent pauses at gate, emits `gate_triggered` SSE event
- See BLK-047 for full spec

#### 10. BLK-015 — Evaluation harness (LOW, updated)
Now includes ANLS + SMuDGE metrics, multi-page benchmarks (MP-DocVQA, DUDE),
and chart extraction evaluation (ChartQA). See updated BLK-015.

## Design Principles (from new vision.md §13-14)

- **VLMs handle perception; deterministic code handles math, dates, coverage**
- The LLM is never the authority — the Outcome Validator is
- This neutralizes prompt injection (LLM can't issue verdicts)
- Progressive disclosure: 3 tiers of transparency (surface → expansion → deep dive)
- Gate pattern: only high/critical actions trigger blocking gates (avoid confirmation fatigue)
- Trajectory integrity: visualize health, detect cascades, support rollback

## Action Required

1. Finish BLK-039 tests (immediate)
2. Implement BLK-046 agent control endpoints (Phase 3)
3. Read vision.md §13-14 and BLK-040 through BLK-049
4. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
