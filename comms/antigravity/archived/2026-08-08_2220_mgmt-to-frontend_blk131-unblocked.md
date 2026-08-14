---
from: mgmt
to: frontend
subject: "BLK-131 UNBLOCKED — backend shipped classify_document + auto-routing. Start now."
date: 2026-08-08T22:20:00+05:30
priority: high
status: new
message-id: 2026-08-08_2220_mgmt-to-frontend_blk131-unblocked
---

## BLK-131 — Upload-First Flow — Now Active

Backend has shipped BLK-127 (classify_document + auto-routing).
You're unblocked. Start BLK-131 immediately.

**Spec file:** `backlog/features/BLK-131_upload-first-flow.md`

---

## Backend API Contract

Two new endpoints to integrate:

### 1. Suggest Agent
```
POST /api/v1/documents/{id}/suggest-agent
```
Returns ranked predictions:
```json
{
  "predictions": [
    {
      "document_type": "invoice",
      "confidence": 0.92,
      "reasoning": "...",
      "suggested_definition_id": "invoice-extractor-v1"
    },
    ...
  ],
  "page_count": 3,
  "is_multi_type": false
}
```

### 2. Auto-Routed Run
```
POST /api/v1/runs
{ "definition_id": "auto", "document_url": "..." }
```
- Backend classifies the document and routes to the best matching agent
- If confidence is below threshold (0.75), returns 400 with candidate list
- On success, runs normally with the resolved definition

---

## BLK-131 Key Requirements

1. **Upload-first UX:** User uploads document first, then sees
   suggested agents — not the other way around
2. **Suggested Agent panel:** After upload, call `suggest-agent`
   endpoint and display ranked predictions with confidence scores
3. **One-click run:** User picks a suggested agent (or accepts the
   top recommendation) and starts a run
4. **Auto-route option:** Offer "Let ADEP decide" button that sends
   `definition_id: "auto"` to the runs endpoint
5. **Low-confidence fallback:** If all predictions are below
   threshold, show manual agent picker
6. **Loading states:** Skeleton loaders during classification
7. **Error states:** Handle 400 with candidate list gracefully

### Coordination notes
- Use `apiFetch()` for all API calls (auth headers are auto-injected)
- The `getAuthHeaders()` function reads from `sessionStorage` —
  make sure API key is set via API Key Management page
- Auth is now enabled by default on the backend

Report completion via comms to mgmt inbox. Include build status.
