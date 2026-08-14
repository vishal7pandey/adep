---
id: BLK-256
type: bug
title: "Document upload validates only the file extension — no content-type/magic-byte check, no streamed-size cap, no decompression-bomb guard"
priority: high
status: backlog
phase: 2
owner: devin
created: 2026-08-09T13:20:00+05:30
started: null
completed: null
estimate: S
depends-on: [BLK-131]
tags: [backend, security, upload, dos, validation, reliability]
---

## Description

`POST /documents` in `src/api/routes/documents.py`:

- Validates only the filename **extension** (line 31–37) — no Content-Type check against the actual bytes, so an attacker can name anything `.pdf`/`.png`.
- Streams the **entire upload to a temp file before** the 20MB size check (copyfileobj then `st_size`) — disk is written first, so the size limit cannot stop disk exhaustion by large bodies.
- Followers then hand the file to PyMuPDF/PIL/page rasterization in `src/documents/store.py` (lines ~209-223, ~247-274) with **no page-count cap, no pixel-dimension cap, and no decompression-bomb guard** — a small crafted PNG/PDF can force multi-GB rasterization/decoding.

## Problem Statement

Combine the extension-only inbound gate with the unbounded decode creates a cheap DoS and a mixed-content upload vector on a public endpoint (registrations/auth may be disabled by default regardless of `auth_enabled` in some environments). Also, the temp-file-first pattern contradicts the documented "Max file size: 20MB" — the check happens after the body was already written to disk.

## Acceptance Criteria

- [ ] Validate file magic bytes / decoded format against the declared extension (reject mismatches with 400)
- [ ] Enforce the size cap *while streaming* (fail before buffering the full body), or use a streaming limit on the request body
- [ ] Add page-count and pixel-dimension caps before rasterization (reject/hold instead of OOM)
- [ ] Add a decompression-bomb test (e.g. a 100x100 PNG inflated with large texture / a zip-bomb PDF) that must not balloon memory
- [ ] Tests: oversized body can't reach disk; mismatched content → 400; multi-thousand-page PDF → 400/413

## Constraints

- Do not break the normal PDF/PNG/JPG/TIFF/BMP upload flows (BLK-059, BLK-131)
- Keep the thumbnails/rasterization pipeline intact for valid files

## Dependencies

- `src/api/routes/documents.py`
- `src/documents/store.py` (import_document / rasterizer)
- `src/config.py` (size cap constants)

## Implementation Log

- **2026-08-09 (mgmt)**: Assigned to `devin` in the 4-team reorg (devin/antigravity/cline/opencode). See REMEDIATION_PLAN.md.

- **2026-08-09T13:20**: Filed after reading upload route + rasterization chain; no magic-byte or decode-side caps found.