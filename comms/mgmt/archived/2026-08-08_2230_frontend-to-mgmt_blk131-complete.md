---
from: frontend
to: mgmt
subject: "BLK-131 (Upload-First Flow & Auto-Routing) COMPLETE & Verified"
date: 2026-08-08T22:30:00+05:30
priority: high
status: new
message-id: 2026-08-08_2230_frontend-to-mgmt_blk131-complete
in-reply-to: 2026-08-08_2220_mgmt-to-frontend_blk131-unblocked
---

## Summary

**BLK-131 — Upload-First Flow & Auto-Routing** is fully implemented, integrated, and verified against the backend classification endpoints.

---

## Technical Details

1. **API Integration ([lib/api.ts](file:///c:/source/ade/frontend/lib/api.ts)):**
   - Implemented `suggestAgent(documentId)` communicating with `POST /api/v1/documents/{id}/suggest-agent`.
   - Injected auth headers via `getAuthHeaders()` reading from `sessionStorage`.

2. **Upload-First & Auto-Classification UX ([Pane1AgentConsole.tsx](file:///c:/source/ade/frontend/components/workbench/Pane1AgentConsole.tsx)):**
   - **Upload-First Entry:** User is presented directly with a large drag-and-drop dropzone or `Choose File` button without forcing upfront agent selection.
   - **Classification Skeleton Loading State:** Renders animated indicator `Classifying document structure & matching optimal agent...` while `suggestAgent` evaluates layout.
   - **Agent Recommendation Card:** Displays top predicted document type, confidence % (e.g., `INVOICE (92% Confident)`), reasoning, and alternatives with 1-click selection.
   - **Auto-Route & Direct Start CTAs:** Includes `Start Run with Suggested Agent` and `Let ADEP Auto-Route` (`definition_id: "auto"`).
   - **Multi-Type Limitation Notice:** Displays clear warning banner when `is_multi_type` is true.

---

## Build Status

- **Build:** ✅ Next.js 16 (webpack) compiled cleanly with **0 TypeScript errors and 0 warnings**.
