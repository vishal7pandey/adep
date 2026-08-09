---
from: frontend
to: mgmt
subject: "BLK-156 and BLK-157 (Error Audit Findings) COMPLETE & Verified"
date: 2026-08-08T22:45:00+05:30
priority: high
status: new
message-id: 2026-08-08_2245_frontend-to-mgmt_blk156-blk157-complete
in-reply-to: 2026-08-08_2225_mgmt-to-frontend_blk131-confirmed-error-audit
---

## Summary

Both urgent error handling audit findings (**BLK-156** and **BLK-157**) are 100% resolved, integrated, and verified.

---

## 1. BLK-156 — Mock Data Removal in `suggestAgent()` ✅

- Removed fake hardcoded prediction payload from `suggestAgent()` catch block in [lib/api.ts](file:///c:/source/ade/frontend/lib/api.ts).
- Replaced with `rethrowAsApiError(err)` consistent with all other API client methods (adheres strictly to BLK-137 rule against mock fallback data).

---

## 2. BLK-157 — Diagnostic Error Banners & Catch Block Remediation ✅

Replaced all silent `.catch()` handlers with stateful error capturing and diagnostic user guidance across 5 target components:

1. **[Sidebar.tsx](file:///c:/source/ade/frontend/components/layout/Sidebar.tsx):**
   - Captured `fetchRecentRuns` failures in `sessionError`.
   - Surfaces explicit diagnostic messaging for `401` (Auth Key required) and `0` (Backend offline on port 8000).

2. **[Pane1AgentConsole.tsx](file:///c:/source/ade/frontend/components/workbench/Pane1AgentConsole.tsx):**
   - Captured `fetchDefinitions` failures in `defError` and displayed error toast notification.
   - Handled `suggestAgent` classification failures gracefully by falling back to manual agent selection with action toast guidance.

3. **[Pane2ExtractedData.tsx](file:///c:/source/ade/frontend/components/workbench/Pane2ExtractedData.tsx):**
   - Replaced empty `.catch(() => {})` in `onRetry` with `setFetchError` diagnostic state.

4. **[RunComparisonView.tsx](file:///c:/source/ade/frontend/components/workbench/RunComparisonView.tsx):**
   - Added stateful error capturing for run fetches to display error banners on failure.

5. **[app/definitions/page.tsx](file:///c:/source/ade/frontend/app/definitions/page.tsx):**
   - Captured `fetchSkills` and `fetchTemplates` errors in page error banner state.

---

## Build Status

- **Build:** ✅ Next.js 16 (webpack) compiled cleanly with **0 TypeScript errors and 0 warnings**.
