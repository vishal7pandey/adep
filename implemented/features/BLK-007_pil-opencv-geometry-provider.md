---
id: BLK-007
type: feature
title: "PIL + OpenCV geometry provider (crop, rotate, deskew, etc.)"
priority: high
status: backlog
phase: 1
owner: unassigned
created: 2026-08-07T20:30:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-003]
tags: [providers, geometry, pil, opencv]
---

## Description

Implement geometry tools using PIL + OpenCV: `crop`, `rotate`, `deskew`,
`auto_orient`, `resize`, `denoise`, `threshold`. Follow the geometry-tool
split (§2.3): `deskew`/`auto_orient` auto-estimate angles; `rotate` takes
agent-supplied angle only.

## Acceptance Criteria

- [ ] `src/providers/image_cv.py` with all 7 geometry functions
- [ ] `deskew` and `auto_orient` auto-estimate angle (Hough/minAreaRect)
- [ ] `rotate` takes explicit angle (agent-supplied, deliberate only)
- [ ] All functions return ToolResult with processed image handle
- [ ] Unit tests with sample images

## Constraints

- No new dependencies beyond PIL + OpenCV (already in requirements.txt)
- Auto-estimating tools must not require agent to supply geometry params

## Dependencies

- BLK-003 (ToolRegistry)

## Notes

- vision.md §2.3 (atomic tools, geometry trap), §9 (v1 providers)
