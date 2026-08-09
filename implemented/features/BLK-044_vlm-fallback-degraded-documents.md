---
id: BLK-044
type: feature
title: "VLM fallback for degraded documents — OCR→crop→VLM escalation"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-07T22:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-004, BLK-005, BLK-006]
tags: [tools, vlm, ocr, fallback, degraded, thermal, assay]
---

## Description

Formalize the OCR→VLM fallback pattern as a standard failure action in
skills. When OCR returns confidence below threshold on a region, the
agent crops the specific region, applies geometry corrections (deskew,
denoise, threshold), and escalates to VLM for native visual
interpretation.

## Motivation

ADE industry mapping identifies multiple sectors with degraded document
challenges:
- §Sector 6 (Materials): dot-matrix printed assay certificates from remote mining sites
- §Sector 9 (Consumer Staples): crumpled, faded thermal receipts
- §Sector 7 (Health Care): handwritten physician notes on CRFs

The InvoiceSkill already has basic failure actions, but the
OCR→geometry→VLM escalation pattern needs to be a reusable, tested
strategy across all skills.

## Acceptance Criteria

- [ ] Standard failure action pattern documented: OCR fail → crop region → deskew → denoise → threshold → VLM
- [ ] Skill failure_actions can reference this pattern via a named constant
- [ ] Geometry tools (deskew, denoise, threshold) available in tool registry
- [ ] VLM handles handwriting recognition (bypass OCR for HANDWRITING regions)
- [ ] Test: degraded scan with OCR confidence < 0.5 triggers VLM fallback
- [ ] Test: handwritten region routes directly to VLM (skips OCR)
- [ ] Test: thermal receipt with faded ink — geometry-first probe order succeeds

## Constraints

- Probe order is skill-specific — not all skills should do geometry-first [SF]
- The fallback is a pattern, not a hardcoded graph change — skills define it in failure_actions
- VLM is more expensive than OCR — only escalate on actual failure

## Dependencies

- BLK-004 (PaddleOCR), BLK-005 (Tesseract), BLK-006 (Azure VLM)

## Notes

- ADE industry mapping: §Sector 6 (Materials), §Sector 9 (Staples), §Sector 7 (Health Care)
- ThermalReceiptSkill: geometry-first probe order (auto_orient, deskew before OCR)
- MetallurgicalAssaySkill: OCR→crop→VLM for dot-matrix prints
