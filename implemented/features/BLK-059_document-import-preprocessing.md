---
id: BLK-059
type: feature
title: "Document import & pre-processing pipeline — multi-format upload and page rasterization"
priority: medium
status: backlog
phase: 4
owner: unassigned
created: 2026-08-08T00:05:00+05:30
started: null
completed: null
estimate: M
depends-on: [BLK-007]
tags: [backend, documents, import, pdf, images, ocr, pre-processing]
---

## Description

Handle multi-format document uploads (PDF, PNG, JPG, TIFF, BMP) and
pre-process them into a standard per-page image format that the agent
can process. Also extract initial metadata (page count, dimensions).

## Motivation

Users will upload real-world documents in many formats. The agent
operates on images/pages, so the backend must normalize input to a
consistent representation.

## Supported Formats

| Format | Input | Handling |
|--------|-------|----------|
| PDF | Multi-page documents | Rasterize each page to 150 DPI PNG |
| PNG/JPG | Single image | Use directly if ≥150 DPI, otherwise scale |
| TIFF | Multi-page or multi-frame | Convert to PNG per page |
| BMP | Single image | Convert to PNG |
| HEIC/HEIF | iPhone photos | Convert to PNG (requires libheif) |

## Pre-processing Pipeline

1. **Upload** to temporary directory
2. **Validate**:
   - File size ≤ 20MB
   - MIME type matches extension
   - PDF password-protected files rejected
3. **Identify format** and page count
4. **Rasterize** to 150 DPI PNG per page
5. **Generate thumbnails** (300px wide) for UI preview
6. **Compute metadata**:
   - Total pages
   - Page dimensions in pixels
   - Aspect ratio
   - Approximate DPI
7. **Move to `.adep/documents/{doc_id}/`**: `page_001.png`, `page_002.png`, ..., `thumbnail.jpg`, `meta.json`

## API

- `POST /api/v1/documents` — multipart upload
  ```json
  {"document_id": "...", "pages": 2, "page_paths": ["..."], "thumbnail": "..."}
  ```
- `GET /api/v1/documents/{id}` — metadata
- `GET /api/v1/documents/{id}/page/{n}` — page image
- `GET /api/v1/documents/{id}/thumbnail` — thumbnail

## Acceptance Criteria

- [ ] Support PDF, PNG, JPG, TIFF, BMP
- [ ] PDF rasterization at 150 DPI
- [ ] Page count and dimensions extracted
- [ ] Thumbnails generated
- [ ] File size limit (20MB) with clear error
- [ ] Password-protected PDFs rejected with clear error
- [ ] Document metadata persisted in `.adep/documents/{id}/meta.json`
- [ ] Page images persisted as `page_NNN.png`
- [ ] Unit tests for each format
- [ ] Integration test: upload PDF → 2 pages → rasterize correctly

## Constraints

- v1 supports common formats only. HEIC can be v2.
- Rasterization uses PIL/PyMuPDF, not expensive OCR at this stage [SF]
- Document store is file-based (v1), not object storage

## Dependencies

- BLK-007 (PIL + OpenCV geometry provider)
