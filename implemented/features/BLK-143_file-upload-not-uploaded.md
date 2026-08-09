---
id: BLK-143
type: bug
title: "File upload in Pane1AgentConsole only sets filename locally — never uploads to backend"
priority: high
status: backlog
phase: 4
owner: frontend
created: 2026-08-08T14:45:00+05:30
estimate: M
tags: [frontend, bug, document-upload, shallow-impl]
---

## Problem

`handleFileUpload` and `handleDrop` in
`frontend/components/workbench/Pane1AgentConsole.tsx` only set the
filename in local state and call `setDocument(fname)` — they never
upload the file to the backend via `POST /api/v1/documents`. The
backend document store is never populated, so when a real run is
started, the document won't exist on the server.

## Evidence

`frontend/components/workbench/Pane1AgentConsole.tsx:246-276`:
```typescript
const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const fname = e.target.files[0].name;
      setUploadedFileName(fname);
      setDocument(fname);  // only sets filename in context
    }
  };

  // ...

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const fname = files[0].name;
      setUploadedFileName(fname);
      setDocument(fname);  // only sets filename in context
    }
  };
```

No `FormData`, no `fetch`, no call to `POST /api/v1/documents`.

The backend has a fully functional document upload endpoint at
`src/api/routes/documents.py:21-62` that accepts file uploads,
validates format, rasterizes PDFs, and stores pages.

## Impact

- Documents are never uploaded to the backend.
- When `startExtractionRun` is eventually wired (per BLK-139), the
  `document_path` sent to the backend won't correspond to any file
  on the server — the run will fail.
- The document viewer (Pane3) has no real pages to display.

## Reproduction or reasoning

1. Open the workbench.
2. Upload a file via drag-drop or file picker.
3. Check the backend document store (`.adep/documents/`) — empty.
4. The filename appears in the UI but no document exists server-side.

## Proposed resolution

1. In `handleFileUpload` and `handleDrop`, create a `FormData` with
   the file and `POST` it to `${API_BASE_URL}/documents`.
2. Use the returned document metadata (which includes `document_id`
   and page paths) to set the document URL for run creation.
3. Add a loading state during upload.
4. Add error handling for upload failures (unsupported format, file
   too large).

## Acceptance criteria

- [ ] File upload sends `FormData` to `POST /api/v1/documents`
- [ ] Upload loading state is shown
- [ ] Upload errors are displayed to the user
- [ ] Document ID from response is used for run creation
- [ ] Both drag-drop and file picker use the same upload path

## Validation plan

- Upload a PDF and verify it appears in `.adep/documents/`
- Upload an unsupported format and verify error is shown
- Upload a file >20MB and verify size limit error is shown
- Verify document metadata is stored for run creation

## Related issues

BLK-139 (startDemoRun mock data — same component needs full rewrite
of run flow), BLK-131 (upload-first flow)
