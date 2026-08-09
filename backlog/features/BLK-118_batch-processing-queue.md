---
id: BLK-118
type: feature
title: "Batch processing queue"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T04:30:00+05:30
estimate: XL
depends-on: []
tags: [frontend, backend, ux, batch, enterprise, queue]
---

## Description

Batch upload and processing queue for enterprise users who need to
process hundreds of documents.

## Requirements

### Frontend
- Drag-drop multiple files or select a folder
- Queue visualization: file list with status (pending, running,
  completed, failed)
- Progress bar showing N/M documents processed
- Auto-start next document when current completes
- Summary report at end: success rate, avg confidence, failures list
- "Export All Results" button (ZIP of JSON/CSV per document)

### Backend (dependency)
- `POST /runs/batch` endpoint for queue management
- Progress SSE events per document
- Concurrent execution with configurable parallelism

## Acceptance Criteria

- [ ] Batch upload UI with drag-drop multi-file
- [ ] Queue visualization with per-file status
- [ ] Progress bar and summary report
- [ ] Backend batch endpoint implemented
- [ ] Export all results as ZIP
- [ ] Error handling for failed documents (doesn't stop queue)

## Source

Frontend proposal #5 in `2026-08-08_0425_frontend-to-mgmt_engineering-proposals.md`

## Notes

This is the feature that separates a demo from a product. No
enterprise customer will adopt one-at-a-time extraction. However,
it requires backend support — frontend can build UI with mock data
first. This should be prioritized after the core extraction pipeline
is proven end-to-end (BLK-103).
