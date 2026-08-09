---
id: BLK-005
type: feature
title: "Tesseract provider (secondary OCR backend)"
priority: medium
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-003]
tags: [providers, ocr, tesseract, perception]
---

## Description

Implement Tesseract as a secondary `ocr` backend for fallback/comparison.
Trivial wrap, already used in L2. Selected when `ADE_OCR_PROVIDER=tesseract`.

## Acceptance Criteria

- [ ] `src/providers/ocr_tesseract.py` with ocr function
- [ ] Returns ToolResult with Grounding
- [ ] Config-driven: selected when `ADE_OCR_PROVIDER=tesseract`
- [ ] Unit tests with mocked Tesseract

## Dependencies

- BLK-003 (ToolRegistry)

## Notes

- vision.md §9 (v1 providers), L2 notebook for reference
- Secondary backend — PaddleOCR is primary
