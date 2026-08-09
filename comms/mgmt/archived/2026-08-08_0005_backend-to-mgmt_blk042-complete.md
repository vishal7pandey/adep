---
from: backend
to: mgmt
subject: "BLK-042 complete â€” 3 industry skills, 307 tests passing"
date: 2026-08-08T00:05:00+05:30
priority: medium
status: closed
in-reply-to: 2026-08-07_2355_backend-to-mgmt_blk044-complete
message-id: 2026-08-08_0005_backend-to-mgmt_blk042-complete
---

## Context

BLK-042 (Industry Skill Library â€” 3 initial skills) is complete.
307 tests pass in 3.75s.

## Acceptance Criteria â€” All Met

- [x] 3 skills implemented: TradeFinance, BillOfQuantities, UtilityBill
- [x] Each skill has: system_prompt, tool_prefs, probe_order, invariants, failure_actions
- [x] Each skill has a corresponding Template (schema contract)
- [x] TradeFinanceScrutinySkill: MT700 field extraction + date arithmetic invariants
- [x] BillOfQuantitiesSkill: table extraction + qtyÃ—rate=total invariant
- [x] UtilityBillSkill: read_chart integration for consumption history
- [x] Each skill tested with invariant validation
- [x] VLM fallback actions integrated from BLK-044

## Implementation

### Skills Created

**`src/skills/trade_finance.py`** â€” TradeFinanceScrutinySkill
- Template: `TradeFinanceTemplate` (12 fields: lc_number, lc_amount, currency, dates, parties, ports, goods)
- Invariants: expiry_date > issue_date, latest_shipment_date â‰¤ expiry_date
- Tool prefs: OCR for text, VLM for handwriting/stamps, read_chart for charts
- Failure actions: MT700 field number navigation + VLM fallback

**`src/skills/bill_of_quantities.py`** â€” BillOfQuantitiesSkill
- Template: `BillOfQuantitiesTemplate` (9 fields: project, line_items, totals, VAT)
- Invariants: qty Ã— rate = total per line item, subtotal + vat = grand_total
- Tool prefs: read_table for tables (primary), OCR for text
- Failure actions: table-focused extraction + VLM fallback

**`src/skills/utility_bill.py`** â€” UtilityBillSkill
- Template: `UtilityBillTemplate` (12 fields: account, usage, amounts, consumption_history)
- Invariant: usage values cannot be negative
- Tool prefs: read_chart for charts/figures (consumption history), OCR for text
- Probe order includes chart entry for 12-month consumption history

### Templates Created

- `src/templates/trade_finance.py` â€” TradeFinanceTemplate
- `src/templates/bill_of_quantities.py` â€” BillOfQuantitiesTemplate
- `src/templates/utility_bill.py` â€” UtilityBillTemplate

### Tests â€” `src/tests/test_industry_skills.py` â€” 45 tests
- **TestSkillStructure** (21): parametrized across all 3 skills â€” name, system_prompt, tool_preferences, probe_order, invariants, failure_actions, known_failures, confidence_overrides
- **TestTradeFinanceSkill** (6): expiry after issue pass/fail, shipment before expiry pass/fail, MT700 in prompt, VLM fallback
- **TestBillOfQuantitiesSkill** (6): qtyÃ—rate=total pass/fail, subtotal+vat=grand_total pass/fail, read_table preference
- **TestUtilityBillSkill** (6): read_chart for chart/figure, usage non-negative pass/fail, chart in probe order, read_chart in prompt
- **TestTemplates** (7): all template fields present, all extend Template base

## Test Results

```
307 passed, 1272 warnings in 3.75s
```

## Next Up

Starting BLK-049 (Trajectory integrity â€” cascade detection).


---

## Resolution

Processed by mgmt. Acknowledged, reviewed, and incorporated into the
backlog and roadmap. Completed items moved to `implemented/`. Follow-up
directives issued via comms where required. Archived 2026-08-08T01:25:28+05:30.
