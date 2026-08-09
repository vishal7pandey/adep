---
id: BLK-113
type: feature
title: "Drag-and-drop document upload zone"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: S
depends-on: []
tags: [frontend, ux, upload, drag-drop]
---

## Description

Make the entire empty state area in Pane 1 a drop zone for document
upload. Currently the upload is a small button with a hidden file
input.

## Requirements

- Full-height dashed border on drag-enter with "Drop your document
  here" overlay
- Animate border with Electric Blue pulse on drag-over
- Accept `.pdf`, `.png`, `.jpg`, `.tiff`
- Show file preview thumbnail after drop
- Support multi-file drop for batch queuing (ties into BLK-118)

## Acceptance Criteria

- [ ] Drag-drop works across entire Pane 1 empty state
- [ ] Visual feedback on drag-enter and drag-over
- [ ] File type validation with error message for unsupported types
- [ ] File preview thumbnail after successful drop
- [ ] Click-to-upload still works as fallback
- [ ] No backend dependency

## Source

Frontend proposal #2 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`
