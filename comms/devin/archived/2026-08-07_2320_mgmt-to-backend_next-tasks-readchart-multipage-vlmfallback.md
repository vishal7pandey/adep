---
from: mgmt
to: backend
subject: "Next tasks — BLK-040 read_chart, BLK-041 multi-page state, BLK-044 VLM fallback"
date: 2026-08-07T23:20:00+05:30
priority: high
status: new
in-reply-to: null
message-id: 2026-08-07_2320_mgmt-to-backend_next-tasks-readchart-multipage-vlmfallback
---

## Acknowledgments

Great progress:
- **BLK-039** — SSE compact event + endpoint done, frontend confirmed ✅
- **BLK-046** — Agent control endpoints (pause/resume/stop/rollback) done,
  contract sent to frontend ✅
- **BLK-043** — Prompt injection defense hardening done — system prompt
  reinforcement, `_contains_instruction_patterns` detection, logging ✅

All three are marked complete in STATUS.md.

## Remaining BLK-039 Work

If not already done, please ensure the 6 compaction unit tests and 1
integration test from BLK-039 are written. The SSE event and endpoint
are confirmed, but the test coverage is critical for Phase 3 sign-off.

## Next Tasks (Phase 4, priority order)

### 1. BLK-040 — read_chart tool (HIGH)

New tool that extracts numerical data from charts/infographics by routing
cropped pixels directly to VLM. Bypasses OCR entirely.

**Spec highlights:**
- Input: image handle (cropped chart region), optional `chart_type` hint
- Output: `{"series": [{"label": "...", "values": [...]}], "x_axis": [...], "y_axis": {"min": ..., "max": ...}}`
- Handles bar, line, pie, stacked area charts
- Grounding: bbox of chart region (non-negotiable [§2.5])
- VLM dispatch via Azure GPT-5.4
- Fallback: if VLM confidence < threshold, return partial data with gap
- Register in ToolRegistry
- Unit tests with sample chart images
- Integration test: UtilityBill skill extracts 12-month consumption from bar chart

**Why:** Utility bills, financial reports, energy docs present critical
metrics as charts. Text-only pipelines can't parse these. ChartQA
benchmark shows VLMs excel at native chart interpretation.

### 2. BLK-041 — Multi-page hierarchical state (HIGH)

Extend AgentState with `DocumentState → PageState[] → RegionState[]`.

**Spec highlights:**
- `PageState` dataclass: `page_number`, `regions` (dict), `status`, `fields_extracted`
- `DocumentState` dataclass: `pages` (list[PageState]), `total_pages`, `current_page`
- AgentState gets `document_state: DocumentState`
- `detect_layout` populates PageState per page
- Plan node navigates hierarchy: "go to page X, region Y"
- `crop` tool accepts page + region coordinates
- Field-driven working set: plan node selects only relevant pages for current gaps
- Trace compaction preserves page-level state
- SSE events include `page` field for all tool calls
- Backward compatible: single-page docs work as before (1 PageState)
- Unit test: 5-page document with page-aware navigation
- Integration test: 20-page document, agent navigates to correct pages

**Why:** MP-DocVQA/DUDE benchmarks show VLM accuracy degrades on multi-page
documents due to context dilution. 60-page leases, 100-page compliance
audits need hierarchical navigation.

### 3. BLK-044 — VLM fallback for degraded documents (MEDIUM)

Formalize OCR→crop→deskew→denoise→VLM escalation as a reusable pattern.

**Spec highlights:**
- Standard failure action pattern: OCR fail → crop region → deskew → denoise → threshold → VLM
- Skill `failure_actions` can reference this pattern via a named constant
- Geometry tools (deskew, denoise, threshold) must be in tool registry
  — check if they exist already, if not, add them
- VLM handles handwriting (bypass OCR for `HANDWRITING` regions)
- Test: degraded scan with OCR confidence < 0.5 triggers VLM fallback
- Test: handwritten region routes directly to VLM
- Test: thermal receipt with faded ink — geometry-first probe order

**Why:** Remote mining site assay certs (dot-matrix), thermal receipts
(faded/crumpled), handwritten physician notes on CRFs all need this.

## After These Three

Next up will be:
- BLK-042 — Industry skill library (TradeFinance, BOQ, UtilityBill skills)
- BLK-049 — Trajectory integrity backend (cascade detection + SSE events)
- BLK-047 — HITL gate pattern backend (risk tiers + approval endpoint)
- BLK-015 — Evaluation harness (ANLS + SMuDGE)

## Action Required

1. Confirm BLK-039 tests are written (or write them if not)
2. Start BLK-040 (read_chart) — highest impact, unblocks UtilityBillSkill
3. Then BLK-041 (multi-page state) — unblocks CommercialLease, ComplianceAudit
4. Then BLK-044 (VLM fallback) — unblocks degraded document handling
5. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
