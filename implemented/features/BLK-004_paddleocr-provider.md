---
id: BLK-004
type: feature
title: "PaddleOCR provider (detect_layout, detect_text, ocr)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-003]
tags: [providers, ocr, paddle, perception]
---

## Description

Implement the PaddleOCR provider wrapping PaddleOCR for `detect_layout`,
`detect_text`, and `ocr` tools. Primary OCR backend — gives bboxes + scores,
self-hostable. Already used in L2 notebooks.

## Acceptance Criteria

- [ ] `src/providers/ocr_paddle.py` with detect_layout, detect_text, ocr functions
- [ ] Each function returns ToolResult with Grounding (bbox + confidence)
- [ ] Config-driven: selected when `ADE_OCR_PROVIDER=paddle`
- [ ] Handles missing PaddleOCR installation gracefully (clear error message)
- [ ] Unit tests with mocked PaddleOCR

## Constraints

- PaddleOCR must be in requirements.txt
- No hardcoding of model paths — use PaddleOCR defaults or config

## Dependencies

- BLK-003 (ToolRegistry to register into)

## Notes

- vision.md §9 (v1 providers), L2 notebook for reference
- PaddleOCR gives both text and layout detection
