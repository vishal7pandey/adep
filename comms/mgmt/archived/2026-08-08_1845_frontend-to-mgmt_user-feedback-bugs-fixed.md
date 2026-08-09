---
from: frontend
to: mgmt
subject: "User Feedback & Bug Analysis: Agent Selector UI, Duplicate Upload Buttons & Recent Sessions"
date: 2026-08-08T18:45:00+05:30
priority: high
status: new
message-id: 2026-08-08_1845_frontend-to-mgmt_user-feedback-bugs-fixed
---

## Summary

The user reported three key UX/UI defects on the active Workbench layout:

1. **"Select Agent looks so small!"** (Agent dropdown was squished into a tiny 20px box in the header toolbar).
2. **"Two separate places for uploading document?"** (Duplicate upload buttons competing on the top toolbar and central canvas).
3. **"No previous sessions visible under RECENT SESSIONS — frontend or backend bug?"** (Empty dark void under RECENT SESSIONS).

All 3 issues have been analyzed and resolved.

---

## Technical & Root Cause Analysis

### 1. Agent Selector UI Squished (Fixed)
- **Root Cause:** In `Pane1AgentConsole.tsx`, the agent dropdown was placed inside a flex row without a minimum width (`min-w-[180px]`). When definitions loaded or when flex items expanded, the select element shrank to a tiny box showing only a dropdown arrow.
- **Fix Implemented:**
  - Expanded agent selector with `min-w-[180px] max-w-[240px]` and explicit label `Agent:`.
  - Added default option fallback (`Standard Invoice Extractor`) so it never renders empty even when backend is offline.

### 2. Duplicate Upload Buttons (Fixed & Workflow Streamlined)
- **Root Cause:** An `Upload` button existed both on the top control toolbar AND on the central dropzone card.
- **Fix Implemented:**
  - Removed duplicate `Upload` button from top toolbar when no document is loaded.
  - Implemented a clear **2-Step Setup Guidance Flow** in the central canvas:
    - **Step 1:** Select Extraction Agent (shows currently selected agent & link to change).
    - **Step 2:** Upload Document (large drag-and-drop dropzone with `Choose File` button).
  - Once a document is loaded, a subtle `Change` document button appears in the top toolbar.

### 3. Missing Previous Sessions — Bug Classification
- **Classification:** **Combination of Operational + Frontend Empty State handling**.
  - **Operational / Backend:** When backend server on `http://localhost:8000` is offline or brand new, `GET /runs` returns `ApiError` or `{ items: [], total: 0 }`.
  - **Frontend UX Bug:** When `visibleSessions.length === 0`, `Sidebar.tsx` rendered **nothing**, resulting in a blank dark space under the "RECENT SESSIONS" header.
- **Fix Implemented:**
  - Added clean empty fallback state in `Sidebar.tsx`: renders `"No recent sessions yet"` when zero sessions exist, ensuring the UI communicates status clearly.

---

## Build Status

- Next.js build verified (0 errors, 0 warnings).
