---
id: BLK-011
type: feature
title: "InvoiceSkill implementation"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-009]
tags: [skills, invoice, v1-slice]
---

## Description

Implement the InvoiceSkill — a concrete Skill for invoice extraction.
Bundles system prompt, tool preferences (prefer ocr for tabular charges,
vlm for charts), probe order, invariants (subtotal + tax == total ± 0.01),
failure actions, and known failure modes (thermal receipts: deskew before ocr).

## Acceptance Criteria

- [ ] `src/skills/invoice.py` with InvoiceSkill dataclass
- [ ] System prompt frames agent for invoice extraction [PE]
- [ ] Tool preferences declared (ocr for text, vlm for charts/handwriting)
- [ ] Probe order: header band → line items → totals
- [ ] Invariant: subtotal + tax == total ± 0.01
- [ ] Failure actions table mapping GapTypes to candidate actions
- [ ] Known failure modes documented (thermal receipts, faint prints)

## Dependencies

- BLK-009 (GapType, Invariant from validator)

## Notes

- vision.md §3.2 (Skill), §9 (v1 vertical slice: Invoice)
- Existing `src/skills/invoice.py` has a first draft — refine
