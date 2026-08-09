---
id: BLK-105
type: feature
title: "Add depth — enhance existing skills with more detailed probe orders and invariants"
priority: medium
status: backlog
phase: 4
owner: backend
created: 2026-08-08T03:30:00+05:30
estimate: M
depends-on: [BLK-103]
tags: [backend, skills, depth, enhancement]
---

## Description

The current 12 skills have basic probe orders and 1-2 invariants
each. Add depth by:

1. **Multi-step probe orders** — most skills have 2-3 steps. Add
   4-6 steps that cover edge cases (handwriting, degraded scans,
   multi-page tables, stamps/signatures).
2. **More invariants** — add cross-field validation (date ranges,
   numeric bounds, format checks, business logic rules).
3. **Known failure modes** — document 3-5 known failure patterns
   per skill with specific failure actions.
4. **Confidence overrides** — set per-field confidence thresholds
   based on field difficulty (e.g., handwritten fields get 0.6,
   printed fields get 0.85).

## Per-Skill Enhancement Plan

### Invoice (already well-built — reference model)
- Current: 3 probe steps, 1 invariant (subtotal + tax = total)
- Add: date range check (invoice_date <= due_date <= today + 365)
- Add: vendor_name format check (non-empty, > 2 chars)
- Add: line_items sum check (sum of line item totals = subtotal)

### Utility Bill
- Current: basic probe order
- Add: usage calculation check (current - previous = usage kWh)
- Add: amount_due = usage × rate + fees
- Add: date range check (billing period <= 45 days)

### Medical Claim (CMS-1500)
- Current: NPI 10-digit check, date order
- Add: service date range check (from <= to)
- Add: total charge = sum of line charges
- Add: NPI Luhn checksum validation

### BOQ
- Current: basic
- Add: amount = qty × rate for each line
- Add: subtotal = sum of all line amounts
- Add: grand total = subtotal + tax

### Commercial Lease
- Current: expiration = commencement + term
- Add: rent_escalation rate check (0-20% annually)
- Add: CAM charges <= rent × 0.3 (rule of thumb)

### Commodity Trade
- Current: volume within ±5% LC tolerance
- Add: total_value = volume × unit_price
- Add: delivery date > trade date

### Metallurgical Assay
- Current: composition within spec range
- Add: sum of all elements = 100% (±0.5%)
- Add: density check if provided

### Store Audit
- Current: cleanliness 1-5 scale
- Add: all checklist items answered
- Add: score = average of all category scores

### Compliance Audit
- Current: retention ≥ 365 days
- Add: audit date <= today
- Add: all required sections present

### Thermal Receipt
- Current: subtotal + tax = total
- Add: line items sum = subtotal
- Add: date format check

### Ad Buy / Insertion Order
- Current: local sums = national total
- Add: total_budget = sum of line items
- Add: flight dates (start < end)

### Trade Finance (LC)
- Current: basic
- Add: LC amount = goods value
- Add: expiry date > shipment date
- Add: documents list completeness check

## Acceptance Criteria

- [ ] Each skill has 4-6 probe steps
- [ ] Each skill has 3+ invariants
- [ ] Each skill documents 3+ known failure modes
- [ ] Each skill has per-field confidence overrides
- [ ] All invariants tested with pass/fail cases
- [ ] No regression in existing 745 tests

## Notes

- This is depth work, not new document types
- Use sample data from `sample-data/` to validate probe orders
- Reference: InvoiceSkill is the gold standard — other skills
  should match its level of detail
