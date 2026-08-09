---
id: BLK-012
type: feature
title: "InvoiceTemplate implementation (Pydantic schema)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-001]
tags: [templates, invoice, v1-slice]
---

## Description

Implement the InvoiceTemplate — a Pydantic schema declaring what a valid
invoice extraction looks like. Fields: invoice_number, invoice_date, vendor,
line_items[], subtotal, tax, total. Document-agnostic — says what, not how.

## Acceptance Criteria

- [ ] `src/templates/invoice.py` with InvoiceTemplate(BaseModel)
- [ ] LineItem nested schema (description, quantity, unit_price, amount)
- [ ] Field descriptions for agent guidance
- [ ] Confidence threshold field (default 0.8)

## Dependencies

- BLK-001 (Template base class)

## Notes

- vision.md §3.1 (Template), §9 (v1 vertical slice)
- Existing `src/templates/invoice.py` has a first draft — refine
