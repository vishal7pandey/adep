---
from: mgmt
to: backend
subject: "Wave 3 tasks — BLK-042 industry skills, BLK-049 trajectory integrity, BLK-047 HITL gates, BLK-015 eval harness"
date: 2026-08-07T23:25:00+05:30
priority: high
status: new
in-reply-to: 2026-08-07_2320_mgmt-to-backend_next-tasks-readchart-multipage-vlmfallback
message-id: 2026-08-07_2325_mgmt-to-backend_wave3-skills-trajectory-hitl-eval
---

## Context

You should now be working on Wave 2 (BLK-040 read_chart, BLK-041
multi-page state, BLK-044 VLM fallback). This message loads up the
remaining Phase 4 tasks so you have full visibility and can plan
ahead. These are not blocking — start them after Wave 2.

## Wave 3 Tasks (after BLK-040, BLK-041, BLK-044)

### 1. BLK-042 — Industry skill library: 3 initial skills (MEDIUM)

Build 3 sector-specific skills with corresponding templates. Each skill
is a Python dataclass with: system_prompt, tool_prefs, probe_order,
invariants, failure_actions, semantic_checks config.

**Skill 1: TradeFinanceScrutinySkill (Financials)**
- Documents: SWIFT MT700, Bill of Lading, commercial invoice
- Template fields: `lc_number`, `currency`, `amount`, `latest_shipment_date`,
  `on_board_date`, `goods_description`, `required_documents[]`, `additional_conditions`
- Invariants (deterministic code in validator):
  - `on_board_date <= latest_shipment_date` (date arithmetic — NO LLM)
  - `invoice_amount <= lc_amount + tolerance` (numeric comparison)
  - Coverage loop: every document in `required_documents[]` must have a
    grounded examination result (affirmative presence, not absence of negatives)
- VLM role: extract field values from MT700 + presentation documents
- VLM excels at: interpreting free-text Field 47A additional conditions
- Validator role: date arithmetic, amount tolerance, document coverage check
- Failure actions: crop specific field region → deskew → re-OCR → VLM fallback
- Semantic checks: ON (cross-document name matching — consignee on BoL vs LC)

**Skill 2: BillOfQuantitiesSkill (Industrials)**
- Documents: Bill of Quantities (multi-page tabular, BIM-exported)
- Template fields: `work_package`, `line_item`, `description`, `unit`,
  `quantity`, `unit_rate`, `line_total`, `vat_rate`, `vat_amount`, `grand_total`
- Invariants:
  - `quantity * unit_rate == line_total` (within rounding tolerance ±0.01)
  - `sum(line_total) + sum(vat_amount) == grand_total`
  - VAT rate consistency: same `vat_rate` across all line items (or flagged)
- Tool prefs: `detect_tables` first, then `read_table` for extraction
- Failure actions: if OCR confidence < 0.5 on a cell → crop cell → deskew → VLM
- Semantic checks: OFF (deterministic math is sufficient)

**Skill 3: UtilityBillSkill (Utilities)**
- Documents: Utility bills (electricity, gas, water) with chart data
- Template fields: `account_number`, `billing_period_start`, `billing_period_end`,
  `current_usage`, `current_amount`, `usage_unit`, `trailing_12_month_usage[]`,
  `trailing_12_month_amount[]`, `average_monthly_usage`
- Invariants:
  - `sum(trailing_12_month_usage) / 12 == average_monthly_usage` (within tolerance)
  - `current_usage` is within trailing 12-month range (anomaly detection)
- Tool prefs: `detect_layout` → `ocr` for text fields → `read_chart` (BLK-040)
  for consumption history chart
- Failure actions: if `read_chart` fails → crop chart region → VLM direct
- Semantic checks: OFF

**Deliverables per skill:**
- [ ] Skill dataclass in `src/skills/`
- [ ] Template (Pydantic schema) in `src/templates/`
- [ ] Invariants registered in validator config
- [ ] Unit test with sample document fixture
- [ ] Skill + Template registered in Definition Store
- [ ] Agent Definition created pairing the skill + template

### 2. BLK-049 — Trajectory integrity backend (MEDIUM, shared with frontend)

Add cascade detection to agent state and emit SSE events.

**State changes:**
- Add `consecutive_non_improving: int` to AgentState (default 0)
- In `reflect_node`: compare current `gap_report.gaps` count vs previous
  - If gaps decreased: reset `consecutive_non_improving = 0`
  - If gaps same or increased: increment `consecutive_non_improving += 1`
- Track `last_gap_count: int` in AgentState for comparison

**SSE events:**
- `trajectory_warning`: emit when `consecutive_non_improving >= 3`
  ```json
  {"type": "trajectory_warning", "consecutive_non_improving": 3, "cycle": 7, "message": "Agent may be stuck — 3 cycles without progress"}
  ```
- `trajectory_critical`: emit when `consecutive_non_improving >= 5`
  ```json
  {"type": "trajectory_critical", "consecutive_non_improving": 5, "cycle": 9, "message": "Agent likely stuck — auto-pausing for user intervention"}
  ```
- On `trajectory_critical`: auto-pause the agent (set status to paused,
  emit `paused` SSE event as well)

**Tests:**
- [ ] Unit test: 3 non-improving cycles triggers `trajectory_warning`
- [ ] Unit test: 5 non-improving cycles triggers `trajectory_critical` + auto-pause
- [ ] Unit test: gap reduction resets counter
- [ ] Unit test: compaction resets counter (fresh summary, agent may take new approach)

### 3. BLK-047 — HITL gate pattern backend (MEDIUM, shared with frontend)

Add risk tiers to SSE events and approval endpoints.

**SSE `field_update` event — add `risk_tier` field:**
```json
{
  "type": "field_update",
  "field": "invoice_total",
  "value": "1234.56",
  "confidence": 0.42,
  "risk_tier": "high",
  "bbox": {...},
  "page": 1
}
```

**Risk tier classification (in `observe_node` or `reflect_node`):**
- `low`: confidence ≥ 0.8
- `medium`: confidence 0.5–0.79
- `high`: confidence < 0.5 OR semantic check failed
- `critical`: agent wants to terminate with partial result (gap_report has unresolved required fields)

**New SSE event — `gate_triggered`:**
```json
{
  "type": "gate_triggered",
  "field": "invoice_total",
  "risk_tier": "high",
  "proposed_value": "1234.56",
  "confidence": 0.42,
  "agent_reasoning": "VLM extracted from top-right region but text is partially obscured",
  "bbox": {...},
  "page": 1
}
```

**New endpoint — `POST /api/v1/runs/{id}/approve`:**
```json
// Request:
{"field": "invoice_total", "action": "accept" | "reject"}

// Response (accept):
{"run_id": "...", "field": "invoice_total", "accepted": true, "message": "Value locked, agent continuing"}

// Response (reject):
{"run_id": "...", "field": "invoice_total", "rejected": true, "message": "Agent will retry with different approach"}
```

**Behavior:**
- `high` risk: agent pauses (emits `gate_triggered` + `paused`), waits for approve/reject
- `critical` risk: agent pauses, emits `gate_triggered` with `risk_tier: "critical"`
- `medium` risk: non-blocking — field is flagged in extraction but agent continues
- `low` risk: no gate — auto-accept
- Timeout: high-risk auto-rejects after 120s (deny by default). Critical: no timeout (waits indefinitely).
- On `accept`: lock field value in extraction, mark as `verified`, agent continues
- On `reject`: clear field value, add to `attempted` set, agent retries

**Tests:**
- [ ] Unit test: low confidence extraction triggers `gate_triggered` with `high` risk
- [ ] Unit test: approve endpoint locks value, agent resumes
- [ ] Unit test: reject endpoint clears value, agent retries
- [ ] Unit test: timeout auto-rejects after 120s
- [ ] Unit test: medium risk does not pause agent

### 4. BLK-015 — Evaluation harness (LOW)

Updated spec now includes ANLS + SMuDGE metrics. See BLK-015 for full
benchmark table. This is lowest priority — pick up only when idle.

**Key deliverables:**
- [ ] Evaluation script: runs extraction on fixture set
- [ ] ANLS metric: Normalized Levenshtein Similarity per field
- [ ] SMuDGE-style metric: bbox IoU with ground truth + output type checking
- [ ] Confidence calibration: confidence vs actual accuracy curve
- [ ] Per-field + per-sector breakdown
- [ ] HTML/JSON report output
- [ ] Multi-page document support (MP-DocVQA style)
- [ ] Chart extraction evaluation (ChartQA-style series comparison)

## Full Backend Pipeline (for your planning)

| Wave | Items | Status |
|------|-------|--------|
| 1 | BLK-039, BLK-046, BLK-043 | ✅ Done |
| 2 | BLK-040, BLK-041, BLK-044 | Assigned (working) |
| 3 | BLK-042, BLK-049, BLK-047, BLK-015 | This message (queue after Wave 2) |

## Action Required

1. Continue Wave 2 (BLK-040, BLK-041, BLK-044)
2. Plan Wave 3 — review specs now so there are no surprises
3. BLK-042 depends on BLK-040 (read_chart for UtilityBillSkill) — sequence accordingly
4. BLK-049 and BLK-047 are independent — can be done in parallel
5. Acknowledge by replying to `mgmt/inbox/`


## Resolution

Work completed. Reply sent to mgmt/inbox/. See completion messages for details.
